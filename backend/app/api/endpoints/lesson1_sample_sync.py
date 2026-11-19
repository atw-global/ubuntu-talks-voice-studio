"""Private, source-verified native dialogue excerpt and word-level group tracking.

Excludes all Mrs Ubuntu English narration from sample audio and captions.
Uses only existing, approved Thando/Themba cue MP3s. No new synthesis.
R2 object versioned separately; immutable hash validated every playback.
Never public or commercially released.
"""
from __future__ import annotations
import hashlib
import json
import logging
import pathlib
import subprocess
import tempfile
import threading
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from botocore.exceptions import ClientError, BotoCoreError
from sqlalchemy import select
from app.api.endpoints.lesson1_archive import BUCKET, _r2_client
from app.api.endpoints.lesson1_recording import CUES, recordings, engine, _hash
from app.lesson_audio import clip_audio

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/sample", tags=["ubuntu-lesson1-synced-dialogue"])
log = logging.getLogger(__name__)
KEY = "courses/zu/beginner-i/lesson-01/v3-stage/native-voices-only.mp3"
MANIFEST = "courses/zu/beginner-i/lesson-01/v3-stage/native-voices-only-timed.json"
SOURCE = "native-greeting-lesson01-v1"
ORDERS = tuple(list(range(3, 11)) + list(range(13, 33)))
PAUSE = 0.35
TARGET = 84.0
MIN_SECONDS = 60.0
MAX_SECONDS = 112.0
MEANINGS = {
 "Sawubona.": "Hello (one person).", "Sanibonani.": "Hello (a group).",
 "Unjani?": "How are you? (one person)", "Ninjani?": "How are you? (a group)",
 "Ngiyaphila.": "I am fine.",
 "Ngiyaphila, wena unjani?": "I'm fine. And how are you?",
 "Sisaphila, nina ninjani?": "We are fine. How are you all?",
 "Ngiyabonga.": "Thank you.",
 "Sala kahle.": "Stay well.", "Ngizokubona kusasa.": "See you tomorrow.",
}

def _create():
    with engine.connect() as conn:
        rows=conn.execute(select(recordings.c.ordinal, recordings.c.mp3,
            recordings.c.source_sha256, recordings.c.audio_sha256)
            .where(recordings.c.ordinal.in_(ORDERS))).all()
    index={int(r[0]):r for r in rows}
    if len(index)!=len(ORDERS):
        raise ValueError("Approved native cue archive is incomplete")
    with tempfile.TemporaryDirectory(prefix="ubuntu_native_sample_") as temp:
        root=pathlib.Path(temp)
        pause=root/"pause.mp3"
        subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
            "-f","lavfi","-i","anullsrc=r=24000:cl=mono","-t",str(PAUSE),
            "-c:a","libmp3lame","-b:a","96k","-y",str(pause)],
            check=True,capture_output=True,timeout=15)
        cursor=0.0
        selected=[]
        concat=[]
        for n in ORDERS:
            cue=CUES[n-1]
            row=index[n]
            if cue["speaker"] not in ("ZULU_A","ZULU_B") or row[2]!=_hash(cue):
                raise ValueError("Source or approved native-speaker mismatch")
            clip=bytes(row[1])
            if hashlib.sha256(clip).hexdigest()!=row[3]:
                raise ValueError("Source cue MP3 integrity mismatch")
            file=root/f"cue_{n:03d}.mp3";file.write_bytes(clip)
            result=subprocess.run(["ffprobe","-v","error","-show_entries",
                "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(file)],
                check=True,capture_output=True,text=True,timeout=10)
            duration=float(result.stdout.strip())
            if selected and cursor>=TARGET:
                break
            if selected:
                concat.append("file 'pause.mp3'")
                cursor+=PAUSE
            start=cursor
            cursor+=duration
            concat.append(f"file '{file.name}'")
            selected.append({"cue":n,"speaker":"Thando" if cue["speaker"]=="ZULU_A" else "Themba",
                "text":cue["text_to_speak"],"meaning":MEANINGS.get(cue["text_to_speak"],""),
                "start":round(start,3),"end":round(cursor,3)})
        if not (MIN_SECONDS <= cursor <= MAX_SECONDS):
            raise ValueError(f"Native excerpt duration outside reviewed range ({cursor:.1f}s)")
        (root/"playlist.txt").write_text("\n".join(concat)+"\n",encoding="utf-8")
        output=root/"preview.mp3"
        subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
            "-f","concat","-safe","1","-i",str(root/"playlist.txt"),
            "-c","copy","-y",str(output)],check=True,capture_output=True,timeout=55)
        probe=subprocess.run(["ffprobe","-v","error","-show_entries",
            "format=duration","-of","default=noprint_wrappers=1:nokey=1",str(output)],
            check=True,capture_output=True,text=True,timeout=10)
        actual=round(float(probe.stdout.strip()),3)
        if not (MIN_SECONDS<=actual<=MAX_SECONDS):
            raise ValueError("Final native preview duration outside limits")
        blob=output.read_bytes()
        ratio=actual/cursor
        for line in selected:
            line["start"]=round(line["start"]*ratio,3)
            line["end"]=round(line["end"]*ratio,3)
        manifest={
            "version":SOURCE,"sample":"native-only-lesson1",
            "duration_seconds":actual,"cue_count":len(selected),
            "source_cue_orders":[x["cue"] for x in selected],
            "audio_bytes":len(blob),"audio_sha256":hashlib.sha256(blob).hexdigest(),
            "timing_method":"verified_mp3_source_durations_normalized_to_exported_MP3",
            "commercial_release":False,"instructor_english_audio":False,
            "cues":selected,
        }
        return blob,manifest

def stage_once():
    client=_r2_client()
    try:
        obj=client.get_object(Bucket=BUCKET,Key=MANIFEST)
        manifest=json.loads(obj["Body"].read())
        head=client.head_object(Bucket=BUCKET,Key=KEY)
        if (manifest.get("version")==SOURCE and not manifest.get("commercial_release")
            and not manifest.get("instructor_english_audio")
            and head.get("ContentLength")==manifest.get("audio_bytes")
            and (head.get("Metadata") or {}).get("sha256")==manifest.get("audio_sha256")):
            return {"status":"already_verified","duration":manifest["duration_seconds"],
                "cues":manifest["cue_count"],"sha256":manifest["audio_sha256"]}
        raise RuntimeError("Versioned sample identity collision")
    except ClientError as exc:
        if str(exc.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):
            raise
    blob,manifest=_create()
    client.put_object(Bucket=BUCKET,Key=KEY,Body=blob,ContentType="audio/mpeg",
        CacheControl="private, no-store",Metadata={"sha256":manifest["audio_sha256"],
        "release":"f0-reference-only"})
    client.put_object(Bucket=BUCKET,Key=MANIFEST,
        Body=json.dumps(manifest,ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",CacheControl="private, no-store")
    head=client.head_object(Bucket=BUCKET,Key=KEY)
    if head.get("ContentLength")!=len(blob) or (head.get("Metadata") or {}).get("sha256")!=manifest["audio_sha256"]:
        raise RuntimeError("Immutable native excerpt failed R2 readback")
    log.info("Ubuntu native-only preview STAGED PASS duration=%s cues=%s bytes=%s sha256=%s",
        manifest["duration_seconds"],manifest["cue_count"],len(blob),manifest["audio_sha256"])
    return {"status":"verified","duration":manifest["duration_seconds"],
        "cues":manifest["cue_count"],"sha256":manifest["audio_sha256"]}

def _manifest():
    try:
        obj=_r2_client().get_object(Bucket=BUCKET,Key=MANIFEST)
        data=json.loads(obj["Body"].read())
        if data.get("version")!=SOURCE or data.get("commercial_release") is not False or data.get("instructor_english_audio") is not False:
            raise ValueError("Native-only audio source mismatch")
        return data
    except (ClientError,BotoCoreError,ValueError) as exc:
        raise HTTPException(503,detail="Native-only private sample not yet staged") from exc

_PACKAGE_LOCK = threading.Lock()
_PACKAGE: dict | None = None

def _verified_package():
    """Checksum the MP3 once, then serve every range from that buffer.

    A browser seek used to download and hash the whole object again. That
    path produced intermittent 502 responses while storage was slow.
    """
    global _PACKAGE
    with _PACKAGE_LOCK:
        if _PACKAGE is not None:
            return _PACKAGE
        data = _manifest()
        expected = int(data["audio_bytes"])
        try:
            obj = _r2_client().get_object(Bucket=BUCKET, Key=KEY)
            blob = obj["Body"].read(expected + 1)
            if len(blob) != expected or hashlib.sha256(blob).hexdigest() != data["audio_sha256"]:
                raise ValueError("Native sample MP3 checksum mismatch")
        except (ClientError, BotoCoreError, ValueError) as exc:
            raise HTTPException(502, detail="Private native dialogue not available") from exc
        _PACKAGE = {"manifest": data, "audio": blob}
        return _PACKAGE

@router.get("/synced-dialogue")
def synced_dialogue():
    return _verified_package()["manifest"]

@router.get("/native-only.mp3")
def native_only_audio(request: Request):
    blob = _verified_package()["audio"]
    status, body, extra = clip_audio(blob, request.headers.get("range"))
    headers = {
        "Cache-Control": "private, no-store, max-age=0",
        "Accept-Ranges": "bytes",
        "X-Robots-Tag": "noindex, nofollow",
        "X-Ubuntu-Release": "F0-private-review-only",
        **extra,
    }
    return Response(content=body, media_type="audio/mpeg", status_code=status, headers=headers)
