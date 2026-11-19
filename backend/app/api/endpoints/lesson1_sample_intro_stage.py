"""Staged-only instructor-introduced Lesson 1 audio sample.

Re-edits already-approved/source-verified F0 reference clips; NO new TTS.
The prefix is independent of the original R2 master and 85-second sample.
It is an internal QA draft, not a public sample or a licensed master.
"""
from __future__ import annotations
import hashlib
import io
import json
import logging
import os
import pathlib
import re
import subprocess
import tempfile
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from botocore.exceptions import ClientError, BotoCoreError
from app.api.endpoints.lesson1_archive import BUCKET, _r2_client
from app.api.endpoints.lesson1_recording import CUES, recordings, engine, _hash
from app.api.endpoints.lesson1_sample import _read_verified

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/sample/intro-stage", tags=["ubuntu-lesson1-intro-stage"])
log = logging.getLogger(__name__)
KEY = "courses/zu/beginner-i/lesson-01/v2-stage/mrs-ubuntu-introduced-reference.mp3"
MANIFEST_KEY = "courses/zu/beginner-i/lesson-01/v2-stage/selected-cues.json"
LOWER_SECONDS = 75
UPPER_SECONDS = 99
SOURCE_VERSION = "intro-with-approved-cue-002-plus-greetings-v1"

def _verify_original_cue_two():
    cue = CUES[1]
    assert cue["order"] == 2 and cue["speaker"] == "MRS_UBUNTU"
    with engine.connect() as conn:
        row = conn.execute(select(recordings.c.source_sha256, recordings.c.audio_sha256,
                                  recordings.c.mp3).where(recordings.c.clip_id == cue["clip_id"])).first()
    if not row or row[0] != _hash(cue):
        raise RuntimeError("Approved instructor introduction source mismatch")
    data = bytes(row[2])
    if hashlib.sha256(data).hexdigest() != row[1]:
        raise RuntimeError("Instructor introduction clip audio checksum mismatch")
    return data

def _assemble_intro():
    clips = _read_verified()
    clips[2] = _verify_original_cue_two()
    with tempfile.TemporaryDirectory(prefix="ubuntu_intro_stage_") as tmp:
        root = pathlib.Path(tmp)
        pause = root / "pause.mp3"
        subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
                        "-f","lavfi","-i","anullsrc=r=24000:cl=mono","-t","0.35",
                        "-c:a","libmp3lame","-b:a","96k","-y",str(pause)],
                       check=True,capture_output=True,timeout=15)
        selected,playlist,total = [],[],0.0
        for n in [2]+list(range(3,86)):
            src = root / ("cue_%03d.mp3" % n)
            src.write_bytes(clips[n])
            proc = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                                   "-of","default=noprint_wrappers=1:nokey=1",str(src)],
                                  check=True,capture_output=True,text=True,timeout=15)
            dur = float(proc.stdout.strip())
            projected = total + dur + (0.35 if selected else 0)
            if n>10 and total >= LOWER_SECONDS and projected > 90:
                break
            if selected:
                playlist.append("file 'pause.mp3'")
                total += .35
            playlist.append("file '"+src.name+"'")
            selected.append(n)
            total += dur
            if total >= 90:
                break
        if not (LOWER_SECONDS <= total <= UPPER_SECONDS) or len(selected) < 12:
            raise RuntimeError("Instructor-led excerpt outside staged preview duration or cue count")
        (root/"playlist.txt").write_text("\n".join(playlist)+"\n",encoding="utf-8")
        out=root/"sample.mp3"
        subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-f","concat",
                        "-safe","1","-i",str(root/"playlist.txt"),"-c","copy","-y",str(out)],
                       check=True,capture_output=True,timeout=50)
        probe=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                              "-of","default=noprint_wrappers=1:nokey=1",str(out)],
                             check=True,capture_output=True,text=True,timeout=15)
        seconds=round(float(probe.stdout.strip()),2)
        if not (LOWER_SECONDS <= seconds <= UPPER_SECONDS):
            raise RuntimeError("Final stage preview outside allowed duration")
        return out.read_bytes(), seconds, selected

def _approved_manifest(data, seconds, selected):
    return {"version":SOURCE_VERSION,"status":"INTERNAL_F0_QA_ONLY",
            "commercial_release":False,"audio_seconds":seconds,
            "audio_bytes":len(data),"audio_sha256":hashlib.sha256(data).hexdigest(),
            "source_cue_orders":selected,
            "cues":[{"order":n,"speaker":CUES[n-1]["speaker"],
                     "voice":CUES[n-1]["azure_voice"],
                     "text":CUES[n-1]["text_to_speak"]} for n in selected]}

def stage_once():
    client=_r2_client()
    try:
        existing=client.get_object(Bucket=BUCKET,Key=MANIFEST_KEY)
        manifest=json.loads(existing["Body"].read())
        audio_head=client.head_object(Bucket=BUCKET,Key=KEY)
        if (manifest.get("version")==SOURCE_VERSION
                and manifest.get("commercial_release") is False
                and manifest.get("audio_bytes")==audio_head.get("ContentLength")
                and manifest.get("audio_sha256")==(audio_head.get("Metadata") or {}).get("sha256")):
            return {"state":"already_verified", "duration":manifest["audio_seconds"],"cues":len(manifest["cues"])}
        raise RuntimeError("Existing immutable staged sample does not match its manifest")
    except ClientError as exc:
        if str(exc.response.get("Error",{}).get("Code")) not in ("404","NoSuchKey","NotFound"):
            raise
    audio,seconds,selected=_assemble_intro()
    manifest=_approved_manifest(audio,seconds,selected)
    client.put_object(Bucket=BUCKET,Key=KEY,Body=audio,ContentType="audio/mpeg",
                      CacheControl="private, no-store",Metadata={"sha256":manifest["audio_sha256"],
                      "release":"f0-staging-only"})
    client.put_object(Bucket=BUCKET,Key=MANIFEST_KEY,Body=json.dumps(manifest,ensure_ascii=False).encode(),
                      ContentType="application/json",CacheControl="private, no-store")
    verified=client.head_object(Bucket=BUCKET,Key=KEY)
    if (verified["ContentLength"]!=len(audio) or
            (verified.get("Metadata") or {}).get("sha256")!=manifest["audio_sha256"]):
        raise RuntimeError("New staging preview object failed R2 identity readback")
    log.info("Ubuntu introduced-private-sample PASS sha256=%s bytes=%s duration=%s cues=%s",
             manifest["audio_sha256"],len(audio),seconds,len(selected))
    return {"state":"verified", "duration":seconds,"cues":len(selected)}

def _get_manifest():
    try:
        obj=_r2_client().get_object(Bucket=BUCKET,Key=MANIFEST_KEY)
        manifest=json.loads(obj["Body"].read())
        if manifest.get("version")!=SOURCE_VERSION or manifest.get("commercial_release") is not False:
            raise ValueError("Staging manifest identity mismatch")
        return manifest
    except (ClientError,BotoCoreError,ValueError) as exc:
        raise HTTPException(503,detail="Instructor-introduced private preview not yet staged") from exc

@router.get("/transcript")
def transcript():
    return _get_manifest()

@router.get("/listen.mp3")
def listen(request: Request):
    manifest=_get_manifest()
    try:
        obj=_r2_client().get_object(Bucket=BUCKET,Key=KEY)
        expected=int(manifest["audio_bytes"])
        body=obj["Body"].read(expected+1)
        if len(body)!=expected or hashlib.sha256(body).hexdigest()!=manifest["audio_sha256"]:
            raise ValueError("Staging sample failed SHA256 readback")
    except (ClientError,BotoCoreError,ValueError) as exc:
        raise HTTPException(502,detail="Private introduced sample unavailable") from exc
    headers={"Cache-Control":"private, no-store, max-age=0",
             "Content-Disposition":'inline; filename="UbuntuTalks_IntroReview.mp3"',
             "Accept-Ranges":"bytes","X-Robots-Tag":"noindex, nofollow",
             "X-Ubuntu-Audio-License":"F0-reference-QA-only"}
    raw=request.headers.get("range","")
    if raw:
        found=re.fullmatch(r"bytes=(\d*)-(\d*)",raw.strip())
        if not found or not (found.group(1) or found.group(2)):
            return Response(status_code=416,headers={**headers,"Content-Range":f"bytes */{len(body)}"})
        first,last=found.groups()
        if first:
            start=int(first);stop=int(last) if last else len(body)-1
        else:
            suffix=int(last)
            if not suffix:
                return Response(status_code=416,headers={**headers,"Content-Range":f"bytes */{len(body)}"})
            start=max(0,len(body)-suffix);stop=len(body)-1
        stop=min(stop,len(body)-1)
        if start>=len(body) or start>stop:
            return Response(status_code=416,headers={**headers,"Content-Range":f"bytes */{len(body)}"})
        return Response(content=body[start:stop+1],media_type="audio/mpeg",status_code=206,
                        headers={**headers,"Content-Range":f"bytes {start}-{stop}/{len(body)}"})
    return Response(content=body,media_type="audio/mpeg",headers=headers)
