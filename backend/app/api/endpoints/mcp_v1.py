"""Versioned MCP endpoint on the existing Voice Studio API.

Reachable at /api/ubuntu/mcp/v1 on the API origin. StudioGateway does not
require the internal gateway token here; this route authenticates the MCP
credential itself and does not echo that credential.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.mcp.protocol import handle_http

router = APIRouter(tags=["ubuntu-mcp"])


@router.api_route("/api/ubuntu/mcp/v1", methods=["POST", "GET", "DELETE"])
async def mcp_v1(request: Request) -> Response:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    status, response_headers, payload = handle_http(request.method, headers, body)
    return Response(content=payload, status_code=status, headers=response_headers)
