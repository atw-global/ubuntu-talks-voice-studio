"""OAuth 2.1 discovery, owner consent, PKCE, and an authenticated studio_health call."""
import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlsplit

from fastapi import FastAPI
from sqlalchemy import update

_database_fd, _database_path = tempfile.mkstemp(prefix="ubuntu-mcp-oauth-", suffix=".sqlite")
os.close(_database_fd)
os.environ["UBUNTU_MCP_DATABASE_URL"] = "sqlite:///" + _database_path
os.environ["UBUNTU_MCP_BOOTSTRAP_TOKEN"] = "test-read-credential"
os.environ["UBUNTU_MCP_ADMIN_TOKEN"] = "test-admin-credential"
os.environ["UBUNTU_MCP_PUBLIC_ORIGIN"] = "http://studio"
os.environ["UBUNTU_MCP_OWNER_PASSWORD"] = "owner-approval-secret"
os.environ.pop("UBUNTU_MCP_READ_TOKENS", None)
os.environ.pop("UBUNTU_MCP_OAUTH_REVOKED_BEFORE", None)
os.environ.pop("UBUNTU_R2_ACCESS_KEY_ID", None)
os.environ.pop("UBUNTU_R2_SECRET_ACCESS_KEY", None)
os.environ.pop("WHOP_API_KEY", None)

from app.api.endpoints.mcp_v1 import router as mcp_router
from app.api.endpoints.oauth_mcp import router as oauth_router
from app.mcp.auth import _engine, recent_audit
from app.mcp.oauth import fetch_cimd, tokens
from app.mcp.protocol import handle_http
from app.middleware.studio_gateway import StudioGateway

OWNER = os.environ["UBUNTU_MCP_OWNER_PASSWORD"]
BOOTSTRAP = os.environ["UBUNTU_MCP_BOOTSTRAP_TOKEN"]
REDIRECT = "https://chatgpt.com/connector_platform_oauth_redirect"
app = FastAPI()
app.include_router(mcp_router)
app.include_router(oauth_router)
gateway = StudioGateway(app)


def _asgi(application, method, path, body, headers, query=""):
    sent = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": query.encode(), "client": ("127.0.0.1", 1234), "server": ("studio", 80),
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
    }
    asyncio.run(application(scope, receive, send))
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


def _json(method, path, payload, query=""):
    status, headers, body = _asgi(
        gateway, method, path, json.dumps(payload).encode(),
        {"content-type": "application/json"}, query,
    )
    return status, headers, json.loads(body.decode() or "null")


def _form(path, fields):
    status, headers, body = _asgi(
        gateway, "POST", path, urlencode(fields).encode(),
        {"content-type": "application/x-www-form-urlencoded"},
    )
    parsed = json.loads(body.decode()) if body.startswith(b"{") else body.decode()
    return status, headers, parsed


def _s256(verifier: str) -> str:
    import base64
    import hashlib
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _mcp(token, payload, session=None, origin=None):
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    if session:
        headers["mcp-session-id"] = session
    if origin:
        headers["origin"] = origin
    status, headers, body = _asgi(gateway, "POST", "/api/ubuntu/mcp/v1", json.dumps(payload).encode(), headers)
    return status, headers, json.loads(body.decode())


def test_discovery_and_unauthorized_mcp_advertise_the_resource():
    status, _headers, metadata = _json("GET", "/.well-known/oauth-protected-resource/api/ubuntu/mcp/v1", {})
    assert status == 200
    assert metadata["resource"] == "http://studio/api/ubuntu/mcp/v1"
    assert metadata["authorization_servers"] == ["http://studio"]
    assert metadata["scopes_supported"] == ["read", "verify"]
    status, _headers, server = _json("GET", "/.well-known/oauth-authorization-server", {})
    assert status == 200
    assert server["issuer"] == "http://studio"
    assert server["code_challenge_methods_supported"] == ["S256"]
    assert server["token_endpoint_auth_methods_supported"] == ["none"]
    assert server["authorization_response_iss_parameter_supported"] is True
    assert server["client_id_metadata_document_supported"] is True
    assert "openid" not in server["scopes_supported"]
    blocked = _json("GET", "/api/ubuntu/azure/lesson1/master/status", {})
    assert blocked[0] == 403
    status, headers, body = _mcp(None, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, origin="https://chatgpt.com")
    assert status == 401
    assert "resource_metadata=" in headers["www-authenticate"]
    assert body == {"error": "unauthorized"}
    assert OWNER not in headers["www-authenticate"]


def test_owner_must_approve_and_pkce_exchanges_for_studio_health():
    rejected = _json("POST", "/oauth/register", {"redirect_uris": ["https://evil.example/callback"], "token_endpoint_auth_method": "none"})
    assert rejected[0] == 400 and rejected[2]["error"] == "invalid_client_metadata"
    status, _headers, registered = _json("POST", "/oauth/register", {
        "redirect_uris": [REDIRECT],
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "client_name": "ChatGPT",
        "scope": "read verify publish",
    })
    assert status == 201
    client_id = registered["client_id"]
    assert registered["scope"] == "read verify"
    assert registered["token_endpoint_auth_method"] == "none"
    preferred = _json("POST", "/oauth/register", {
        "redirect_uris": [REDIRECT],
        "token_endpoint_auth_method": "private_key_jwt",
    })
    assert preferred[0] == 201 and preferred[2]["token_endpoint_auth_method"] == "none"
    verifier = "a" * 50
    challenge = _s256(verifier)
    query = urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
        "code_challenge": challenge, "code_challenge_method": "plain", "state": "state-1", "scope": "publish",
    })
    status, _headers, page = _asgi(gateway, "GET", "/oauth/authorize", b"", {}, query)
    assert status == 400 and b"code=" not in page
    query = query.replace("code_challenge_method=plain", "code_challenge_method=S256")
    saved = os.environ.pop("UBUNTU_MCP_OWNER_PASSWORD")
    status, _headers, page = _asgi(gateway, "GET", "/oauth/authorize", b"", {}, query)
    assert status == 400 and b"not configured" in page
    os.environ["UBUNTU_MCP_OWNER_PASSWORD"] = saved
    status, _headers, page = _asgi(gateway, "GET", "/oauth/authorize", b"", {}, query)
    assert status == 200 and b"Approve read access" in page and OWNER.encode() not in page
    fields = {
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": "state-1",
        "owner_password": "wrong",
    }
    status, headers, page = _form("/oauth/authorize", fields)
    assert status == 401 and "location" not in headers and "code=" not in page
    fields["owner_password"] = OWNER
    status, headers, _page = _form("/oauth/authorize", fields)
    assert status == 302
    location = urlsplit(headers["location"])
    issued = parse_qs(location.query)
    assert location.scheme == "https" and issued["iss"] == ["http://studio"] and issued["state"] == ["state-1"]
    code = issued["code"][0]
    denied = _form("/oauth/token", {
        "grant_type": "authorization_code", "code": code, "code_verifier": "b" * 50,
        "client_id": client_id, "redirect_uri": REDIRECT, "resource": "http://studio/api/ubuntu/mcp/v1",
    })
    assert denied[0] == 400 and denied[2]["error"] == "invalid_grant"
    exchanged = _form("/oauth/token", {
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
        "client_id": client_id, "redirect_uri": REDIRECT, "resource": "http://studio/api/ubuntu/mcp/v1",
    })
    assert exchanged[0] == 200
    access = exchanged[2]["access_token"]
    refresh = exchanged[2]["refresh_token"]
    assert exchanged[2]["scope"] == "read verify"
    reused = _form("/oauth/token", {
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
        "client_id": client_id, "redirect_uri": REDIRECT,
    })
    assert reused[0] == 400
    opened = _mcp(access, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}, origin="https://chatgpt.com")
    assert opened[0] == 200
    session = opened[1]["mcp-session-id"]
    health = _mcp(access, {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "studio_health", "arguments": {}}}, session)
    result = health[2]["result"]["structuredContent"]
    assert result["ok"] is True and result["service"] == "ubuntu-talks-voice-studio-api"
    assert access not in json.dumps(result) and BOOTSTRAP not in json.dumps(result)
    blocked_tool = _mcp(access, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "publish_course", "arguments": {}}}, session)
    assert blocked_tool[2]["result"]["structuredContent"]["error"] == "permission_denied"
    rotated = _form("/oauth/token", {"grant_type": "refresh_token", "refresh_token": refresh, "client_id": client_id})
    assert rotated[0] == 200 and rotated[2]["access_token"] != access
    stale = _form("/oauth/token", {"grant_type": "refresh_token", "refresh_token": refresh, "client_id": client_id})
    assert stale[0] == 400
    _form("/oauth/revoke", {"token": rotated[2]["access_token"]})
    revoked = _mcp(rotated[2]["access_token"], {"jsonrpc": "2.0", "id": 4, "method": "initialize", "params": {}})
    assert revoked[0] == 401
    details = " ".join(row["detail"] for row in recent_audit(30))
    assert access not in details and refresh not in details and OWNER not in details and code not in details


def test_expired_and_watermarked_tokens_are_rejected():
    status, _headers, registered = _json("POST", "/oauth/register", {"redirect_uris": [REDIRECT], "token_endpoint_auth_method": "none"})
    client_id = registered["client_id"]
    verifier = "c" * 50
    fields = {
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
        "code_challenge": _s256(verifier), "code_challenge_method": "S256", "state": "state-2",
        "owner_password": OWNER,
    }
    status, headers, _body = _form("/oauth/authorize", fields)
    assert status == 302, headers
    code = parse_qs(urlsplit(headers["location"]).query)["code"][0]
    exchanged = _form("/oauth/token", {
        "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
        "client_id": client_id, "redirect_uri": REDIRECT,
    })
    access = exchanged[2]["access_token"]
    with _engine().begin() as conn:
        conn.execute(update(tokens).values(access_expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc)))
    expired = _mcp(access, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert expired[0] == 401
    os.environ["UBUNTU_MCP_OAUTH_REVOKED_BEFORE"] = "2099-01-01T00:00:00+00:00"
    try:
        verifier = "d" * 50
        fields["code_challenge"] = _s256(verifier)
        fields["state"] = "state-3"
        status, headers, _body = _form("/oauth/authorize", fields)
        code = parse_qs(urlsplit(headers["location"]).query)["code"][0]
        minted = _form("/oauth/token", {
            "grant_type": "authorization_code", "code": code, "code_verifier": verifier,
            "client_id": client_id, "redirect_uri": REDIRECT,
        })
        rejected = _mcp(minted[2]["access_token"], {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert rejected[0] == 401
    finally:
        os.environ.pop("UBUNTU_MCP_OAUTH_REVOKED_BEFORE", None)


def test_cimd_client_is_limited_to_chatgpt_and_an_approved_redirect():
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return {"client_id": url, "redirect_uris": [REDIRECT, "https://evil.example/callback"]}

    original = fetch_cimd
    import app.mcp.oauth as oauth
    oauth.fetch_cimd = fake_fetch
    try:
        status, _headers, page = _asgi(gateway, "GET", "/oauth/authorize", b"", {}, urlencode({
            "response_type": "code", "client_id": "https://evil.example/client.json", "redirect_uri": REDIRECT,
            "code_challenge": _s256("e" * 50), "code_challenge_method": "S256", "state": "state-4",
        }))
        assert status == 400 and calls == []
        client_id = "https://chatgpt.com/oauth/client.json"
        status, headers, _page = _form("/oauth/authorize", {
            "response_type": "code", "client_id": client_id, "redirect_uri": "https://evil.example/callback",
            "code_challenge": _s256("e" * 50), "code_challenge_method": "S256", "state": "state-4",
            "owner_password": OWNER,
        })
        assert status == 400 and "location" not in headers
        status, headers, _page = _form("/oauth/authorize", {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
            "code_challenge": _s256("e" * 50), "code_challenge_method": "S256", "state": "state-5",
            "owner_password": OWNER,
        })
        assert status == 302 and calls == [client_id, client_id]
        assert parse_qs(urlsplit(headers["location"]).query)["iss"] == ["http://studio"]
    finally:
        oauth.fetch_cimd = original


def test_bootstrap_credential_still_calls_studio_health():
    direct = handle_http("POST", {"authorization": f"Bearer {BOOTSTRAP}", "content-type": "application/json"}, json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"},
    }).encode())
    assert direct[0] == 200


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_"):
            function()
            print(name, "ok")
