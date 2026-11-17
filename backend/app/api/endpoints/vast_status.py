"""Read-only Vast.ai credential validation for Ubuntu Talks Voice Studio.

No endpoints in this module can create, start, stop, rent, or delete GPU instances.
The outer StudioGateway rejects unauthenticated calls before they reach this router.
"""
from __future__ import annotations

import os

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/ubuntu/vast", tags=["ubuntu-vast"])


@router.get("/status")
async def vast_status():
    api_key = os.environ.get("VAST_API_KEY", "").strip()
    if not api_key:
        return JSONResponse(
            {"connected": False, "reason": "VAST_API_KEY not configured",
             "gpu_provisioning_enabled": False},
            status_code=200,
        )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://console.vast.ai/api/v0/users/current/",
                headers={"Authorization": f"Bearer {api_key}"},
            )

        if response.status_code != 200:
            return JSONResponse(
                {"connected": False, "reason": "Vast.ai rejected the credential",
                 "upstream_status": response.status_code,
                 "gpu_provisioning_enabled": False},
                status_code=200,
            )

        data = response.json()
        return {
            "connected": True,
            "account_id": data.get("id"),
            "gpu_provisioning_enabled": False,
            "mode": "read_only",
        }
    except (httpx.HTTPError, ValueError):
        return JSONResponse(
            {"connected": False, "reason": "Vast.ai check unavailable",
             "gpu_provisioning_enabled": False},
            status_code=200,
        )
