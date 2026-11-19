"""Private immutable R2 archival of the verified isiZulu greeting excerpt.

This is an archival QA operation, NOT a public player. The source consists
only of approved already-recorded Azure cue MP3s. A public sample requires
native-language, Azure commercial-rights and storefront release clearance.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request

from app.api.endpoints.lesson1_archive import BUCKET, _r2_client
from app.api.endpoints.lesson1_sample import _assemble, _read_verified

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/sample/archive", tags=["ubuntu-lesson1-sample-archive"])
log = logging.getLogger(__name__)
KEY = "courses/zu/beginner-i/lesson-01/v1/sample-greetings-85s-qa.mp3"
EXPECTED_SHA256 = "d8a87dde1a3e92c3e6727e8dab2106eac1739a02e34597a1f6da6cb73640c7e0"
EXPECTED_BYTES = 1021292
_cached = {"state": "not_started", "verified": False, "error": None}
_lock = asyncio.Lock()


def _archive_sample():
    blob, duration, selected = _assemble(_read_verified())
    digest = hashlib.sha256(blob).hexdigest()
    if (digest != EXPECTED_SHA256 or len(blob) != EXPECTED_BYTES
            or not (55 <= duration <= 120) or len(selected) != 25):
        raise RuntimeError("Sample fails original verified source identity; refusing archive")
    client = _r2_client()
    try:
        prior = client.head_object(Bucket=BUCKET, Key=KEY)
        meta = prior.get("Metadata") or {}
        if (prior.get("ContentLength") != EXPECTED_BYTES
                or meta.get("sha256") != EXPECTED_SHA256
                or prior.get("ContentType") != "audio/mpeg"):
            raise RuntimeError("Existing R2 QA sample conflicts with source identity")
        return {"bytes": EXPECTED_BYTES, "duration_seconds": duration, "sha256": digest, "state": "verified"}
    except ClientError as exc:
        err = str(exc.response.get("Error", {}).get("Code", ""))
        if err not in {"404", "NoSuchKey", "NotFound"}:
            raise
    client.put_object(
        Bucket=BUCKET, Key=KEY, Body=blob, ContentType="audio/mpeg",
        CacheControl="private, no-store",
        Metadata={"sha256": digest, "cue-count": str(len(selected)),
                  "qa-status": "native-language-and-rights-pending"},
    )
    obj = client.head_object(Bucket=BUCKET, Key=KEY)
    if (obj.get("ContentLength") != EXPECTED_BYTES
            or (obj.get("Metadata") or {}).get("sha256") != digest
            or obj.get("ContentType") != "audio/mpeg"):
        raise RuntimeError("Uploaded QA sample failed R2 HEAD verification")
    return {"bytes": EXPECTED_BYTES, "duration_seconds": duration, "sha256": digest, "state": "verified"}


@router.get("/status")
def sample_archive_status():
    return {
        "bucket": BUCKET, "object_key": KEY,
        "expected_sha256": EXPECTED_SHA256, "expected_bytes": EXPECTED_BYTES,
        "credentials_configured": bool(os.environ.get("UBUNTU_R2_ACCESS_KEY_ID")
                                       and os.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY")),
        "state": _cached["state"], "upload_verified": _cached["verified"],
        "last_error": _cached["error"], "public_url": None,
        "whop_attached": False, "commercial_release_approved": False,
    }


@router.post("/upload")
async def upload_sample():
    async with _lock:
        if not (os.environ.get("UBUNTU_R2_ACCESS_KEY_ID")
                and os.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY")):
            raise HTTPException(503, detail="R2 private upload credentials not configured in Render backend")
        _cached.update({"state": "archiving", "error": None})
        try:
            receipt = await asyncio.to_thread(_archive_sample)
            _cached.update({"state": "verified", "verified": True, "error": None})
            log.info("Private R2 greetings sample QA archive verified sha256=%s bytes=%d",
                     receipt["sha256"], receipt["bytes"])
            return {**receipt, "bucket": BUCKET, "object_key": KEY,
                    "public_url": None, "commercial_release_approved": False}
        except (RuntimeError, ClientError, BotoCoreError) as exc:
            _cached.update({"state": "failed", "error": type(exc).__name__})
            log.exception("Private R2 greetings QA archive failed")
            raise HTTPException(502, detail="Private sample archival check failed") from exc


@router.get("/private-preview.mp3")
def play_private_archived_sample(request: Request):
    """Play immutable F0 reference in the already Basic-auth + gateway-locked Studio.

    Unlike qa-preview.mp3, no database clip lookup or ffmpeg rebuild happens
    during playback. This NEVER creates a public R2 URL or licenses the clip.
    """
    from fastapi.responses import Response
    try:
        obj = _r2_client().get_object(Bucket=BUCKET, Key=KEY)
        meta = obj.get("Metadata") or {}
        if (obj.get("ContentLength") != EXPECTED_BYTES
                or meta.get("sha256") != EXPECTED_SHA256):
            raise ValueError("Private R2 sample metadata mismatch")
        body = obj["Body"].read(EXPECTED_BYTES + 1)
        if len(body) != EXPECTED_BYTES or hashlib.sha256(body).hexdigest() != EXPECTED_SHA256:
            raise ValueError("Private R2 sample hash mismatch")
    except (ClientError, BotoCoreError, ValueError) as exc:
        log.error("Private preview read failed type=%s", type(exc).__name__)
        raise HTTPException(502, detail="Private reference sample not available") from exc
    from fastapi.responses import Response
    import re
    headers = {
        "Cache-Control": "private, no-store, max-age=0",
        "Content-Disposition": 'inline; filename="UbuntuTalks_Lesson1_InternalReview.mp3"',
        "Accept-Ranges": "bytes",
        "X-Ubuntu-Preview-Reference": "F0-private-QA-only",
        "X-Ubuntu-Preview-Seconds": "85.08",
        "X-Robots-Tag": "noindex, nofollow",
    }
    range_header = request.headers.get("range", "")
    if range_header:
        match = re.fullmatch(r"bytes=(\\d*)-(\\d*)", range_header.strip())
        if not match or not (match.group(1) or match.group(2)):
            return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{EXPECTED_BYTES}"})
        first, last = match.groups()
        if first:
            start = int(first)
            stop = int(last) if last else EXPECTED_BYTES - 1
        else:
            suffix = int(last)
            if not suffix:
                return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{EXPECTED_BYTES}"})
            start, stop = max(0, EXPECTED_BYTES - suffix), EXPECTED_BYTES - 1
        stop = min(stop, EXPECTED_BYTES - 1)
        if start >= EXPECTED_BYTES or start > stop:
            return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{EXPECTED_BYTES}"})
        return Response(content=body[start:stop+1], media_type="audio/mpeg", status_code=206,
                        headers={**headers, "Content-Range": f"bytes {start}-{stop}/{EXPECTED_BYTES}"})
    return Response(content=body, media_type="audio/mpeg", headers=headers)
