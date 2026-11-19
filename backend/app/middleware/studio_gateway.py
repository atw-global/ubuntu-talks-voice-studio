"""Protect Render's public backend origin from direct unauthenticated access.

The OpenSpeakers frontend at Ubuntu Talks Voice Studio authenticates visitors,
then its Nginx proxy supplies the separate server-side gateway token.
Neither the browser nor a JavaScript asset receives the token.
"""
from __future__ import annotations

import os
import secrets

from starlette.responses import JSONResponse

from app.mcp.oauth import PUBLIC_PATHS

GATEWAY_EXEMPT = PUBLIC_PATHS | {"/health"}


class StudioGateway:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        typ = scope.get("type")
        if typ not in {"http", "websocket"}:
            return await self.application(scope, receive, send)

        # Health, the MCP route, and the OAuth discovery routes authenticate
        # themselves. Every other route keeps the internal gateway token.
        if typ == "http" and scope.get("path") in GATEWAY_EXEMPT:
            return await self.application(scope, receive, send)

        expected = os.environ.get("STUDIO_BACKEND_GATEWAY_TOKEN", "")
        supplied = ""
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-voice-studio-internal-key":
                supplied = value.decode("utf-8", errors="replace")
                break

        if not (expected and supplied and secrets.compare_digest(expected, supplied)):
            if typ == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return
            return await JSONResponse(
                {"error": "Not authorized to access the Ubuntu Talks Voice Studio backend."},
                status_code=403,
            )(scope, receive, send)

        # Do not accept mutating API requests before a real speech worker is
        # installed and explicitly enabled. This prevents orphaned Celery jobs.
        if typ == "http" and scope.get("path", "").startswith(("/api/", "/v1/")):
            if scope.get("method", "GET").upper() not in {"GET", "HEAD", "OPTIONS"}:
                if (scope.get("path", "") not in {"/api/ubuntu/azure/audition/leah", "/api/ubuntu/azure/audition/thando", "/api/ubuntu/azure/audition/themba", "/api/ubuntu/azure/lesson1/start", "/api/ubuntu/azure/lesson1/master/start", "/api/ubuntu/azure/lesson1/archive/upload", "/api/ubuntu/azure/lesson1/sample/archive/upload", "/api/ubuntu/whop/course-factory/cover/apply", "/api/ubuntu/azure/pronunciation-fix/1", "/api/ubuntu/azure/pronunciation-fix/2", "/api/ubuntu/azure/lesson1-english-guidance-demo"} and os.environ.get("VOICE_STUDIO_GENERATION_ENABLED", "false").lower() != "true"):
                    return await JSONResponse(
                        {"error": "Speech generation is not enabled; GPU worker is not connected."},
                        status_code=503,
                    )(scope, receive, send)

        return await self.application(scope, receive, send)
