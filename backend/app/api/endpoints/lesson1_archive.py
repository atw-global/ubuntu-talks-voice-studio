"""Secure, hash-verified R2 archive for the private Lesson 1 QA master.

Requires pre-existing least-privilege R2 credentials in Render *backend only*.
No public URLs are generated or returned. The Whop publishing gate stays closed.
"""
from __future__ import annotations
import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from botocore.exceptions import BotoCoreError, ClientError
import boto3
from app.api.endpoints.lesson1_master import VERSION, _init, masters, engine

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/archive", tags=["ubuntu-lesson1-archive"])
log = logging.getLogger(__name__)
BUCKET = "ubuntu-talks-instructor-masters"
KEY = "courses/zu/beginner-i/lesson-01/v1/master.mp3"
ACCOUNT_ID = "4776967df1db80c2a31141343cd113c1"
EXPECTED_SHA256 = "ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a"
_cached = {"state": "not_started", "error": None, "verified": False}
_lock = asyncio.Lock()

def _r2_client():
    access = os.environ.get("UBUNTU_R2_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY", "").strip()
    if not access or not secret:
        raise RuntimeError("Dedicated R2 upload credentials not configured")
    return boto3.client("s3", endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=access, aws_secret_access_key=secret,
        region_name="auto")

def _read_source():
    _init()
    with engine.connect() as conn:
        item = conn.execute(select(
            masters.c.sha256, masters.c.mp3, masters.c.size_bytes, masters.c.cue_count)
            .where(masters.c.version == VERSION)).first()
    if not item:
        raise RuntimeError("Approved source audio master missing")
    checksum, blob, size, count = item
    blob = bytes(blob)
    if (checksum != EXPECTED_SHA256 or hashlib.sha256(blob).hexdigest() != EXPECTED_SHA256
            or len(blob) != size or count != 139):
        raise RuntimeError("Source master failed SHA256 / size / cue-count verification")
    return blob

def _archive():
    blob = _read_source()
    client = _r2_client()
    # No overwrite without verifying existing asset. Immutable v1 key.
    try:
        old = client.head_object(Bucket=BUCKET, Key=KEY)
        metadata = old.get("Metadata") or {}
        if old.get("ContentLength") != len(blob) or metadata.get("sha256") != EXPECTED_SHA256:
            raise RuntimeError("Existing v1 R2 object differs from approved source; refusing overwrite")
        return {"state": "verified", "sha256": EXPECTED_SHA256, "bytes": len(blob)}
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code not in {"404", "NoSuchKey", "NotFound"}:
            raise
    client.put_object(Bucket=BUCKET, Key=KEY, Body=blob, ContentType="audio/mpeg",
        Metadata={"sha256": EXPECTED_SHA256, "source": "ubuntu-lesson01-approved-139"},
        CacheControl="private, no-store")
    head = client.head_object(Bucket=BUCKET, Key=KEY)
    if (head.get("ContentLength") != len(blob)
            or (head.get("Metadata") or {}).get("sha256") != EXPECTED_SHA256
            or head.get("ContentType") != "audio/mpeg"):
        raise RuntimeError("R2 object readback mismatch")
    # R2 ETag is not necessarily the SHA256: SHA256 is independently calculated
    # from bytes before upload and carried as metadata verified by HEAD.
    return {"state": "verified", "sha256": EXPECTED_SHA256, "bytes": len(blob)}

@router.get("/status")
def status():
    return {"bucket": BUCKET, "object_key": KEY, "source_sha256": EXPECTED_SHA256,
        "credentials_configured": bool(os.environ.get("UBUNTU_R2_ACCESS_KEY_ID") and
                                      os.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY")),
        "upload_verified": _cached["verified"], "state": _cached["state"],
        "last_error": _cached["error"],
        "public_url": None, "whop_attached": False, "commercial_release_approved": False}

@router.post("/upload")
async def upload():
    async with _lock:
        if not (os.environ.get("UBUNTU_R2_ACCESS_KEY_ID") and
                os.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY")):
            raise HTTPException(503, detail="R2 private upload credentials not configured in Render backend")
        _cached.update({"state": "archiving", "error": None})
        try:
            receipt = await asyncio.to_thread(_archive)
            _cached.update({"state": "verified", "verified": True, "error": None})
            log.info("Private R2 Lesson 1 archive verified: bytes=%d sha256=%s",
                     receipt["bytes"], receipt["sha256"])
            return {**receipt, "bucket": BUCKET, "object_key": KEY, "public_url": None}
        except (RuntimeError, ClientError, BotoCoreError) as err:
            _cached.update({"state": "failed", "error": str(err)[:240]})
            log.exception("R2 Lesson 1 archive failed")
            raise HTTPException(502, detail="R2 archival verification failed; check API log") from err
