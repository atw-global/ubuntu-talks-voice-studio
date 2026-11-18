"""Narrow, backend-only Whop integration for the new hidden isiZulu pilot.

Unlike browser automation, this uses a company API key stored in Render.
Never returns tokens, media upload destinations, or other secrets to clients.
It does not change the new course's visibility or touch legacy products.
"""
from __future__ import annotations

import hashlib
import logging
import os
import struct
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/ubuntu/whop/course-factory", tags=["ubuntu-whop-course-factory"])
log = logging.getLogger(__name__)

ACCOUNT = "biz_E1ClvLpPiPOdSj"
PRODUCT = "prod_EBSCxcpCQvcgI"
LESSON = "lesn_p61ZUtWXJkEie"
HD_URL = "https://cdn.shopify.com/s/files/1/0712/9500/8877/files/ubuntu-talks-everyday-isizulu-beginner-i-hd.png?v=1795026974"
FILE_NAME = "ubuntu-talks-everyday-isizulu-beginner-i-hd.png"
EXPECTED_WIDTH = 1672
EXPECTED_HEIGHT = 941
MIN_IMAGE_BYTES = 500_000
MAX_IMAGE_BYTES = 8_000_000
WHOP_ORIGIN = "https://api.whop.com/api/v1"
API_VERSION = "2026-11-17-3"


def _token():
    token = os.environ.get("WHOP_API_KEY", "").strip()
    if not token:
        raise HTTPException(status_code=503, detail="Dedicated Whop company API key not configured on Render")
    return token


def _headers():
    return {"Authorization": "Bearer " + _token(),
            "Api-Version-Date": API_VERSION, "Accept": "application/json"}


def _request(client: httpx.Client, method: str, path: str, *, json=None):
    if not path.startswith("/") or ".." in path:
        raise RuntimeError("Unsafe Whop API path")
    try:
        response = client.request(method, WHOP_ORIGIN + path,
                                  headers=_headers(), json=json, timeout=20.0)
    except httpx.HTTPError as exc:
        raise HTTPException(502, detail="Whop network unavailable") from exc
    if response.status_code in (401, 403):
        raise HTTPException(502, detail="Whop key missing required company or resource permission")
    if response.status_code >= 400:
        log.error("Whop factory API %s %s status=%d", method, path, response.status_code)
        raise HTTPException(502, detail="Whop API request failed")
    return response.json()


def _product(client: httpx.Client):
    data = _request(client, "GET", "/products/" + PRODUCT)
    if data.get("id") != PRODUCT or data.get("account", {}).get("id") != ACCOUNT:
        raise HTTPException(409, detail="Product identity and account binding mismatch")
    if data.get("visibility") != "hidden":
        raise HTTPException(409, detail="Refusing media operations on public product")
    return data


def _load_approved_image(client: httpx.Client):
    # Fixed host and path, not caller-supplied input: prevents SSRF.
    url = urlparse(HD_URL)
    if url.scheme != "https" or url.netloc != "cdn.shopify.com":
        raise HTTPException(500, detail="Approved artwork source configuration invalid")
    try:
        response = client.get(HD_URL, follow_redirects=False, timeout=25.0)
        response.raise_for_status()
        blob = response.content
    except httpx.HTTPError as exc:
        raise HTTPException(502, detail="Approved HD image source unavailable") from exc
    if not (MIN_IMAGE_BYTES <= len(blob) <= MAX_IMAGE_BYTES):
        raise HTTPException(422, detail="Image size outside verified HD cover limits")
    if not blob.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
        raise HTTPException(422, detail="Artwork source is not PNG")
    width, height = struct.unpack(">II", blob[16:24])
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        raise HTTPException(422, detail="Artwork dimensions do not match approved source")
    return blob


@router.get("/status")
def status():
    """Credential presence and *read-only* Whop product identity verification."""
    if not os.environ.get("WHOP_API_KEY"):
        return {"credentials_configured": False, "connection_verified": False,
                "product_id": PRODUCT, "lesson_id": LESSON,
                "expected_visibility": "hidden", "ready_for_cover_upload": False}
    with httpx.Client() as client:
        item = _product(client)
    gallery = item.get("gallery_images") or []
    return {"credentials_configured": True, "connection_verified": True,
            "product_id": PRODUCT, "product_visibility": item.get("visibility"),
            "product_gallery_file_ids": [x.get("id") for x in gallery],
            "lesson_id": LESSON, "ready_for_cover_upload": True}


@router.post("/cover/apply")
def apply_approved_cover():
    """Explicitly invoked, narrow replacement of this single approved product cover.

    Preserves any other gallery images while replacing the known blurry source.
    Never automatically publishes any product or lesson.
    """
    with httpx.Client() as client:
        before = _product(client)
        gallery = before.get("gallery_images") or []
        if any((entry.get("filename") == FILE_NAME) for entry in gallery):
            return {"status": "already_present", "product_id": PRODUCT,
                    "product_visibility": "hidden"}
        blob = _load_approved_image(client)
        digest = hashlib.sha256(blob).hexdigest()
        file_info = _request(client, "POST", "/files",
                             json={"filename": FILE_NAME, "byte_size": len(blob),
                                   "visibility": "public"})
        file_id = file_info.get("id")
        upload_url = file_info.get("upload_url")
        if not (isinstance(file_id, str) and file_id.startswith("file_")
                and isinstance(upload_url, str)):
            raise HTTPException(502, detail="Whop did not return a direct-upload file destination")
        parsed = urlparse(upload_url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise HTTPException(502, detail="Invalid Whop presigned upload destination")
        # Do not forward the bearer API key to the presigned storage URL.
        upload_headers = file_info.get("upload_headers") or {}
        try:
            put = client.put(upload_url, content=blob, headers=upload_headers, timeout=45.0)
            put.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(502, detail="Whop direct image upload did not complete") from exc
        after_file = _request(client, "GET", "/files/" + file_id)
        if after_file.get("id") != file_id or after_file.get("upload_status") != "ready":
            raise HTTPException(502, detail="Whop image upload not yet verified ready")
        retained = [{"id": x["id"]} for x in gallery
                    if x.get("id") and x.get("id") != "file_YrbXTD2X1rWSC"]
        _request(client, "PATCH", "/products/" + PRODUCT,
                 json={"gallery_images": [{"id": file_id}] + retained})
        readback = _product(client)
        files = [x.get("id") for x in readback.get("gallery_images") or []]
        if file_id not in files:
            raise HTTPException(502, detail="Whop gallery readback did not contain approved artwork")
    log.info("Whop hidden product HD gallery verified product=%s file=%s sha256=%s bytes=%d",
             PRODUCT, file_id, digest, len(blob))
    return {"status": "verified", "product_id": PRODUCT,
            "new_file_id": file_id, "bytes": len(blob), "sha256": digest,
            "width": EXPECTED_WIDTH, "height": EXPECTED_HEIGHT,
            "product_visibility": "hidden", "public_course_released": False}
