"""OAuth 2.1 PKCE for ChatGPT against the Voice Studio MCP endpoint."""
import asyncio
import base64
import hashlib
import json
import os
import secrets
import tempfile
from urllib.parse import parse_qs, urlsplit

_database_fd, _database_path = tempfile.mkstemp(prefix="ubuntu-oauth-", suffix=".sqlite")
os.close(_database_fd)
os.environ["UBUNTU_MCP_DATABASE_URL"] = "sqlite:///" + _database_path
os.environ["UBUNTU_MCP_PUBLIC_ORIGIN"] = "https://ubuntu-talks-voice-studio-api.onrender.com"
os.environ["UBUNTU_MCP_OAUTH_OWNER_SECRET"] = "owner-secret-for-test"
os.environ["STUDIO_BACKEND_GATEWAY_TOKEN"] = "gateway-secret-for-test"

from fastapi import FastAPI

from app.api.endpoints.mcp_v1 import router as mcp_router
from app.api.endpoints.oauth import router as oauth_router
from app.middleware.studio_gateway import StudioGateway

OWNER = os.environ["UBUNTU_MCP_OAUTH_OWNER_SECRET"]
GATEWAY = os.environ["STUDIO_BACKEND_GATEWAY_TOKEN"]
ORIGIN = os.environ["UBUNTU_MCP_PUBLIC_ORIGIN"]
app = StudioGateway(FastAPI())
app.application.include_router(oauth_router)
app.application.include_router(mcp_router)


def _asgi(method, path, body=b"", headers=None, query=""):
    sent = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "https", "path": path, "raw_path": path.encode(),
        "query_string": query.encode(), "client": ("127.0.0.1", 9), "server": ("studio", 443),
        "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
    }
    asyncio.run(app(scope, receive, send))
    status = 0
    response_headers = {}
    payload = b""
    for message in sent:
        if message["type"] == "http.response.start":
            status = message["status"]
            response_headers = {key.decode().lower(): value.decode() for key, value in message["headers"]}
        elif message["type"] == "http.response.body":
            payload += message.get("body", b"")
    return status, response_headers, payload


def _json(method, path, payload=None, headers=None, query=""):
    body = b"" if payload is None else json.dumps(payload).encode()
    sent_headers = {"content-type": "application/json", **(headers or {})}
    status, response_headers, raw = _asgi(method, path, body, sent_headers, query)
    return status, response_headers, json.loads(raw.decode() or "null")


def _form(path, fields):
    from urllib.parse import urlencode
    status, headers, raw = _asgi("POST", path, urlencode(fields).encode(), {"content-type": "application/x-www-form-urlencoded"})
    return status, headers, raw


def _challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _register():
    status, _headers, body = _json("POST", "/oauth/register", {
        "client_name": "ChatGPT",
        "redirect_uris": ["https://chatgpt.com/connector_platform_oauth_redirect"],
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
    })
    assert status == 201, body
    assert "client_secret" not in body
    return body["client_id"]


def test_discovery_is_public_and_other_routes_stay_behind_the_gateway():
    status, headers, body = _json("GET", "/.well-known/oauth-protected-resource")
    assert status == 200
    assert body["resource"].endswith("/api/ubuntu/mcp/v1")
    assert body["authorization_servers"] == [ORIGIN]
    assert body["scopes_supported"] == ["read", "verify"]
    path_status, _headers, path_body = _json("GET", "/.well-known/oauth-protected-resource/api/ubuntu/mcp/v1")
    assert path_status == 200 and path_body["resource"] == body["resource"]
    server_status, _headers, server = _json("GET", "/.well-known/oauth-authorization-server")
    assert server_status == 200
    assert server["code_challenge_methods_supported"] == ["S256"]
    assert server["registration_endpoint"].endswith("/oauth/register")
    assert "export" not in server["scopes_supported"]
    blocked, _headers, blocked_body = _json("GET", "/api/ubuntu/azure/lesson1/master/start")
    assert blocked == 403 and GATEWAY not in json.dumps(blocked_body)
    missing, mcp_headers, _payload = _asgi("POST", "/api/ubuntu/mcp/v1", b"{}", {})
    assert missing == 401
    assert "resource_metadata=" in mcp_headers["www-authenticate"]
    assert GATEWAY not in mcp_headers["www-authenticate"]


def test_missing_owner_secret_issues_no_code():
    client_id = _register()
    verifier = secrets.token_urlsafe(48)
    saved = os.environ.pop("UBUNTU_MCP_OAUTH_OWNER_SECRET")
    try:
        status, _headers, body = _form("/oauth/authorize", {
            "response_type": "code", "client_id": client_id,
            "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
            "code_challenge": _challenge(verifier), "code_challenge_method": "S256",
            "scope": "read verify", "owner_secret": saved,
        })
    finally:
        os.environ["UBUNTU_MCP_OAUTH_OWNER_SECRET"] = saved
    assert status == 503 and b"code=" not in body and saved.encode() not in body


def test_unknown_client_and_bad_redirect_are_refused():
    status, _headers, body = _json("POST", "/oauth/register", {
        "redirect_uris": ["https://evil.example/steal"],
        "token_endpoint_auth_method": "none",
    })
    assert status == 400 and body["error"] == "invalid_redirect_uri"
    status, _headers, body = _json("POST", "/oauth/register", {
        "redirect_uris": ["https://chatgpt.com/callback"],
        "token_endpoint_auth_method": "client_secret_basic",
    })
    assert status == 400 and body["error"] == "invalid_client_metadata"


def test_owner_must_approve_before_chatgpt_can_call_studio_health():
    client_id = _register()
    verifier = secrets.token_urlsafe(48)
    query = (
        "response_type=code&client_id=" + client_id
        + "&redirect_uri=https://chatgpt.com/connector_platform_oauth_redirect"
        + "&code_challenge=" + _challenge(verifier)
        + "&code_challenge_method=S256&state=csrf-state&scope=read%20verify"
    )
    page_status, _headers, page = _asgi("GET", "/oauth/authorize", query=query)
    assert page_status == 200 and b"Owner secret" in page and OWNER.encode() not in page
    denied, _headers, denied_body = _form("/oauth/authorize", {
        "response_type": "code", "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "code_challenge": _challenge(verifier), "code_challenge_method": "S256",
        "state": "csrf-state", "scope": "read verify", "owner_secret": "wrong",
    })
    assert denied == 401 and b"code=" not in denied_body and OWNER.encode() not in denied_body
    broad, _headers, broad_body = _form("/oauth/authorize", {
        "response_type": "code", "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "code_challenge": _challenge(verifier), "code_challenge_method": "S256",
        "scope": "read admin", "owner_secret": OWNER,
    })
    assert broad == 400 and b"read and verify" in broad_body
    approved, headers, _body = _form("/oauth/authorize", {
        "response_type": "code", "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "code_challenge": _challenge(verifier), "code_challenge_method": "S256",
        "state": "csrf-state", "scope": "read verify", "owner_secret": OWNER,
    })
    assert approved == 302
    location = headers["location"]
    parsed = parse_qs(urlsplit(location).query)
    assert parsed["state"] == ["csrf-state"]
    assert OWNER not in location and GATEWAY not in location
    bad_verifier, _headers, bad_body = _form("/oauth/token", {
        "grant_type": "authorization_code", "code": parsed["code"][0], "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "code_verifier": secrets.token_urlsafe(48),
    })
    assert bad_verifier == 400 and json.loads(bad_body)["error"] == "invalid_grant"
    approved, headers, _body = _form("/oauth/authorize", {
        "response_type": "code", "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "code_challenge": _challenge(verifier), "code_challenge_method": "S256",
        "state": "csrf-state", "scope": "read verify", "owner_secret": OWNER,
    })
    code = parse_qs(urlsplit(headers["location"]).query)["code"][0]
    token_status, _headers, token_body = _form("/oauth/token", {
        "grant_type": "authorization_code", "code": code, "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "code_verifier": verifier,
    })
    assert token_status == 200, token_body
    issued = json.loads(token_body)
    assert issued["scope"] == "read verify" and issued["token_type"] == "Bearer"
    reused, _headers, reused_body = _form("/oauth/token", {
        "grant_type": "authorization_code", "code": code, "client_id": client_id,
        "redirect_uri": "https://chatgpt.com/connector_platform_oauth_redirect",
        "code_verifier": verifier,
    })
    assert reused == 400 and json.loads(reused_body)["error"] == "invalid_grant"
    opened, open_headers, open_body = _asgi("POST", "/api/ubuntu/mcp/v1", json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}},
    }).encode(), {"authorization": "Bearer " + issued["access_token"], "content-type": "application/json"})
    assert opened == 200, open_body
    session = open_headers["mcp-session-id"]
    called, _headers, call_body = _asgi("POST", "/api/ubuntu/mcp/v1", json.dumps({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "studio_health", "arguments": {}},
    }).encode(), {
        "authorization": "Bearer " + issued["access_token"],
        "content-type": "application/json",
        "mcp-session-id": session,
    })
    assert called == 200
    health = json.loads(call_body)["result"]["structuredContent"]
    assert health["ok"] is True and health["service"] == "ubuntu-talks-voice-studio-api"
    assert issued["access_token"] not in call_body.decode() and OWNER not in call_body.decode()
    exported, _headers, export_body = _asgi("POST", "/api/ubuntu/mcp/v1", json.dumps({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "export_verified_master", "arguments": {}},
    }).encode(), {
        "authorization": "Bearer " + issued["access_token"],
        "content-type": "application/json",
        "mcp-session-id": session,
    })
    assert json.loads(export_body)["result"]["structuredContent"]["error"] == "permission_denied"
    refreshed, _headers, refresh_body = _form("/oauth/token", {
        "grant_type": "refresh_token", "refresh_token": issued["refresh_token"], "client_id": client_id,
    })
    assert refreshed == 200
    rotated = json.loads(refresh_body)
    stale, _headers, stale_body = _form("/oauth/token", {
        "grant_type": "refresh_token", "refresh_token": issued["refresh_token"], "client_id": client_id,
    })
    assert stale == 400 and json.loads(stale_body)["error"] == "invalid_grant"
    revoke_status, _headers, _revoke_body = _form("/oauth/revoke", {"token": rotated["access_token"]})
    assert revoke_status == 200
    denied_call, _headers, _denied_body = _asgi("POST", "/api/ubuntu/mcp/v1", json.dumps({
        "jsonrpc": "2.0", "id": 4, "method": "initialize", "params": {},
    }).encode(), {"authorization": "Bearer " + rotated["access_token"], "content-type": "application/json"})
    assert denied_call == 401
