"""Timed native-speaker dialogue for the original 85.08s F0 QA sample.

Timings come from the exact 25 verified source cue recordings and same
0.35-second inter-cue pauses as the verified sample assembler. No English
instructor cue is part of this sample. Backend-gateway protected.
"""
from __future__ import annotations

from functools import lru_cache
import pathlib
import subprocess
import tempfile
from sqlalchemy import select
from fastapi import APIRouter, HTTPException
from app.api.endpoints.lesson1_recording import CUES, recordings, engine, _hash
from app.api.endpoints.lesson1_sample_archive import EXPECTED_SHA256

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/sample", tags=["ubuntu-lesson1-synced-dialogue"])
ORDERS = tuple(range(3, 28))
PAUSE = 0.35
DURATION = 85.08
MEANINGS = {
 "Sawubona.": "Hello (one person).",
 "Sanibonani.": "Hello (a group).",
 "Unjani?": "How are you? (one person)",
 "Ninjani?": "How are you? (a group)",
 "Ngiyaphila.": "I am fine.",
 "Ngiyaphila, wena unjani?": "I'm fine. And how are you?",
 "Sisaphila, nina ninjani?": "We are fine. How are you all?",
 "Ngiyabonga.": "Thank you.",
}

@lru_cache(maxsize=1)
def _synced():
    with engine.connect() as conn:
        rows = conn.execute(select(recordings.c.ordinal, recordings.c.mp3,
            recordings.c.source_sha256).where(recordings.c.ordinal.in_(ORDERS))).all()
    index = {int(r[0]): r for r in rows}
    if len(index) != len(ORDERS):
        raise ValueError("Source-verified dialogue is incomplete")
    lines, cursor = [], 0.0
    with tempfile.TemporaryDirectory(prefix="ubuntu_sample_sync_") as tmp:
        root = pathlib.Path(tmp)
        for i,n in enumerate(ORDERS):
            cue = CUES[n-1]
            row = index[n]
            if row[2] != _hash(cue) or cue["speaker"] == "MRS_UBUNTU":
                raise ValueError("Source-approved isiZulu-only dialogue mismatch")
            src = root / f"cue_{n:03d}.mp3"
            src.write_bytes(bytes(row[1]))
            result = subprocess.run(["ffprobe","-v","error","-show_entries",
                "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(src)],
                capture_output=True,text=True,check=True,timeout=12)
            seconds = float(result.stdout.strip())
            if i:
                cursor += PAUSE
            start = round(cursor,3)
            cursor += seconds
            lines.append({
                "cue": n,
                "speaker": "Thando" if cue["speaker"] == "ZULU_A" else "Themba",
                "text": cue["text_to_speak"],
                "meaning": MEANINGS.get(cue["text_to_speak"], ""),
                "start":start,
                "end":round(cursor,3),
            })
    # MP3 concat may introduce encoder padding. Normalize timing to observed
    # immutable duration, preserving source order and approximate cue starts.
    if not (75 < cursor < 95):
        raise ValueError("Derived source cue timing outside verified sample range")
    factor = DURATION / cursor
    for item in lines:
        item["start"] = round(item["start"]*factor,3)
        item["end"] = round(item["end"]*factor,3)
    return {
        "sample":"original-85s-native-only",
        "duration_seconds":DURATION,"cue_count":len(lines),
        "source_sha256":EXPECTED_SHA256,
        "timing_method":"source_mp3_durations_plus_0.35s_pauses_normalized",
        "commercial_release":False,
        "instructor_english_audio":False,
        "cues":lines,
    }

@router.get("/synced-dialogue")
def synced_dialogue():
    try:
        return _synced()
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(503, detail="Private synchronized lesson sample not available") from exc
