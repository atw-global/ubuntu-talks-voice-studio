"""Source-locked isiZulu Beginner I Lesson 1 assembled audio master.

Creates a private internal QA master from 137 unchanged approved isiZulu/English
cues and two replacement English-only Mrs Ubuntu opening cues. The existing
139 original approved cue recordings remain untouched in PostgreSQL.

Production gate: voice QA, rights clearance, Drive/R2 archive, Whop hidden
course readback, and full learner test before public publication.
"""
from __future__ import annotations
import asyncio
import hashlib
import io
import json
import logging
import os
import pathlib
import subprocess
import tempfile
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import Column, DateTime, Integer, LargeBinary, MetaData, String, Table, select
from sqlalchemy.dialects.postgresql import insert
from app.api.endpoints.lesson1_recording import CUES, _hash, recordings, engine

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ubuntu/azure/lesson1/master", tags=["ubuntu-lesson1-master"])
meta = MetaData()
masters = Table(
    "ubuntu_voice_studio_lesson1_masters", meta,
    Column("version", String(40), primary_key=True),
    Column("mp3", LargeBinary, nullable=False),
    Column("sha256", String(64), nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("duration_sec", Integer, nullable=False),
    Column("cue_count", Integer, nullable=False),
    Column("generated_at", DateTime(timezone=True), nullable=False),
)
VERSION = "english-instructor-v1"
REVISED_NARRATION = {
    1: ("Welcome to Lesson One: Sounds, Greetings and Respect. "
        "Your challenge today is to greet one person or a group, respond "
        "appropriately, and take leave. First, listen carefully to the "
        "conversation. You do not need to understand every word yet."),
    2: ("The scene: A new neighbour greets you, and then you meet a group. "
        "You will hear two different speakers. One opens the conversation, "
        "and the other responds. Listen for the way a natural exchange "
        "moves from one speaker to another."),
}
assert len(CUES) == 139
assert all(CUES[n-1]["speaker"] == "MRS_UBUNTU" for n in REVISED_NARRATION)
_task = None
_status = {"state": "not_started", "error": None}
_lock = asyncio.Lock()

def _init():
    meta.create_all(engine, checkfirst=True)

def _master_metadata():
    _init()
    with engine.connect() as conn:
        row = conn.execute(select(
            masters.c.sha256, masters.c.size_bytes, masters.c.duration_sec,
            masters.c.cue_count, masters.c.generated_at,
        ).where(masters.c.version == VERSION)).first()
    if not row:
        return None
    return {"sha256": row[0], "bytes": row[1], "duration_seconds": row[2],
            "cue_count": row[3], "created_at": row[4].isoformat()}

async def _narrate(text, client, key, region):
    xml = ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
           'xml:lang="en-ZA"><voice name="en-ZA-LeahNeural">' +
           escape(text) + '</voice></speak>')
    response = await client.post(
        f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={"Ocp-Apim-Subscription-Key": key,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                 "User-Agent": "UbuntuTalksLesson1Master/1.0"},
        content=xml.encode("utf-8"))
    if response.status_code != 200 or not response.content:
        raise RuntimeError(f"Azure narration returned HTTP {response.status_code}")
    return bytes(response.content)

def _load_sources():
    with engine.connect() as conn:
        rows = conn.execute(
            select(recordings.c.ordinal, recordings.c.source_sha256, recordings.c.mp3)
            .where(recordings.c.ordinal >= 3)
        ).all()
    digests = {cue["order"]: _hash(cue) for cue in CUES[2:]}
    saved = {n: bytes(audio) for n, digest, audio in rows if digests.get(n) == digest}
    if set(saved) != set(range(3, 140)):
        missing = sorted(set(range(3, 140)) - set(saved))
        raise RuntimeError(f"Unverified source cue audio: {missing[:20]}")
    return saved

def _assemble(audio):
    with tempfile.TemporaryDirectory(prefix="ubuntu_lesson1_master_") as work:
        base = pathlib.Path(work)
        for n, data in audio.items():
            (base / f"cue_{n:03d}.mp3").write_bytes(data)
        for seconds, name in [(0.45, "short"), (0.9, "section"), (2.5, "practice")]:
            subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                 "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                 "-t", str(seconds), "-c:a", "libmp3lame", "-b:a", "96k",
                 "-y", str(base / f"{name}.mp3")],
                check=True, capture_output=True, timeout=25)
        paths = []
        for i, cue in enumerate(CUES):
            paths.append(f"file 'cue_{i+1:03d}.mp3'")
            if i == 138:
                continue
            n = cue["order"]
            following = CUES[i + 1]
            # Pauses are between spoken cues and never disrupt an utterance.
            if 61 <= n <= 84 or 87 <= n <= 96 or 123 <= n <= 127:
                pause = "practice"
            elif cue["speaker"] == "MRS_UBUNTU" or following["speaker"] == "MRS_UBUNTU":
                pause = "section"
            else:
                pause = "short"
            paths.append(f"file '{pause}.mp3'")
        (base / "playlist.txt").write_text(chr(10).join(paths) + chr(10), encoding="utf-8")
        target = base / "full-lesson-01.mp3"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
             "-f", "concat", "-safe", "1", "-i", str(base / "playlist.txt"),
             "-c", "copy", "-y", str(target)],
            check=True, capture_output=True, timeout=100)
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(target)],
            check=True, capture_output=True, text=True, timeout=25)
        duration = round(float(proc.stdout.strip()))
        blob = target.read_bytes()
        if len(blob) < 100000 or duration < 120:
            raise RuntimeError("Master incomplete or unexpectedly short")
        return blob, duration

async def _produce():
    global _status
    async with _lock:
        try:
            if _master_metadata() is not None:
                _status = {"state": "complete", "error": None}
                return
            _status = {"state": "assembling", "error": None}
            old = await asyncio.to_thread(_load_sources)
            key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
            region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
            if not key or not region or not region.replace("-", "").isalnum():
                raise RuntimeError("Azure speech configuration missing")
            async with httpx.AsyncClient(timeout=55) as client:
                a = await _narrate(REVISED_NARRATION[1], client, key, region)
                await asyncio.sleep(3)
                b = await _narrate(REVISED_NARRATION[2], client, key, region)
            old.update({1: a, 2: b})
            blob, seconds = await asyncio.to_thread(_assemble, old)
            sha = hashlib.sha256(blob).hexdigest()
            _init()
            with engine.begin() as conn:
                conn.execute(insert(masters).values(
                    version=VERSION, mp3=blob, sha256=sha,
                    size_bytes=len(blob), duration_sec=seconds, cue_count=139,
                    generated_at=datetime.now(timezone.utc),
                ).on_conflict_do_nothing(index_elements=[masters.c.version]))
            _status = {"state": "complete", "error": None}
            log.info("Lesson 01 audio master PASS: cues=139 bytes=%d duration=%d sha=%s",
                     len(blob), seconds, sha)
        except Exception as exc:
            _status = {"state": "failed", "error": str(exc)[:300]}
            log.exception("Lesson 01 master generation FAILED")

@router.get("/status")
def master_status():
    saved = _master_metadata()
    return {"version": VERSION, "state": "complete" if saved else _status["state"],
            "error": None if saved else _status["error"],
            "master": saved, "approved_cue_count": 139,
            "narrator_adjusted_cues": [1, 2],
            "isiZulu_cues_unchanged": True,
            "native_language_qa_pass": False,
            "commercial_release_approved": False}

@router.post("/start")
async def start_master():
    global _task
    if _master_metadata() is not None:
        return master_status()
    if _task is None or _task.done():
        _task = asyncio.create_task(_produce(), name="ubuntu_lesson01_full_master")
    return master_status()

@router.get("/listen.mp3")
def listen_master():
    _init()
    with engine.connect() as conn:
        row = conn.execute(select(masters.c.mp3).where(masters.c.version == VERSION)).first()
    if not row:
        raise HTTPException(404, detail="Full lesson audio is not ready")
    return Response(content=bytes(row[0]), media_type="audio/mpeg",
                    headers={"Cache-Control": "private, no-store",
                             "Content-Disposition": 'inline; filename="UbuntuTalks_isiZulu_Beginner_I_Lesson_01_Full.mp3"'})

@router.get("/download.mp3")
def download_master():
    resp = listen_master()
    resp.headers["Content-Disposition"] = 'attachment; filename="UbuntuTalks_isiZulu_Beginner_I_Lesson_01_Full.mp3"'
    return resp
