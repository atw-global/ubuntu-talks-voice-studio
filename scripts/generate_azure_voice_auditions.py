#!/usr/bin/env python3
"""Generate *evaluation-only* MP3s from approved source-locked SSML.

Requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in the environment.
This is intentionally a manual, small audition script; it does not touch
existing Ubuntu lesson voice mappings or automatically publish course audio.

Usage:
    AZURE_SPEECH_KEY=... AZURE_SPEECH_REGION=eastus \\
      python scripts/generate_azure_voice_auditions.py

Do not commit credentials or generated MP3s to Git.
"""
from __future__ import annotations

import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDITIONS = ROOT / "auditions" / "isiZulu-beginner-I"
OUTPUT = AUDITIONS / "local-output"
VOICES = ("en-ZA-LeahNeural", "zu-ZA-ThandoNeural", "zu-ZA-ThembaNeural")


def main() -> None:
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if not key or not region:
        raise SystemExit("Missing AZURE_SPEECH_KEY or AZURE_SPEECH_REGION.")
    if not region.replace("-", "").isalnum():
        raise SystemExit("Invalid Azure region.")
    endpoint = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in VOICES:
        payload = (AUDITIONS / (name + ".ssml")).read_bytes()
        request = urllib.request.Request(
            endpoint, data=payload, method="POST",
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                "User-Agent": "UbuntuTalksVoiceStudio-Audition",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                audio = response.read()
        except urllib.error.HTTPError as error:
            # Do not print response headers or any secret-bearing details.
            raise SystemExit(f"{name}: Azure returned HTTP {error.code}") from None
        if not audio:
            raise SystemExit(f"{name}: Azure returned an empty audio response.")
        file = OUTPUT / (name + ".mp3")
        file.write_bytes(audio)
        print(f"{name}: saved {file.relative_to(ROOT)} ({len(audio)} bytes)")
    print("Evaluation clips only. Obtain voice and language QA before publication.")


if __name__ == "__main__":
    main()
