"""Capped, opt-in Azure neural voice audition; no course audio publication.

The studio's Nginx Basic Auth and server-only gateway token protect this route.
One user click creates one small evaluation-only MP3 using the configured F0/S0
Speech resource. No TTS worker or GPU is provisioned.
"""
from __future__ import annotations

import os
from xml.sax.saxutils import escape

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/api/ubuntu/azure", tags=["ubuntu-azure"])

SAMPLES = {
    "leah": {
        "voice": "en-ZA-LeahNeural",
        "locale": "en-ZA",
        "role": "Mrs Ubuntu (English narration)",
        "text": "Welcome to Lesson 1: Sounds, Greetings & Respect.",
    },
    "thando": {
        "voice": "zu-ZA-ThandoNeural",
        "locale": "zu-ZA",
        "role": "isiZulu speaker A",
        "text": "Sawubona, unjani?",
    },
    "themba": {
        "voice": "zu-ZA-ThembaNeural",
        "locale": "zu-ZA",
        "role": "isiZulu speaker B",
        "text": "Ngiyaphila, wena unjani?",
    },
}

def _credentials():
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if not key or not region:
        raise HTTPException(status_code=503, detail="Azure Speech credentials are not configured")
    if not region.replace("-", "").isalnum():
        raise HTTPException(status_code=503, detail="Invalid Azure Speech region")
    return key, region

@router.get("/status")
async def azure_status():
    if not os.environ.get("AZURE_SPEECH_KEY") or not os.environ.get("AZURE_SPEECH_REGION"):
        return {"configured": False, "verified": False, "available_samples": list(SAMPLES)}
    key, region = _credentials()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list",
                headers={"Ocp-Apim-Subscription-Key": key},
            )
        if res.status_code != 200:
            return {"configured": True, "verified": False, "upstream_status": res.status_code,
                    "available_samples": list(SAMPLES)}
        voices = res.json()
        present = {v.get("ShortName") for v in voices if isinstance(v, dict)}
        return {"configured": True, "verified": True,
                "available_samples": {k: {"voice": v["voice"], "supported": v["voice"] in present}
                                      for k, v in SAMPLES.items()},
                "billing": "No synthesis invoked by status check"}
    except (httpx.HTTPError, ValueError):
        return {"configured": True, "verified": False,
                "reason": "Azure voice list unavailable", "available_samples": list(SAMPLES)}

@router.post("/audition/{sample_id}")
async def audition(sample_id: str):
    if sample_id not in SAMPLES:
        raise HTTPException(status_code=404, detail="Unknown approved pilot sample")
    key, region = _credentials()
    sample = SAMPLES[sample_id]
    text = sample["text"][:240]
    xml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xml:lang="' + sample["locale"] + '"><voice name="' + sample["voice"] + '">'
        + escape(text) + '</voice></speak>'
    )
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            res = await client.post(
                f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                    "User-Agent": "UbuntuTalksVoiceStudio/1.0",
                },
                content=xml.encode("utf-8"),
            )
        if res.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Azure synthesis returned HTTP {res.status_code}")
        if not res.content:
            raise HTTPException(status_code=502, detail="Azure returned empty audio")
        return Response(
            content=res.content, media_type="audio/mpeg",
            headers={"Content-Disposition": f'inline; filename="ubuntu-lesson1-{sample_id}-audition.mp3"',
                     "Cache-Control": "private, no-store"},
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Azure synthesis unavailable") from exc


# Language-aware pronunciation QA: reproduce approved text exactly, but use a
# native zu-ZA voice for the embedded word "isiZulu" in English narration.
# Audition only: DO NOT overwrite saved 139-cue lesson audio without approval.
@router.post("/pronunciation-fix/{cue_number}")
async def pronunciation_fix(cue_number: int):
    if cue_number not in (1, 2):
        raise HTTPException(status_code=404, detail="Only first two narration cues are available for QA")
    import json
    import pathlib
    from xml.sax.saxutils import escape as escape_xml
    path = pathlib.Path(__file__).resolve().parents[2] / "data" / "lesson01_approved_139.json"
    source = json.loads(path.read_text(encoding="utf-8"))
    cue = source["spoken_cues"][cue_number - 1]
    assert cue["order"] == cue_number and cue["speaker"] == "MRS_UBUNTU"
    text = cue["text_to_speak"]
    parts = text.split("isiZulu")
    if len(parts) != 2:
        raise HTTPException(status_code=500, detail="Source cue has unexpected language mix")
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-ZA">'
        '<voice name="en-ZA-LeahNeural">' + escape_xml(parts[0]) + '</voice>'
        '<voice name="zu-ZA-ThandoNeural">isiZulu</voice>'
        '<voice name="en-ZA-LeahNeural">' + escape_xml(parts[1]) + '</voice>'
        '</speak>'
    )
    key, region = _credentials()
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
                content=ssml.encode("utf-8"),
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                    "User-Agent": "UbuntuTalksVoiceStudioPronunciationQA/1.0",
                },
            )
        if response.status_code != 200 or not response.content:
            raise HTTPException(status_code=502, detail=f"Azure returned HTTP {response.status_code}")
        return Response(
            content=response.content, media_type="audio/mpeg",
            headers={"Content-Disposition": f'inline; filename="lesson1-cue-{cue_number:04d}-pronunciation-qa.mp3"',
                     "Cache-Control": "private, no-store"},
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Azure synthesis unavailable") from exc


@router.post("/lesson1-english-guidance-demo")
async def lesson1_english_guidance_demo():
    """Generate Leah's English intro/outro, then join with the ALREADY
    RECORDED source-exact isiZulu cues 3-10. The previous Azure request
    placed 10 voices in one SSML document and Azure rejected it (HTTP 400).
    Each Azure request here has only one voice. No approved lesson clip is
    overwritten; join happens in temporary storage.
    """
    import asyncio
    import json
    import pathlib
    import subprocess
    import tempfile
    from xml.sax.saxutils import escape as esc

    from sqlalchemy import select
    from app.api.endpoints.lesson1_recording import engine, recordings, _hash

    manifest_path = pathlib.Path(__file__).resolve().parents[2] / "data" / "lesson01_approved_139.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cues = manifest["spoken_cues"][2:10]
    expected = ["ZULU_A", "ZULU_B", "ZULU_A", "ZULU_B",
                "ZULU_A", "ZULU_B", "ZULU_A", "ZULU_B"]
    if len(cues) != 8 or any(c["speaker"] != role or c["order"] != n
                             for n, (c, role) in enumerate(zip(cues, expected), 3)):
        raise HTTPException(status_code=500, detail="Approved Lesson 1 dialogue source mismatch")

    # Check database first. Do not make billable Azure calls if needed clips are missing.
    with engine.connect() as conn:
        rows = conn.execute(
            select(recordings.c.clip_id, recordings.c.source_sha256, recordings.c.mp3)
            .where(recordings.c.clip_id.in_([c["clip_id"] for c in cues]))
        ).all()
    saved = {row[0]: row for row in rows}
    missing = [c["order"] for c in cues if c["clip_id"] not in saved
               or saved[c["clip_id"]][1] != _hash(c)]
    if missing:
        raise HTTPException(status_code=409,
                            detail=f"Original dialogue clips not yet available: {missing}")

    intro = ("Welcome to Lesson One: Sounds, Greetings and Respect. "
             "Today, you will practise greeting one person, greeting a group, "
             "and answering politely. First, listen to our two speakers. "
             "Notice how their expressions change with the situation.")
    outro = ("Now you have heard the conversation. "
             "Next, we will break it down and practise each expression together.")
    key, region = _credentials()
    uri = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
        "User-Agent": "UbuntuTalksEnglishGuidanceQA/2.0",
    }

    async def synth_leah(client, english_text):
        ssml = ('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                'xml:lang="en-ZA"><voice name="en-ZA-LeahNeural">' +
                esc(english_text) + '</voice></speak>')
        response = await client.post(uri, content=ssml.encode("utf-8"), headers=headers)
        if response.status_code != 200 or not response.content:
            raise HTTPException(
                status_code=502,
                detail=f"Azure narrator-only synthesis returned HTTP {response.status_code}")
        return bytes(response.content)

    try:
        async with httpx.AsyncClient(timeout=50) as client:
            english_intro = await synth_leah(client, intro)
            await asyncio.sleep(3)
            english_outro = await synth_leah(client, outro)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Azure narrator synthesis unavailable") from exc

    def assemble():
        # Each saved clip is a standalone MP3 with the same output format.
        # Audio is temp-only; approved recordings in PostgreSQL stay immutable.
        with tempfile.TemporaryDirectory(prefix="ubuntu_voice_demo_") as folder:
            folder = pathlib.Path(folder)
            audio_parts = [english_intro] + [bytes(saved[c["clip_id"]][2]) for c in cues] + [english_outro]
            paths = []
            for i, blob in enumerate(audio_parts):
                path = folder / f"part_{i:02d}.mp3"
                path.write_bytes(blob)
                paths.append(path)
            pause = folder / "pause.mp3"
            # Brief gap at voice boundaries, preserving each original recording.
            make_pause = subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                 "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                 "-t", "0.45", "-c:a", "libmp3lame", "-b:a", "96k",
                 "-y", str(pause)],
                capture_output=True, timeout=20, check=False)
            if make_pause.returncode != 0:
                raise RuntimeError("Unable to generate short audio pause")
            # Build an ordered concat manifest, injecting a short gap between
            # finished utterances but never a change within an utterance.
            playlist = folder / "pieces.txt"
            lines = []
            for i, path in enumerate(paths):
                lines.append(f"file '{path.name}'")
                if i < len(paths) - 1:
                    lines.append("file 'pause.mp3'")
            playlist.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
            output = folder / "lesson1-sample.mp3"
            result = subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                 "-f", "concat", "-safe", "1", "-i", str(playlist),
                 "-c", "copy", "-y", str(output)],
                capture_output=True, timeout=30, check=False)
            if result.returncode != 0 or not output.is_file():
                raise RuntimeError("Unable to assemble the audio demo")
            return output.read_bytes()

    try:
        mp3 = await asyncio.to_thread(assemble)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(status_code=500, detail="Audio assembly failed") from exc
    if len(mp3) < 2000:
        raise HTTPException(status_code=500, detail="The assembled sample was unexpectedly short")
    return Response(
        content=mp3, media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="lesson1-english-guidance-demo.mp3"',
                 "Cache-Control": "private, no-store"},
    )
