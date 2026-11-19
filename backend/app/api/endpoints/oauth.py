"""OAuth discovery and token routes for the existing Voice Studio API."""
from __future__ import annotations

import json
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.mcp.oauth import (
    authorization_server_metadata,
    authorize_page,
    exchange_token,
    protected_resource_metadata,
    register_client,
    revoke_token,
    submit_authorization,
)

router = APIRouter(tags=["ubuntu-mcp-oauth"])


def _form(raw: bytes) -> dict[str, str]:
    parsed = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def _query(request: Request) -> dict[str, str]:
    return {key: values[-1] for key, values in parse_qs(request.url.query, keep_blank_values=True).items()}


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/{resource_path:path}")
async def protected_resource(resource_path: str = "") -> JSONResponse:
    document = protected_resource_metadata()
    if resource_path and resource_path != "api/ubuntu/mcp/v1":
        return JSONResponse({"error": "unknown_resource"}, status_code=404)
    return JSONResponse(document)


@router.get("/.well-known/oauth-authorization-server")
async def authorization_server() -> JSONResponse:
    return JSONResponse(authorization_server_metadata())


@router.post("/oauth/register")
async def register(request: Request) -> JSONResponse:
    try:
        body = json.loads((await request.body()).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JSONResponse({"error": "invalid_client_metadata"}, status_code=400)
    status, payload = register_client(body)
    return JSONResponse(payload, status_code=status)


@router.get("/oauth/authorize")
async def authorize_get(request: Request) -> HTMLResponse:
    status, page = authorize_page(_query(request))
    return HTMLResponse(page, status_code=status)


@router.post("/oauth/authorize")
async def authorize_post(request: Request) -> Response:
    status, page, location = submit_authorization(_form(await request.body()))
    if location:
        return RedirectResponse(location, status_code=status)
    return HTMLResponse(page, status_code=status)


@router.post("/oauth/token")
async def token(request: Request) -> JSONResponse:
    status, payload = exchange_token(_form(await request.body()))
    return JSONResponse(payload, status_code=status, headers={"cache-control": "no-store"})


@router.post("/oauth/revoke")
async def revoke(request: Request) -> Response:
    revoke_token(_form(await request.body()).get("token", ""))
    return Response(status_code=200)
