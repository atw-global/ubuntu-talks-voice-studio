"""OAuth discovery, registration, consent, token, and revocation routes.

These paths are exempt from the internal gateway token. They never read or
return that token, the bootstrap token, or the owner password.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from app.mcp.oauth import (
    authorization_page,
    authorization_server_metadata,
    exchange_token,
    parse_form,
    protected_resource_metadata,
    register_client,
    revoke_token,
    submit_authorization,
)

router = APIRouter(tags=["ubuntu-mcp-oauth"])


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/api/ubuntu/mcp/v1")
def protected_resource() -> JSONResponse:
    return JSONResponse(protected_resource_metadata(), headers={"cache-control": "public, max-age=300"})


@router.get("/.well-known/oauth-authorization-server")
def authorization_server() -> JSONResponse:
    return JSONResponse(authorization_server_metadata(), headers={"cache-control": "public, max-age=300"})


@router.post("/oauth/register")
async def register(request: Request) -> JSONResponse:
    status, payload = register_client(parse_form(await request.body(), request.headers.get("content-type", "")))
    return JSONResponse(payload, status_code=status, headers={"cache-control": "no-store"})


@router.get("/oauth/authorize")
def authorize_form(request: Request) -> Response:
    status, _content_type, body = authorization_page(dict(request.query_params))
    return Response(content=body, status_code=status, media_type="text/html", headers={"cache-control": "no-store"})


@router.post("/oauth/authorize")
async def authorize_submit(request: Request) -> Response:
    params = parse_form(await request.body(), request.headers.get("content-type", ""))
    remote = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded and len(forwarded) <= 64 and all(character.isalnum() or character in ".:_" for character in forwarded):
        remote = forwarded
    status, headers, body = submit_authorization(params, remote)
    headers.setdefault("cache-control", "no-store")
    return Response(content=body, status_code=status, headers=headers)


@router.post("/oauth/token")
async def token(request: Request) -> JSONResponse:
    status, payload = exchange_token(parse_form(await request.body(), request.headers.get("content-type", "")))
    return JSONResponse(payload, status_code=status, headers={"cache-control": "no-store"})


@router.post("/oauth/revoke")
async def revoke(request: Request) -> Response:
    revoke_token(parse_form(await request.body(), request.headers.get("content-type", "")))
    return Response(status_code=200, headers={"cache-control": "no-store"})
