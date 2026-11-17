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
