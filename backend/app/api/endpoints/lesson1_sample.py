"""Private, exact-source Lesson 01 greeting audio sampler.

This endpoint is a *QA tool*, not a publicly distributable media URL.
The existing StudioGateway protects all routes; public publication requires a
separate reviewed R2 object with rights, native-language and Whop gates passed.
Only uses already-recorded, source-hash-matched Azure clips. No synthesis.
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import tempfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.api.endpoints.lesson1_recording import CUES, recordings, engine, _hash

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/sample", tags=["ubuntu-lesson1-sample"])

# Source-order excerpt from the approved, recorded greetings demonstration.
# No invented spoken lines or replacement voice recordings.
ORDINALS = tuple(range(3, 86))
MIN_SECONDS = 55
MAX_SECONDS = 120
TARGET_SECONDS = 85


def _read_verified():
    expected = {cue["order"]: cue for cue in CUES if cue["order"] in ORDINALS}
    if len(expected) != len(ORDINALS):
        raise HTTPException(409, "Approved cue index mismatch")
    with engine.connect() as conn:
        rows = conn.execute(
            select(recordings.c.ordinal, recordings.c.source_sha256,
                   recordings.c.audio_sha256, recordings.c.mp3)
            .where(recordings.c.ordinal.in_(ORDINALS))
        ).all()
    existing = {row[0]: row for row in rows}
    audio = {}
    for n in ORDINALS:
        item = existing.get(n)
        cue = expected[n]
        if item is None or item[1] != _hash(cue):
            raise HTTPException(409, "Source-approved clip missing or mismatched")
        chunk = bytes(item[3])
        if hashlib.sha256(chunk).hexdigest() != item[2]:
            raise HTTPException(409, "Recorded clip checksum mismatch")
        audio[n] = chunk
    return audio


def _assemble(audio):
    """Build a natural, source-ordered excerpt without chopping a spoken cue."""
    with tempfile.TemporaryDirectory(prefix="ubuntu_lesson01_sample_") as tmp:
        root = pathlib.Path(tmp)
        pause = root / "pause.mp3"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
             "-t", "0.35", "-c:a", "libmp3lame", "-b:a", "96k",
             "-y", str(pause)],
            check=True, capture_output=True, timeout=15,
        )
        playlist = []
        total_seconds = 0.0
        selected = []
        for n in ORDINALS:
            path = root / f"cue_{n:03d}.mp3"
            path.write_bytes(audio[n])
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                check=True, capture_output=True, text=True, timeout=15,
            )
            cue_seconds = float(proc.stdout.strip())
            if total_seconds >= MIN_SECONDS and total_seconds + cue_seconds + 0.35 > TARGET_SECONDS:
                break
            if selected:
                playlist.append("file 'pause.mp3'")
                total_seconds += 0.35
            playlist.append(f"file '{path.name}'")
            selected.append(n)
            total_seconds += cue_seconds
            if total_seconds >= TARGET_SECONDS:
                break
        if total_seconds < MIN_SECONDS or total_seconds > MAX_SECONDS:
            raise HTTPException(409, "Source sample outside 55-120s; requires editorial selection")
        (root / "playlist.txt").write_text("\n".join(playlist) + "\n", encoding="utf-8")
        dest = root / "sample.mp3"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
             "-f", "concat", "-safe", "1", "-i", str(root / "playlist.txt"),
             "-c", "copy", "-y", str(dest)],
            check=True, capture_output=True, timeout=50,
        )
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(dest)],
            check=True, capture_output=True, text=True, timeout=15,
        )
        seconds = float(proc.stdout.strip())
        if not (MIN_SECONDS <= seconds <= MAX_SECONDS):
            raise HTTPException(409, "Sample duration out of QA range")
        return dest.read_bytes(), round(seconds, 2), selected

@router.get("/qa-status")
def qa_status():
    """No indication of commercial QA approval and no public file URL."""
    return {
        "course_id": "zu-beginner-i",
        "lesson": 1,
        "clip_orders": list(ORDINALS),
        "native_speaker_qa": "PENDING",
        "commercial_rights": "PENDING",
        "secure_public_sample": False,
        "whop_attached": False,
        "release": "BLOCKED",
    }


@router.get("/qa-preview.mp3")
def qa_preview():
    """Authenticated internal greeting sample; never a public sales embed."""
    audio = _read_verified()
    try:
        blob, seconds, selected = _assemble(audio)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        raise HTTPException(502, "Unable to assemble source-verified QA sample")
    return Response(
        content=blob, media_type="audio/mpeg",
        headers={
            "Cache-Control": "private, no-store",
            "X-Ubuntu-Sample-Duration-Seconds": str(seconds),
            "X-Ubuntu-Source-Cue-Count": str(len(selected)),
            "X-Ubuntu-Sample-SHA256": hashlib.sha256(blob).hexdigest(),
            "Content-Disposition": 'inline; filename="UbuntuTalks_EverydayIsiZulu_Lesson01_QA_Sample.mp3"',
        },
    )
