"""Visitor and enrolled access for the Lesson 1 classroom.

Enrollment is a Whop membership read. A header, a hidden button, or a missing
API key never counts as access. Paid stage bodies are omitted until the
membership matches the Everyday isiZulu plan.
"""
from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.lesson1_learning import (
    access_catalog,
    membership_header_accepted,
    membership_record_grants,
    resolve_stage,
)

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/classroom", tags=["ubuntu-lesson1-classroom"])
log = logging.getLogger(__name__)
WHOP_ORIGIN = "https://api.whop.com/api/v1"
API_VERSION = "2026-11-17-3"


def _enrolled(request: Request) -> bool:
    raw = request.headers.get("x-ubuntu-membership-id", "").strip()
    token = os.environ.get("WHOP_API_KEY", "").strip()
    if not membership_header_accepted(raw) or not token:
        return False
    try:
        response = httpx.get(
            WHOP_ORIGIN + "/memberships/" + raw,
            headers={
                "Authorization": "Bearer " + token,
                "Api-Version-Date": API_VERSION,
                "Accept": "application/json",
            },
            timeout=15.0,
        )
    except httpx.HTTPError:
        log.warning("Lesson 1 membership lookup failed before a Whop response")
        return False
    if response.status_code != 200:
        log.info("Lesson 1 membership lookup status=%s", response.status_code)
        return False
    try:
        record = response.json()
    except ValueError:
        return False
    return isinstance(record, dict) and membership_record_grants(record)


@router.get("/access")
def access(request: Request):
    body = access_catalog()
    body["enrolled"] = _enrolled(request)
    return body


@router.get("/stages/{stage_id}")
def stage(stage_id: str, request: Request):
    status, body = resolve_stage(stage_id, _enrolled(request))
    if status != 200:
        return JSONResponse(status_code=status, content=body)
    return body
