"""OpenSpeakers FastAPI application entry point.

Production-quality setup:
  - Request ID tracking (X-Request-ID header)
  - Structured error responses
  - CORS with explicit origin list
  - Health check at /health (Docker-compatible)
  - Alembic migrations on startup
  - Graceful shutdown
  - WebSocket endpoint for real-time job progress
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.endpoints.openai_compat import router as openai_compat_router
from app.api.endpoints.system import router as system_router
from app.api.router import api_router
from app.api.websockets import ws_router
from app.core.config import settings
from app.middleware.request_id import RequestIDMiddleware

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting OpenSpeakers backend (env=%s)", settings.ENVIRONMENT)

    # Run DB migrations. A failure here means the DB is unreachable or the schema
    # is broken — continuing would just produce cryptic ORM errors on the first
    # query. Fail fast so the container restart loop surfaces the problem.
    try:
        from app.db.migrations import run_migrations

        run_migrations()
    except Exception:
        logger.exception("Migration failed — refusing to start with an inconsistent DB")
        raise

    # Ensure audio output directory exists
    from pathlib import Path

    Path(settings.AUDIO_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Surface models that will silently route to the default "tts" queue because
    # they lack a QUEUE_MAP entry. Not fatal — the default queue is valid — but a
    # missing entry usually means a new model was added and the routing wasn't
    # updated to match the worker that actually has its deps installed.
    from app.api.endpoints.tts import QUEUE_MAP
    from app.models.manager import ModelManager

    registered = set(ModelManager.get_instance().registered_ids)
    unrouted = sorted(m for m in registered if m not in QUEUE_MAP)
    if unrouted:
        logger.warning(
            "Models without explicit QUEUE_MAP entry (falling back to 'tts' queue): %s",
            ", ".join(unrouted),
        )
    stale = sorted(set(QUEUE_MAP) - registered)
    if stale:
        logger.warning(
            "QUEUE_MAP has entries for unregistered models: %s",
            ", ".join(stale),
        )

    logger.info("OpenSpeakers backend ready")
    if __import__("os").environ.get("UBUNTU_LESSON1_MASTER_AUTOSTART", "").lower() == "true":
        try:
            from app.api.endpoints.lesson1_master import _produce as _build_master, _master_metadata
            if _master_metadata() is None:
                __import__("asyncio").create_task(_build_master(), name="lesson01-approved-master")
        except Exception:
            logger.exception("Lesson01 master auto-start failed")

    # Opt-in internal diagnostic verifies that the English-guidance sample
    # returns a nonempty MP3 without exposing any credentials or audio publicly.
    # Runs only when the temporary demo verification flag is enabled.
    import os as _envos
    if _envos.environ.get("UBUNTU_LESSON1_DEMO_VERIFY", "").lower() == "true":
        import asyncio as _verify_asyncio
        async def _check_lesson1_demo():
            from app.api.endpoints.azure_audition import lesson1_english_guidance_demo
            try:
                result = await lesson1_english_guidance_demo()
                blob = result.body
                if result.media_type == "audio/mpeg" and len(blob) > 3000:
                    logger.info("Ubuntu Lesson 1 sample self-test PASS: audio/mpeg %d bytes", len(blob))
                else:
                    logger.error("Ubuntu Lesson 1 sample self-test FAIL: invalid media/size")
            except Exception:
                logger.exception("Ubuntu Lesson 1 sample self-test FAIL")
        _verify_asyncio.create_task(_check_lesson1_demo(), name="ubuntu-lesson1-demo-selftest")
    # Verify source-matched Lesson 1 sample assembly within the protected
    # server process. The test logs only size/duration/hash, never audio bytes.
    if _envos.environ.get("UBUNTU_LESSON1_SAMPLE_SELFTEST", "true").lower() == "true":
        import asyncio as _sample_asyncio
        import hashlib as _sample_hashlib
        async def _sample_selftest():
            try:
                from app.api.endpoints.lesson1_sample import _read_verified, _assemble
                def verify():
                    blob, duration, selected = _assemble(_read_verified())
                    return len(blob), duration, len(selected), _sample_hashlib.sha256(blob).hexdigest()
                size, duration, cues, digest = await _sample_asyncio.to_thread(verify)
                logger.info("Ubuntu private Lesson 1 greeting sample SELFTEST PASS: bytes=%d duration_sec=%.2f cues=%d sha256=%s release=BLOCKED",
                            size, duration, cues, digest)
            except Exception as error:
                logger.error("Ubuntu private Lesson 1 greeting sample SELFTEST FAIL: type=%s", type(error).__name__)
                logger.exception("Private lesson sample failed internal technical verification")
        _sample_asyncio.create_task(_sample_selftest(), name="ubuntu-lesson01-sample-technical-qa")
    # Private, source-hash-gated master and greeting excerpt archival.
    # Runs only when BOTH dedicated bucket credentials exist. No public URLs,
    # no Whop publication, and no overwrite of inconsistent existing objects.
    if (_envos.environ.get("UBUNTU_R2_ACCESS_KEY_ID") and
            _envos.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY")):
        import asyncio as _archive_asyncio
        async def _private_lesson01_archive():
            try:
                from app.api.endpoints.lesson1_archive import _archive as _archive_master
                from app.api.endpoints.lesson1_sample_archive import _archive_sample
                for label, operation in (("master", _archive_master), ("greeting_sample", _archive_sample)):
                    try:
                        result = await _archive_asyncio.to_thread(operation)
                        logger.info("Ubuntu private R2 Lesson01 %s ARCHIVE VERIFIED sha256=%s bytes=%d public_url=NONE",
                                    label, result["sha256"], result["bytes"])
                    except Exception as exc:
                        logger.error("Ubuntu private R2 Lesson01 %s ARCHIVE FAILED type=%s", label, type(exc).__name__)
                        logger.exception("Protected archive requires manual operator review")
            except Exception as exc:
                logger.error("Ubuntu private R2 archival setup FAILED type=%s", type(exc).__name__)
        _archive_asyncio.create_task(_private_lesson01_archive(), name="ubuntu-lesson01-secure-r2-archive")
    # Company API key check runs inside Render without exposing any bearer token.
    # Explicitly approved single-product cover update is opt-in and idempotent.
    if _envos.environ.get("WHOP_API_KEY", "").strip():
        import asyncio as _whop_asyncio
        async def _check_whop_pilot():
            try:
                from app.api.endpoints.whop_course_factory import status as _whop_status
                result = await _whop_asyncio.to_thread(_whop_status)
                logger.info("Ubuntu Whop company API CHECK PASS product=%s visibility=%s gallery=%s",
                            result.get("product_id"), result.get("product_visibility"), result.get("product_gallery_file_ids"))
                try:
                    from app.api.endpoints.whop_course_factory import release_preflight as _release_preflight
                    preflight = await _whop_asyncio.to_thread(_release_preflight)
                    logger.info("Ubuntu Whop LIVE PILOT PREFLIGHT price=%s one_time=%s lesson_media_count=%d commercial_release=%s",
                                preflight["price_usd"], preflight["one_time"],
                                preflight["lesson_attachment_count"], preflight["commercial_release_allowed"])
                except Exception as preflight_error:
                    logger.warning("Ubuntu Whop PILOT PREFLIGHT blocked type=%s detail=%s",
                                   type(preflight_error).__name__,
                                   getattr(preflight_error, "detail", "internal_error"))
                if _envos.environ.get("UBUNTU_WHOP_APPROVED_COVER_APPLY", "").lower() == "true":
                    from app.api.endpoints.whop_course_factory import apply_approved_cover
                    outcome = await _whop_asyncio.to_thread(apply_approved_cover)
                    logger.info("Ubuntu Whop HD COVER APPLY RESULT status=%s product=%s file=%s",
                                outcome.get("status"), outcome.get("product_id"), outcome.get("new_file_id"))
            except Exception as error:
                logger.error("Ubuntu Whop company API check/apply FAILED type=%s detail=%s",
                             type(error).__name__, getattr(error, "detail", "internal_failure"))
        _whop_asyncio.create_task(_check_whop_pilot(), name="ubuntu-whop-private-company-api-check")
    else:
        logger.info("Ubuntu Whop company API key NOT CONFIGURED; hidden pilot unchanged")
    # Internal-only playback self-test. Uses the same authenticated R2 route
    # handler as the staging audio player; never logs or exposes audio bytes.
    if _envos.environ.get("UBUNTU_R2_ACCESS_KEY_ID") and _envos.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY"):
        import asyncio as _audio_check_asyncio
        async def _check_private_sample_playback():
            try:
                from app.api.endpoints.lesson1_sample_archive import play_private_archived_sample
                from starlette.requests import Request as _PlaybackRequest
                asgi_request = _PlaybackRequest({"type": "http", "method": "GET", "path": "/api/ubuntu/azure/lesson1/sample/archive/private-preview.mp3", "headers": []})
                result = await _audio_check_asyncio.to_thread(play_private_archived_sample, asgi_request)
                partial_request = _PlaybackRequest({"type": "http", "method": "GET", "path": "/api/ubuntu/azure/lesson1/sample/archive/private-preview.mp3", "headers": [(b"range", b"bytes=0-1023")]})
                partial = await _audio_check_asyncio.to_thread(play_private_archived_sample, partial_request)
                if partial.status_code != 206 or len(partial.body) != 1024 or partial.headers.get("content-range") != "bytes 0-1023/1021292":
                    raise RuntimeError("Mobile byte-range playback failed")
                from app.api.endpoints.lesson1_sample_archive import EXPECTED_BYTES
                if result.status_code != 200 or result.media_type != "audio/mpeg" or len(result.body) != EXPECTED_BYTES:
                    raise RuntimeError("Unexpected private sample response identity")
                logger.info("Ubuntu private Lesson01 R2 PLAYER SELFTEST PASS HTTP=200 mime=audio/mpeg bytes=%d commercial_publication=BLOCKED", len(result.body))
            except Exception as exc:
                logger.error("Ubuntu private Lesson01 R2 PLAYER SELFTEST FAIL type=%s", type(exc).__name__)
        _audio_check_asyncio.create_task(_check_private_sample_playback(), name="ubuntu-r2-sample-private-player-selftest")
    # Render private network DNS locator is not a credential. Log only its hostname.\n    logger.info("Ubuntu backend private-network discovery=%s", _envos.environ.get("RENDER_DISCOVERY_SERVICE", "UNSET"))\n    # Stage then verify the identical native-only MP3 and cue manifest in sequence.
    # These are private reference files; no public access or license asserted.
    import asyncio as _native_sample_asyncio
    async def _stage_native_only_sample():
        try:
            from app.api.endpoints.lesson1_sample_sync import stage_once, synced_dialogue, native_only_audio
            from starlette.requests import Request as _NativeRequest
            result = await _native_sample_asyncio.to_thread(stage_once)
            manifest = await _native_sample_asyncio.to_thread(synced_dialogue)
            rows = manifest["cues"]
            if (len(rows) != result["cues"] or rows[0]["cue"] != 3
                or rows[-1]["end"] > manifest["duration_seconds"] + 0.25
                or any(r["speaker"] not in ("Thando", "Themba") for r in rows)
                or manifest["instructor_english_audio"] is not False):
                raise RuntimeError("Native speaker sync manifest invalid")
            request = _NativeRequest({"type":"http","method":"GET",
                "path":"/api/ubuntu/azure/lesson1/sample/native-only.mp3",
                "headers":[(b"range",b"bytes=0-1023")]})
            audio = await _native_sample_asyncio.to_thread(native_only_audio, request)
            if (audio.status_code != 206 or len(audio.body) != 1024
                or not audio.headers.get("content-range","").startswith("bytes 0-1023/")):
                raise RuntimeError("Native sample mobile-range transport invalid")
            logger.info("Ubuntu native-only sample PLAYBACK+SYNC PASS duration=%s cues=%s hash=%s sample_range=206",
                result["duration"],len(rows),result["sha256"])
        except Exception as exc:
            logger.error("Ubuntu native-only sample PLAYBACK+SYNC FAILED type=%s",type(exc).__name__)
    _native_sample_asyncio.create_task(_stage_native_only_sample(),name="ubuntu-native-only-lesson01-stager")
    # Produce immutable instructor-introduced private sample once; unchanged
    # approved voices and exact source cue text, no public rights implied.
    if _envos.environ.get("UBUNTU_R2_ACCESS_KEY_ID") and _envos.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY"):
        import asyncio as _intro_asyncio
        async def _stage_intro_sample():
            try:
                from app.api.endpoints.lesson1_sample_intro_stage import stage_once
                result = await _intro_asyncio.to_thread(stage_once)
                logger.info("Ubuntu introduced 85-95s PRIVATE sample STAGED state=%s duration=%s cues=%s",
                            result["state"], result["duration"], result["cues"])
            except Exception as exc:
                logger.error("Ubuntu introduced PRIVATE sample STAGING FAILED type=%s", type(exc).__name__)
        _intro_asyncio.create_task(_stage_intro_sample(), name="ubuntu-private-instructor-intro-stager")
    # Explicitly authorized isiZulu Lesson 1 Azure recording. Auto-resume
    # from PostgreSQL checkpoints after Render free-service restarts.
    # Opt-in only; no worker/GPU. Recording never publishes course content.
    import os
    import asyncio
    if os.environ.get("UBUNTU_LESSON1_AUTORECORD", "false").lower() == "true":
        from app.api.endpoints.lesson1_recording import _progress, _record
        try:
            if _progress()["remaining"] > 0:
                logger.info("Starting/resuming authorized 139-cue Lesson 1 Azure recording")
                asyncio.create_task(_record(), name="ubuntu-lesson1-azure-auto")
        except Exception:
            logger.exception("Unable to resume authorized Lesson 1 recording")
    yield
    logger.info("OpenSpeakers backend shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OpenSpeakers",
    description="Unified TTS and voice cloning API — VibeVoice, Fish Speech, Qwen3, Kokoro",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ── Exception handlers ────────────────────────────────────────────────────────


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning("ValueError in %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=422,
        content={
            "error": str(exc),
            "status_code": 422,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, _exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception(
        "Unhandled exception [request_id=%s] %s %s",
        request_id,
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "request_id": request_id,
        },
    )


# ── Request timing middleware (simple) ───────────────────────────────────────


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    t = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - t) * 1000)
    response.headers["X-Process-Time-Ms"] = str(elapsed_ms)
    return response


# ── Routes ────────────────────────────────────────────────────────────────────

# System routes at root (health check for Docker)
app.include_router(system_router)

# REST API under /api
app.include_router(api_router)

# WebSocket routes (no /api prefix — proxied separately in nginx)
app.include_router(ws_router)

# OpenAI-compatible API (mounted at root so /v1/audio/speech works)
app.include_router(openai_compat_router)

# Source-verified private Cloudflare R2 archive, no public access.
from app.api.endpoints.lesson1_archive import router as lesson1_archive_router
app.include_router(lesson1_archive_router)

# Full 139-cue private audio master, preserving all native isiZulu speech.
from app.api.endpoints.lesson1_master import router as lesson1_master_router
app.include_router(lesson1_master_router)

# Native-speaker-only learner-stage preview cue timing; no instructor speech.
from app.api.endpoints.lesson1_sample_sync import router as lesson1_sample_sync_router
app.include_router(lesson1_sample_sync_router)

# Lesson 1 classroom access. Paid stages require a verified Whop membership.
from app.api.endpoints.lesson1_classroom import router as lesson1_classroom_router
app.include_router(lesson1_classroom_router)

# Internal source-verified greeting audio QA sample; StudioGateway protected.
from app.api.endpoints.lesson1_sample import router as lesson1_sample_router
app.include_router(lesson1_sample_router)

# Private Lesson 1 native-language review; audio never made public.
from app.api.endpoints.lesson1_release_review import router as lesson1_release_review_router
app.include_router(lesson1_release_review_router)

# Source-exact, instructor-introduced F0 preview for private staging.
from app.api.endpoints.lesson1_sample_intro_stage import router as lesson1_sample_intro_router
app.include_router(lesson1_sample_intro_router)

# Checksum-gated private QA archive for the approved greeting sample.
from app.api.endpoints.lesson1_sample_archive import router as lesson1_sample_archive_router
app.include_router(lesson1_sample_archive_router)

# Server-side Whop company-key integration; guarded by StudioGateway.
from app.api.endpoints.whop_course_factory import router as whop_course_factory_router
app.include_router(whop_course_factory_router)

# Approved 139-block isiZulu Lesson 1 resumable Azure recorder.
from app.api.endpoints.lesson1_recording import router as lesson1_recording_router
app.include_router(lesson1_recording_router)

# Ubuntu Talks Azure Speech pilot: only explicit, capped voice audition requests.
from app.api.endpoints.azure_audition import router as azure_audition_router
app.include_router(azure_audition_router)

# Ubuntu Talks Vast.ai integration is read-only until explicitly enabled.
from app.api.endpoints.vast_status import router as vast_status_router
app.include_router(vast_status_router)

# Versioned MCP endpoint. Its own credentials apply; the gateway token does not.
from app.api.endpoints.mcp_v1 import router as mcp_v1_router
app.include_router(mcp_v1_router)

# OAuth 2.1 discovery and consent for MCP clients. Owner approval is required.
from app.api.endpoints.oauth_mcp import router as oauth_mcp_router
app.include_router(oauth_mcp_router)

# Security boundary for the dedicated Render API origin: the frontend
# Nginx proxy authenticates the user and injects this server-side token.
# This ASGI wrapper protects HTTP *and* WebSocket connections.
from app.middleware.studio_gateway import StudioGateway
app = StudioGateway(app)
