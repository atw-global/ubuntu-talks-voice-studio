"""OAuth 2.1 authorization for ChatGPT and other MCP clients.

Authorization Code with S256 PKCE. A client is never approved silently:
the owner must submit UBUNTU_MCP_OWNER_PASSWORD on the consent page.
Issued tokens have only the read and verify scopes. The gateway token and
the bootstrap token are not used here and are not returned.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlencode, urlsplit

from sqlalchemy import Column, DateTime, MetaData, String, Table, select, update

from app.mcp.auth import _engine, token_hash, write_audit

PUBLIC_PATHS = frozenset({
    "/api/ubuntu/mcp/v1",
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-protected-resource/api/ubuntu/mcp/v1",
    "/.well-known/oauth-authorization-server",
    "/oauth/authorize",
    "/oauth/token",
    "/oauth/register",
    "/oauth/revoke",
})
RESOURCE_PATH = "/api/ubuntu/mcp/v1"
GRANTED_SCOPES = ("read", "verify")
STABLE_REDIRECT = "https://chatgpt.com/connector_platform_oauth_redirect"
CALLBACK_REDIRECT = re.compile(r"^https://chatgpt\.com/connector/oauth/[A-Za-z0-9_-]{8,128}$")
CIMD_URL = re.compile(r"^https://chatgpt\.com/oauth/(?:client\.json|[A-Za-z0-9_-]{8,128}/client\.json)$")
ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=30)
CODE_TTL = timedelta(minutes=5)
_meta = MetaData()
clients = Table(
    "ubuntu_mcp_oauth_clients", _meta,
    Column("client_id", String(80), primary_key=True),
    Column("redirect_uris", String(1000), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
)
codes = Table(
    "ubuntu_mcp_oauth_codes", _meta,
    Column("code_hash", String(64), primary_key=True),
    Column("client_id", String(300), nullable=False),
    Column("redirect_uri", String(300), nullable=False),
    Column("code_challenge", String(128), nullable=False),
    Column("resource", String(300), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True)),
)
tokens = Table(
    "ubuntu_mcp_oauth_tokens", _meta,
    Column("id", String(40), primary_key=True),
    Column("access_hash", String(64), nullable=False, unique=True),
    Column("refresh_hash", String(64), nullable=False, unique=True),
    Column("client_id", String(300), nullable=False),
    Column("scopes", String(40), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("access_expires_at", DateTime(timezone=True), nullable=False),
    Column("refresh_expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
)
_ready = False
_failures: dict[str, list[datetime]] = {}


def public_origin() -> str:
    return os.environ.get("UBUNTU_MCP_PUBLIC_ORIGIN", "https://ubuntu-talks-voice-studio-api.onrender.com").rstrip("/")


def resource_url() -> str:
    return public_origin() + RESOURCE_PATH


def metadata_url() -> str:
    return public_origin() + "/.well-known/oauth-protected-resource" + RESOURCE_PATH


def www_authenticate() -> str:
    return (
        'Bearer realm="ubuntu-talks-voice-studio", '
        f'resource_metadata="{metadata_url()}", scope="read verify"'
    )


def protected_resource_metadata() -> dict:
    return {
        "resource": resource_url(),
        "authorization_servers": [public_origin()],
        "bearer_methods_supported": ["header"],
        "scopes_supported": list(GRANTED_SCOPES),
    }


def authorization_server_metadata() -> dict:
    origin = public_origin()
    return {
        "issuer": origin,
        "authorization_endpoint": origin + "/oauth/authorize",
        "token_endpoint": origin + "/oauth/token",
        "registration_endpoint": origin + "/oauth/register",
        "revocation_endpoint": origin + "/oauth/revoke",
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "revocation_endpoint_auth_methods_supported": ["none"],
        "client_id_metadata_document_supported": True,
        "authorization_response_iss_parameter_supported": True,
        "scopes_supported": list(GRANTED_SCOPES),
    }


def ensure_tables() -> None:
    global _ready
    if not _ready:
        _meta.create_all(_engine())
        _ready = True


def redirect_allowed(uri: str) -> bool:
    if uri == STABLE_REDIRECT or CALLBACK_REDIRECT.match(uri or ""):
        return True
    extras = {item.strip() for item in os.environ.get("UBUNTU_MCP_OAUTH_REDIRECTS", "").split(",") if item.strip()}
    return uri in extras


def register_client(payload: dict) -> tuple[int, dict]:
    ensure_tables()
    uris = payload.get("redirect_uris")
    if not isinstance(uris, list) or not uris or not all(isinstance(item, str) and redirect_allowed(item) for item in uris):
        write_audit(None, None, "oauth.register", None, False, "redirect_rejected")
        return 400, {"error": "invalid_client_metadata"}
    method = payload.get("token_endpoint_auth_method", "none")
    # ChatGPT's metadata prefers private_key_jwt and also supports none.
    # This server accepts only the public PKCE method, so registration
    # records that method even when the request names the other one.
    if method not in {"none", "private_key_jwt"}:
        return 400, {"error": "invalid_client_metadata"}
    client_id = "utmcp_" + uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    with _engine().begin() as conn:
        conn.execute(clients.insert().values(
            client_id=client_id, redirect_uris="\n".join(uris), created_at=now, revoked_at=None,
        ))
    write_audit(client_id, None, "oauth.register", None, True, "client_registered")
    return 201, {
        "client_id": client_id,
        "client_id_issued_at": int(now.timestamp()),
        "redirect_uris": uris,
        "token_endpoint_auth_method": "none",
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "scope": "read verify",
    }


def client_redirects(client_id: str) -> list[str] | None:
    if CIMD_URL.match(client_id or ""):
        document = _cimd_document(client_id)
        if not document or document.get("client_id") != client_id:
            return None
        uris = document.get("redirect_uris")
        if not isinstance(uris, list):
            return None
        return [item for item in uris if isinstance(item, str) and redirect_allowed(item)]
    ensure_tables()
    with _engine().connect() as conn:
        row = conn.execute(select(clients.c.redirect_uris, clients.c.revoked_at).where(
            clients.c.client_id == client_id)).first()
    if not row or row.revoked_at is not None:
        return None
    return [item for item in row.redirect_uris.split("\n") if item]


def fetch_cimd(client_id: str) -> dict | None:
    """Fetch a ChatGPT client metadata document. The URL is rebuilt and redirects are refused."""
    import urllib.request
    parts = urlsplit(client_id)
    if parts.scheme != "https" or parts.hostname != "chatgpt.com" or parts.username or parts.query or parts.fragment:
        return None
    if not CIMD_URL.match("https://chatgpt.com" + parts.path):
        return None
    url = "https://chatgpt.com" + parts.path

    class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(_RefuseRedirect)
    try:
        with opener.open(url, timeout=5) as response:
            if response.status != 200:
                return None
            body = response.read(20000)
    except Exception:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _cimd_document(client_id: str) -> dict | None:
    return fetch_cimd(client_id)


def authorization_page(params: dict) -> tuple[int, str, str]:
    """Return status, content type, and body. Unknown clients get no code."""
    prepared = _prepare_authorization(params)
    if prepared.get("error"):
        return 400, "text/html; charset=utf-8", _page(prepared["error"], None)
    return 200, "text/html; charset=utf-8", _page(None, prepared)


def submit_authorization(params: dict, remote: str) -> tuple[int, dict[str, str], str]:
    if _limited(remote):
        write_audit(None, None, "oauth.authorize", None, False, "rate_limited")
        return 429, {"content-type": "text/html; charset=utf-8"}, _page("Too many attempts. Wait and try again.", None)
    prepared = _prepare_authorization(params)
    if prepared.get("error"):
        return 400, {"content-type": "text/html; charset=utf-8"}, _page(prepared["error"], None)
    expected = os.environ.get("UBUNTU_MCP_OWNER_PASSWORD", "")
    supplied = params.get("owner_password") or ""
    if not expected or not isinstance(supplied, str) or not _equal(expected, supplied):
        _failures.setdefault(remote, []).append(datetime.now(timezone.utc))
        write_audit(prepared["client_id"][:40], None, "oauth.authorize", None, False, "owner_rejected")
        return 401, {"content-type": "text/html; charset=utf-8"}, _page("Owner approval was not accepted.", prepared)
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    ensure_tables()
    with _engine().begin() as conn:
        conn.execute(codes.insert().values(
            code_hash=token_hash(code),
            client_id=prepared["client_id"],
            redirect_uri=prepared["redirect_uri"],
            code_challenge=prepared["code_challenge"],
            resource=resource_url(),
            expires_at=now + CODE_TTL,
            used_at=None,
        ))
    write_audit(prepared["client_id"][:40], None, "oauth.authorize", None, True, "code_issued")
    query = urlencode({"code": code, "state": prepared["state"], "iss": public_origin()})
    return 302, {"location": prepared["redirect_uri"] + "?" + query, "cache-control": "no-store"}, ""


def exchange_token(form: dict) -> tuple[int, dict]:
    grant = form.get("grant_type")
    if grant == "authorization_code":
        return _exchange_code(form)
    if grant == "refresh_token":
        return _exchange_refresh(form)
    return 400, {"error": "unsupported_grant_type"}


def revoke_token(form: dict) -> None:
    raw = form.get("token") or ""
    if not raw:
        return
    digest = token_hash(raw)
    now = datetime.now(timezone.utc)
    ensure_tables()
    with _engine().begin() as conn:
        conn.execute(update(tokens).where(
            (tokens.c.access_hash == digest) | (tokens.c.refresh_hash == digest)
        ).values(revoked_at=now))
    write_audit(None, None, "oauth.revoke", None, True, "token_revoked")


def access_credential(digest: str) -> dict | None:
    ensure_tables()
    now = _naive(datetime.now(timezone.utc))
    with _engine().connect() as conn:
        row = conn.execute(select(
            tokens.c.id, tokens.c.scopes, tokens.c.access_expires_at, tokens.c.revoked_at, tokens.c.created_at,
        ).where(tokens.c.access_hash == digest)).first()
    if not row or row.revoked_at is not None:
        return None
    if _naive(row.access_expires_at) <= now or _issued_before_cutoff(row.created_at):
        return None
    return {"id": row.id, "label": "oauth", "scopes": set(row.scopes.split())}


def _exchange_code(form: dict) -> tuple[int, dict]:
    code = form.get("code") or ""
    verifier = form.get("code_verifier") or ""
    client_id = form.get("client_id") or ""
    redirect_uri = form.get("redirect_uri") or ""
    resource = form.get("resource") or resource_url()
    if resource != resource_url() or not code or not verifier:
        return 400, {"error": "invalid_grant"}
    ensure_tables()
    now = datetime.now(timezone.utc)
    digest = token_hash(code)
    accepted = False
    with _engine().begin() as conn:
        row = conn.execute(select(codes).where(codes.c.code_hash == digest)).first()
        if (row and row.used_at is None and _naive(row.expires_at) > _naive(now)
                and row.client_id == client_id and row.redirect_uri == redirect_uri
                and row.resource == resource and _equal(row.code_challenge, _s256(verifier))):
            result = conn.execute(update(codes).where(
                codes.c.code_hash == digest, codes.c.used_at.is_(None),
            ).values(used_at=now))
            accepted = result.rowcount == 1
    if not accepted:
        write_audit(None, None, "oauth.token", None, False, "code_rejected")
        return 400, {"error": "invalid_grant"}
    return _issue(client_id, now)


def _exchange_refresh(form: dict) -> tuple[int, dict]:
    raw = form.get("refresh_token") or ""
    client_id = form.get("client_id") or ""
    if not raw:
        return 400, {"error": "invalid_grant"}
    ensure_tables()
    now = datetime.now(timezone.utc)
    digest = token_hash(raw)
    accepted = False
    with _engine().begin() as conn:
        row = conn.execute(select(tokens).where(tokens.c.refresh_hash == digest)).first()
        if (row and row.revoked_at is None and row.client_id == client_id
                and _naive(row.refresh_expires_at) > _naive(now) and not _issued_before_cutoff(row.created_at)):
            result = conn.execute(update(tokens).where(
                tokens.c.id == row.id, tokens.c.revoked_at.is_(None),
            ).values(revoked_at=now))
            accepted = result.rowcount == 1
    if not accepted:
        return 400, {"error": "invalid_grant"}
    return _issue(client_id, now)


def _issue(client_id: str, now: datetime) -> tuple[int, dict]:
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(32)
    with _engine().begin() as conn:
        conn.execute(tokens.insert().values(
            id="oat_" + uuid.uuid4().hex[:16],
            access_hash=token_hash(access),
            refresh_hash=token_hash(refresh),
            client_id=client_id,
            scopes=" ".join(GRANTED_SCOPES),
            created_at=now,
            access_expires_at=now + ACCESS_TTL,
            refresh_expires_at=now + REFRESH_TTL,
            revoked_at=None,
        ))
    write_audit(client_id[:40], None, "oauth.token", None, True, "access_issued")
    return 200, {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": int(ACCESS_TTL.total_seconds()),
        "refresh_token": refresh,
        "scope": "read verify",
    }


def _prepare_authorization(params: dict) -> dict:
    client_id = params.get("client_id") or ""
    redirect_uri = params.get("redirect_uri") or ""
    state = params.get("state") or ""
    challenge = params.get("code_challenge") or ""
    method = params.get("code_challenge_method") or ""
    response_type = params.get("response_type") or ""
    if response_type != "code" or method != "S256" or not challenge or not state:
        return {"error": "This authorization request is incomplete."}
    allowed = client_redirects(client_id)
    if not allowed or redirect_uri not in allowed:
        return {"error": "This client is not approved for that redirect."}
    if not os.environ.get("UBUNTU_MCP_OWNER_PASSWORD", ""):
        return {"error": "Owner approval is not configured on this service."}
    return {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
    }


def _page(message: str | None, prepared: dict | None) -> str:
    notice = f"<p>{html.escape(message)}</p>" if message else ""
    if not prepared:
        return f"<!doctype html><html><head><meta charset='utf-8'><title>Ubuntu Talks</title></head><body>{notice}</body></html>"
    fields = "".join(
        f"<input type='hidden' name='{html.escape(key)}' value='{html.escape(prepared[key])}'>"
        for key in ("client_id", "redirect_uri", "state", "code_challenge")
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Approve Ubuntu Talks</title></head><body>"
        "<h1>Approve read access</h1>"
        "<p>Approve this only if you just started it from your own ChatGPT connector. "
        "The client receives read and verify access only. It cannot record, export, attach, or publish.</p>"
        f"<p>Client: {html.escape(prepared['client_id'])}<br>Redirect: {html.escape(prepared['redirect_uri'])}</p>"
        f"{notice}<form method='post' action='/oauth/authorize'>{fields}"
        "<input type='hidden' name='response_type' value='code'>"
        "<input type='hidden' name='code_challenge_method' value='S256'>"
        "<label>Owner approval password <input name='owner_password' type='password' autocomplete='current-password' required></label>"
        "<button type='submit'>Approve read and verify</button></form></body></html>"
    )


def _equal(left: str, right: str) -> bool:
    if len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def _s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _limited(remote: str) -> bool:
    now = datetime.now(timezone.utc)
    recent = [item for item in _failures.get(remote, []) if now - item < timedelta(minutes=15)]
    _failures[remote] = recent
    return len(recent) >= 8


def _issued_before_cutoff(created_at: datetime) -> bool:
    raw = os.environ.get("UBUNTU_MCP_OAUTH_REVOKED_BEFORE", "").strip()
    if not raw:
        return False
    try:
        cutoff = datetime.fromisoformat(raw)
    except ValueError:
        return False
    return _naive(created_at) <= _naive(cutoff)


def _naive(value: datetime) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def parse_form(body: bytes, content_type: str) -> dict:
    if "application/json" in content_type:
        try:
            value = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}
    parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=False)
    return {key: values[-1] for key, values in parsed.items()}


def query_params(query: str) -> dict:
    parsed = parse_qs(query, keep_blank_values=False)
    return {key: values[-1] for key, values in parsed.items()}


