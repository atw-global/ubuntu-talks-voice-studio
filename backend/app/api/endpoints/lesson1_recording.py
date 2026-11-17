"""Resumable, source-exact isiZulu Lesson 1 Azure speech recording.

Only starts from an explicitly authenticated POST. No GPU. The F0 account
may be used for internal evaluation; commercial release requires a rights check.
All generated individual MP3s are persisted in the isolated PostgreSQL DB.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import os
import pathlib
import time
import zipfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import Column, Integer, LargeBinary, MetaData, String, Table, Text, DateTime, create_engine, select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ubuntu/azure/lesson1", tags=["ubuntu-lesson1-recording"])
DATA = pathlib.Path(__file__).resolve().parents[2] / "data" / "lesson01_approved_139.json"
MANIFEST = json.loads(DATA.read_text(encoding="utf-8"))
CUES = MANIFEST["spoken_cues"]
assert len(CUES) == 139
VOICE_ALLOWLIST = {"en-ZA-LeahNeural", "zu-ZA-ThandoNeural", "zu-ZA-ThembaNeural"}
assert all(x["azure_voice"] in VOICE_ALLOWLIST and x["text_to_speak"] for x in CUES)
assert [x["order"] for x in CUES] == list(range(1, 140))

meta = MetaData()
recordings = Table(
    "ubuntu_voice_studio_lesson1_clips", meta,
    Column("clip_id", String(32), primary_key=True),
    Column("ordinal", Integer, nullable=False),
    Column("voice", String(80), nullable=False),
    Column("source_sha256", String(64), nullable=False),
    Column("mp3", LargeBinary, nullable=False),
    Column("audio_sha256", String(64), nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
)
state = Table(
    "ubuntu_voice_studio_lesson1_runs", meta,
    Column("run_key", String(80), primary_key=True),
    Column("state", String(28), nullable=False),
    Column("last_error", Text, nullable=True),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
_running_task = None


def _init():
    meta.create_all(engine, checkfirst=True)


def _hash(cue):
    return hashlib.sha256((cue["azure_voice"] + "\n" + cue["text_to_speak"]).encode()).hexdigest()


def _progress():
    _init()
    with engine.connect() as conn:
        rows = conn.execute(select(recordings.c.clip_id, recordings.c.source_sha256,
                                   func.octet_length(recordings.c.mp3))).all()
        run = conn.execute(select(state.c.state, state.c.last_error, state.c.updated_at)
                           .where(state.c.run_key == "lesson1")).first()
    good = {cid: length for cid, digest, length in rows
            if any(c["clip_id"] == cid and _hash(c) == digest for c in CUES)}
    return {
        "lesson_id": MANIFEST["lesson_id"],
        "source_exact": True,
        "total": len(CUES),
        "recorded": len(good),
        "remaining": len(CUES) - len(good),
        "bytes": sum(good.values()),
        "state": run[0] if run else "not_started",
        "last_error": run[1] if run else None,
        "updated_at": run[2].isoformat() if run and run[2] else None,
        "commercial_release_approved": False,
        "storage": "isolated Render PostgreSQL; download ZIP and archive externally before free DB expiry",
    }


def _set_run(status, error=None):
    now = datetime.now(timezone.utc)
    with engine.begin() as conn:
        conn.execute(insert(state).values(run_key="lesson1", state=status,
                                          last_error=error, started_at=now,
                                          updated_at=now).on_conflict_do_update(
            index_elements=[state.c.run_key],
            set_={"state": status, "last_error": error, "updated_at": now},
        ))


def _next_cues():
    _init()
    with engine.connect() as conn:
        rows = conn.execute(select(recordings.c.clip_id, recordings.c.source_sha256)).all()
    prev = dict(rows)
    return [c for c in CUES if prev.get(c["clip_id"]) != _hash(c)]


async def _record():
    try:
        _set_run("recording")
        key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
        region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
        if not key or not region or not region.replace("-", "").isalnum():
            raise RuntimeError("Azure Speech credentials or region are missing")
        uri = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
            "User-Agent": "UbuntuTalksLesson1Production/1.0",
        }
        async with httpx.AsyncClient(timeout=65) as client:
            for cue in _next_cues():
                vo = cue["azure_voice"]
                xml = ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                       'xml:lang="' + cue["language"] + '"><voice name="' + vo + '">'
                       + escape(cue["text_to_speak"]) + '</voice></speak>')
                result = None
                for retry in range(5):
                    response = await client.post(uri, headers=headers,
                                                 content=xml.encode("utf-8"))
                    if response.status_code == 200 and response.content:
                        result = response.content
                        break
                    if response.status_code in (429, 500, 502, 503, 504):
                        await asyncio.sleep(min(8 * (retry + 1), 42))
                        continue
                    raise RuntimeError(f"Azure HTTP {response.status_code} for {cue['clip_id']}")
                if not result:
                    raise RuntimeError(f"Azure retries exhausted at {cue['clip_id']}")
                now = datetime.now(timezone.utc)
                with engine.begin() as conn:
                    conn.execute(insert(recordings).values(
                        clip_id=cue["clip_id"], ordinal=cue["order"], voice=vo,
                        source_sha256=_hash(cue), mp3=result,
                        audio_sha256=hashlib.sha256(result).hexdigest(), generated_at=now,
                    ).on_conflict_do_update(
                        index_elements=[recordings.c.clip_id],
                        set_={"source_sha256": _hash(cue), "ordinal": cue["order"],
                              "voice": vo, "mp3": result,
                              "audio_sha256": hashlib.sha256(result).hexdigest(),
                              "generated_at": now},
                    ))
                # Free F0 is limited to ~20 synthesis transactions per minute.
                # Stay below the cap with a 4-second cadence. No parallel synthesis.
                await asyncio.sleep(4.0)
        _set_run("complete")
    except Exception as exc:
        logger.exception("Lesson 1 recording stopped")
        # Do not expose key, Azure response headers, or text to the UI.
        _set_run("interrupted", str(exc)[:180])


@router.get("/status")
def recording_status():
    return _progress()


@router.post("/start")
async def start_recording():
    global _running_task
    if not os.environ.get("AZURE_SPEECH_KEY") or not os.environ.get("AZURE_SPEECH_REGION"):
        raise HTTPException(503, detail="Azure Speech credentials missing")
    progress = _progress()
    if progress["remaining"] == 0:
        return progress
    if _running_task is not None and not _running_task.done():
        return progress
    _running_task = asyncio.create_task(_record(), name="ubuntu-lesson1-azure-recording")
    # Let the task start before returning; failures are recorded.
    await asyncio.sleep(0.02)
    return _progress()


@router.get("/playlist")
def playlist():
    """Show source-locked ordered cues and whether each clip is ready."""
    _init()
    with engine.connect() as conn:
        rows = conn.execute(select(recordings.c.clip_id, recordings.c.source_sha256)).all()
    saved = dict(rows)
    return {"lesson_id": MANIFEST["lesson_id"],
            "total": len(CUES),
            "recorded": sum(saved.get(c["clip_id"]) == _hash(c) for c in CUES),
            "cues": [
                {"order": c["order"], "clip_id": c["clip_id"], "speaker": c["speaker"],
                 "voice": c["azure_voice"], "text": c["text_to_speak"],
                 "available": saved.get(c["clip_id"]) == _hash(c)}
                for c in CUES
            ]}


@router.get("/clips/{ordinal}")
def play_clip(ordinal: int):
    """Authenticated, source-verified clip for ordered full-lesson playback."""
    if ordinal < 1 or ordinal > len(CUES):
        raise HTTPException(404, detail="Invalid cue number")
    cue = CUES[ordinal-1]
    _init()
    with engine.connect() as conn:
        row = conn.execute(
            select(recordings.c.source_sha256, recordings.c.mp3).where(
                recordings.c.clip_id == cue["clip_id"]
            )
        ).first()
    if not row or row[0] != _hash(cue):
        raise HTTPException(404, detail="Audio not recorded for this cue")
    return Response(content=bytes(row[1]), media_type="audio/mpeg",
        headers={"Cache-Control": "private, max-age=600",
                 "Content-Disposition": f'inline; filename="lesson1-{ordinal:04d}.mp3"'})


@router.get("/export.zip")
def export_audio():
    _init()
    with engine.connect() as conn:
        rows = conn.execute(select(recordings.c.clip_id, recordings.c.ordinal,
                                   recordings.c.voice, recordings.c.source_sha256,
                                   recordings.c.mp3, recordings.c.audio_sha256)
                            .order_by(recordings.c.ordinal)).all()
    if not rows:
        raise HTTPException(404, detail="No Lesson 1 clips recorded yet")
    good = {row[0]: row for row in rows}
    archive = io.BytesIO()
    included = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as z:
        for cue in CUES:
            item = good.get(cue["clip_id"])
            if not item or item[3] != _hash(cue):
                continue
            name = f"clips/{cue['order']:04d}_{cue['speaker']}_{cue['clip_id']}.mp3"
            z.writestr(name, bytes(item[4]))
            included.append({"clip_id": cue["clip_id"], "file": name,
                             "audio_sha256": item[5]})
        z.writestr("approved_139_cue_manifest.json",
                   json.dumps(MANIFEST, ensure_ascii=False, indent=2))
        z.writestr("recording_inventory.json",
                   json.dumps({"count": len(included), "total": len(CUES),
                               "clips": included, "complete": len(included) == 139,
                               "publication_status": "NATIVE_QA_AND_PAID_TIER_RIGHTS_PENDING"},
                              indent=2))
    archive.seek(0)
    return StreamingResponse(archive, media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="UbuntuTalks_isiZulu_Lesson01_139_recordings.zip"',
                 "Cache-Control": "private, no-store"})
