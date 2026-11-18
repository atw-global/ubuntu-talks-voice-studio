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

# Approved 139-block isiZulu Lesson 1 resumable Azure recorder.
from app.api.endpoints.lesson1_recording import router as lesson1_recording_router
app.include_router(lesson1_recording_router)

# Ubuntu Talks Azure Speech pilot: only explicit, capped voice audition requests.
from app.api.endpoints.azure_audition import router as azure_audition_router
app.include_router(azure_audition_router)

# Ubuntu Talks Vast.ai integration is read-only until explicitly enabled.
from app.api.endpoints.vast_status import router as vast_status_router
app.include_router(vast_status_router)

# Security boundary for the dedicated Render API origin: the frontend
# Nginx proxy authenticates the user and injects this server-side token.
# This ASGI wrapper protects HTTP *and* WebSocket connections.
from app.middleware.studio_gateway import StudioGateway
app = StudioGateway(app)
