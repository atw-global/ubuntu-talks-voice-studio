"""Streamable HTTP MCP session for Voice Studio.

Clients authenticate with their own bearer credential. The internal gateway
token is not read and is not returned.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from app.mcp.auth import authenticate, write_audit
from app.mcp.tools import call_tool, public_tool_definitions

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26")
PATH = "/api/ubuntu/mcp/v1"
_sessions: dict[str, dict] = {}


def _session(session_id: str, credential_id: str) -> dict | None:
    record = _sessions.get(session_id)
    if not record or record["credential_id"] != credential_id:
        return None
    if record["expires"] < datetime.now(timezone.utc):
        _sessions.pop(session_id, None)
        return None
    return record


def _origin_allowed(origin: str | None) -> bool:
    if not origin:
        return True
    allowed = [item.strip() for item in os.environ.get("UBUNTU_MCP_ALLOWED_ORIGINS", "").split(",") if item.strip()]
    return origin in allowed


def handle_http(method: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], bytes]:
    origin = headers.get("origin")
    if not _origin_allowed(origin):
        return 403, {"content-type": "application/json"}, b'{"error":"origin_not_allowed"}'
    if method == "GET":
        return 405, {"allow": "POST, DELETE", "content-type": "application/json"}, b'{"error":"sse_stream_not_offered"}'
    token = _bearer(headers.get("authorization", ""))
    credential = authenticate(token) if token else None
    if method == "DELETE":
        if not credential:
            write_audit(None, headers.get("mcp-session-id"), "DELETE", None, False, "unauthorized")
            return 401, _auth_headers(), b'{"error":"unauthorized"}'
        _sessions.pop(headers.get("mcp-session-id", ""), None)
        write_audit(credential["id"], headers.get("mcp-session-id"), "DELETE", None, True, "session_closed")
        return 204, {}, b""
    if method != "POST":
        return 405, {"allow": "POST, DELETE"}, b""
    if not credential:
        write_audit(None, None, "POST", None, False, "unauthorized")
        return 401, _auth_headers(), b'{"error":"unauthorized"}'
    try:
        message = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        write_audit(credential["id"], None, "POST", None, False, "invalid_json")
        return 400, {"content-type": "application/json"}, b'{"error":"invalid_json"}'
    if isinstance(message, list):
        responses = [_dispatch(item, credential, headers) for item in message]
        payload = [item for item in responses if item is not None]
        status = 202 if not payload else 200
        return status, {"content-type": "application/json"}, json.dumps(payload).encode("utf-8")
    response, status, extra = _dispatch_with_status(message, credential, headers)
    response_headers = {"content-type": "application/json", **extra}
    if response is None:
        return status, response_headers, b""
    return status, response_headers, json.dumps(response).encode("utf-8")


def _dispatch(message: dict, credential: dict, headers: dict[str, str]):
    response, _status, _extra = _dispatch_with_status(message, credential, headers)
    return response


def _dispatch_with_status(message: dict, credential: dict, headers: dict[str, str]):
    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid Request"), 200, {}
    method = str(message.get("method") or "")
    request_id = message.get("id")
    session_id = headers.get("mcp-session-id")
    notification = request_id is None or method.startswith("notifications/")
    if method == "initialize":
        new_session = uuid.uuid4().hex
        _sessions[new_session] = {
            "credential_id": credential["id"],
            "expires": datetime.now(timezone.utc) + timedelta(hours=12),
        }
        params = message.get("params") or {}
        requested = str(params.get("protocolVersion") or "")
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        write_audit(credential["id"], new_session, method, None, True, "initialized")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "ubuntu-talks-voice-studio", "version": "1.0.0"},
                "instructions": "Read tools are available to the default credential. Export, recording, attachment, and publication require a separate scope and still refuse unapproved audio.",
            },
        }, 200, {"mcp-session-id": new_session}
    if notification:
        write_audit(credential["id"], session_id, method, None, True, "notification")
        return None, 202, {}
    record = _session(session_id or "", credential["id"])
    if record is None:
        write_audit(credential["id"], session_id, method, None, False, "session_required")
        return _error(request_id, -32001, "Session required"), 404, {}
    if method == "ping":
        write_audit(credential["id"], session_id, method, None, True, "pong")
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}, 200, {}
    if method == "tools/list":
        write_audit(credential["id"], session_id, method, None, True, "listed")
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": public_tool_definitions()}}, 200, {}
    if method == "tools/call":
        params = message.get("params") or {}
        name = str(params.get("name") or "")
        result = call_tool(name, credential["scopes"])
        write_audit(credential["id"], session_id, method, name, bool(result.get("ok")), result.get("error") or "ok")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}],
                "structuredContent": result,
                "isError": not bool(result.get("ok")),
            },
        }, 200, {}
    write_audit(credential["id"], session_id, method, None, False, "method_not_found")
    return _error(request_id, -32601, "Method not found"), 200, {}


def _bearer(header: str) -> str:
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return value.strip()


def _auth_headers() -> dict[str, str]:
    return {"content-type": "application/json", "www-authenticate": 'Bearer realm="ubuntu-talks-voice-studio"'}


def _error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
