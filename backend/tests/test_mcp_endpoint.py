"""Authenticated MCP calls against the Voice Studio endpoint. No Azure and no R2."""
import asyncio
import json
import os
import pathlib
import subprocess
import tempfile

from fastapi import FastAPI
from starlette.responses import JSONResponse

os.environ["UBUNTU_MCP_DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(prefix="ubuntu-mcp-", suffix=".sqlite")
os.environ["UBUNTU_MCP_BOOTSTRAP_TOKEN"] = "test-read-credential"
os.environ["UBUNTU_MCP_ADMIN_TOKEN"] = "test-admin-credential"
os.environ.pop("UBUNTU_MCP_READ_TOKENS", None)
os.environ.pop("UBUNTU_R2_ACCESS_KEY_ID", None)
os.environ.pop("UBUNTU_R2_SECRET_ACCESS_KEY", None)
os.environ.pop("WHOP_API_KEY", None)

from app.api.endpoints.mcp_v1 import router as mcp_router
from app.mcp.auth import recent_audit
from app.mcp.protocol import handle_http
from app.mcp.tools import _decode
from app.middleware.studio_gateway import StudioGateway

TOKEN = os.environ["UBUNTU_MCP_BOOTSTRAP_TOKEN"]
ADMIN = os.environ["UBUNTU_MCP_ADMIN_TOKEN"]
app = FastAPI()
app.include_router(mcp_router)


def _asgi(application, method, path, body, headers):
    sent = []

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "client": ("127.0.0.1", 1234), "server": ("studio", 80),
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


class Response:
    def __init__(self, status, headers, payload):
        self.status_code = status
        self.headers = headers
        self.text = payload.decode()
        self.content = payload

    def json(self):
        return json.loads(self.text)


def _post(token, payload, session=None, origin=None):
    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
    if session:
        headers["mcp-session-id"] = session
    if origin:
        headers["origin"] = origin
    status, headers, payload = _asgi(app, "POST", "/api/ubuntu/mcp/v1", json.dumps(payload).encode(), headers)
    return Response(status, headers, payload)


def _session(token=TOKEN):
    opened = _post(token, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"},
    }})
    assert opened.status_code == 200, opened.text
    assert opened.headers["mcp-session-id"]
    assert TOKEN not in opened.text and ADMIN not in opened.text
    return opened.headers["mcp-session-id"]


def _call(session, name, token=TOKEN, request_id=2):
    response = _post(token, {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": {"name": name, "arguments": {}}}, session)
    assert response.status_code == 200, response.text
    body = response.json()
    assert TOKEN not in response.text and ADMIN not in response.text
    return body["result"]["structuredContent"], body["result"]["isError"]


def test_gateway_lets_mcp_through_and_keeps_other_routes_closed():
    async def inner(scope, receive, send):
        await JSONResponse({"reached": scope["path"]})(scope, receive, send)

    gateway = StudioGateway(inner)
    opened = Response(*_asgi(gateway, "POST", "/api/ubuntu/mcp/v1", b"{}", {}))
    blocked = Response(*_asgi(gateway, "POST", "/api/ubuntu/azure/lesson1/master/start", b"{}", {}))
    assert opened.status_code == 200 and opened.json()["reached"] == "/api/ubuntu/mcp/v1"
    assert blocked.status_code == 403


def test_missing_and_wrong_credentials_are_rejected():
    missing = Response(*_asgi(app, "POST", "/api/ubuntu/mcp/v1", b"{}", {}))
    wrong = Response(*_asgi(app, "POST", "/api/ubuntu/mcp/v1", b"{}", {"authorization": "Bearer wrong"}))
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert "test-read-credential" not in missing.text


def test_revoked_credential_cannot_initialize():
    os.environ["UBUNTU_MCP_BOOTSTRAP_TOKEN"] = "replacement-read-credential"
    try:
        denied = _post(TOKEN, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert denied.status_code == 401
        opened = _post("replacement-read-credential", {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert opened.status_code == 200
    finally:
        os.environ["UBUNTU_MCP_BOOTSTRAP_TOKEN"] = TOKEN


def test_authenticated_read_tools_and_closed_release_tools():
    session = _session()
    listed = _post(TOKEN, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, session)
    names = {tool["name"] for tool in listed.json()["result"]["tools"]}
    assert "verify_master_sha256" in names and "publish_course" in names
    health, failed = _call(session, "studio_health")
    assert failed is False and health["gateway_token_accepted_from_client"] is False
    verified, failed = _call(session, "verify_master_sha256", request_id=3)
    assert failed is False and verified["available"] is False and verified["regenerated"] is False
    assert verified["sha256"] is None and verified["historical_reference_matches"] is False
    alignment, failed = _call(session, "get_cue_alignment", request_id=4)
    assert [item["text"] for item in alignment["source_order"]] == ["Sanibonani.", "Unjani?", "Ninjani?"]
    assert alignment["timing_status"] == "manual_review"
    manifest, failed = _call(session, "get_audio_manifest", request_id=5)
    assert manifest["cue_count"] == 139
    exported, failed = _call(session, "export_verified_master", request_id=6)
    assert failed is True and exported["error"] == "permission_denied"
    admin_session = _session(ADMIN)
    published, failed = _call(admin_session, "publish_course", token=ADMIN, request_id=8)
    assert failed is True and published["published"] is False and published["visibility"] == "hidden"
    staged, failed = _call(admin_session, "stage_audio_for_whop", token=ADMIN, request_id=9)
    assert failed is True and staged["attached"] is False
    replaced, failed = _call(admin_session, "replace_recording", token=ADMIN, request_id=10)
    assert replaced["replaced"] is False
    recorded, failed = _call(admin_session, "run_recording", token=ADMIN, request_id=11)
    assert recorded["started"] is False and recorded["clips_changed"] is False
    details = " ".join(row["detail"] for row in recent_audit(30))
    assert TOKEN not in details and ADMIN not in details


def test_browser_origin_is_rejected_and_get_does_not_start_a_stream():
    blocked = _post(TOKEN, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}, origin="https://example.test")
    assert blocked.status_code == 403
    status, headers, body = handle_http("GET", {"authorization": f"Bearer {TOKEN}"}, b"")
    assert status == 405 and b"master" not in body


def test_decoder_hashes_a_real_mp3_without_using_it_as_the_lesson_master():
    with tempfile.TemporaryDirectory() as temp:
        path = pathlib.Path(temp) / "tone.mp3"
        subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.4",
             "-c:a", "libmp3lame", "-b:a", "64k", "-y", str(path)],
            check=True, timeout=20,
        )
        decoded = _decode(path.read_bytes())
    assert decoded["ok"] is True and decoded["duration_seconds"] > 0.2


if __name__ == "__main__":
    for name, function in sorted(globals().items()):
        if name.startswith("test_"):
            function()
            print(name, "ok")
