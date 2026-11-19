"""OAuth 2.1 authorization code + PKCE for ChatGPT MCP clients.

ChatGPT can register and start a login, but a code is issued only after the
owner submits the secret configured on the API service. Tokens are stored as
SHA-256 hashes. The gateway token and the MCP bootstrap token are never read
or returned here.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

from sqlalchemy import Column, DateTime, MetaData, String, Table

from app.mcp.auth import _engine, token_hash, write_audit

PUBLIC_ORIGIN = "https://ubuntu-talks-voice-studio-api.onrender.com"
RESOURCE_PATH = "/api/ubuntu/mcp/v1"
ALLOWED_SCOPES = ("read", "verify")
CODE_TTL = timedelta(minutes=10)
ACCESS_TTL = timedelta(hours=1)
REFRESH_TTL = timedelta(days=14)
VERIFIER = re.compile(r"^[A-Za-z0-9._~-]{43,128}$")
DEFAULT_REDIRECTS = ("https://chatgpt.com/", "https://chat.openai.com/")

_meta = MetaData()
clients = Table(
    "ubuntu_mcp_oauth_clients", _meta,
    Column("id", String(48), primary_key=True),
    Column("name", String(120), nullable=False),
    Column("redirects", String(1000), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
codes = Table(
    "ubuntu_mcp_oauth_codes", _meta,
    Column("code_hash", String(64), primary_key=True),
    Column("client_id", String(48), nullable=False),
    Column("redirect_uri", String(400), nullable=False),
    Column("challenge", String(128), nullable=False),
    Column("scopes", String(40), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True)),
)
tokens = Table(
    "ubuntu_mcp_oauth_tokens", _meta,
    Column("token_hash", String(64), primary_key=True),
    Column("kind", String(16), nullable=False),
    Column("client_id", String(48), nullable=False),
    Column("scopes", String(40), nullable=False),
    Column("family", String(40), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
)


def public_origin() -> str:
    configured = os.environ.get("UBUNTU_MCP_PUBLIC_ORIGIN", "").strip().rstrip("/")
    return configured or PUBLIC_ORIGIN


def resource_url() -> str:
    return public_origin() + RESOURCE_PATH


def metadata_url() -> str:
    return public_origin() + "/.well-known/oauth-protected-resource"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= _now()


def _ready() -> None:
    _meta.create_all(_engine())


def _redirect_prefixes() -> tuple[str, ...]:
    raw = os.environ.get("UBUNTU_MCP_OAUTH_REDIRECTS", "").strip()
    if not raw:
        return DEFAULT_REDIRECTS
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def redirect_allowed(uri: str) -> bool:
    if not uri.startswith("https://") or any(char in uri for char in ("\r", "\n", " ")):
        return False
    return any(uri.startswith(prefix) for prefix in _redirect_prefixes())


def parse_scopes(raw: str | None) -> tuple[str, ...] | None:
    if raw is None or not str(raw).strip():
        return ALLOWED_SCOPES
    parts = [item for item in re.split(r"[\s,]+", str(raw).strip()) if item]
    if not parts or any(item not in ALLOWED_SCOPES for item in parts):
        return None
    return tuple(dict.fromkeys(parts))


def protected_resource_metadata() -> dict:
    return {
        "resource": resource_url(),
        "authorization_servers": [public_origin()],
        "scopes_supported": list(ALLOWED_SCOPES),
        "bearer_methods_supported": ["header"],
        "resource_name": "Ubuntu Talks Voice Studio",
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
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": list(ALLOWED_SCOPES),
        "revocation_endpoint_auth_methods_supported": ["none"],
    }


def register_client(body: dict) -> tuple[int, dict]:
    if not isinstance(body, dict):
        return 400, {"error": "invalid_client_metadata"}
    method = str(body.get("token_endpoint_auth_method") or "none")
    if method != "none":
        return 400, {"error": "invalid_client_metadata", "error_description": "Public PKCE clients only."}
    redirects = body.get("redirect_uris")
    if not isinstance(redirects, list) or not redirects or any(not isinstance(item, str) or not redirect_allowed(item) for item in redirects):
        return 400, {"error": "invalid_redirect_uri"}
    scopes = parse_scopes(body.get("scope"))
    if scopes is None:
        return 400, {"error": "invalid_scope"}
    name = str(body.get("client_name") or "ChatGPT")[:120]
    client_id = "utvs_" + secrets.token_urlsafe(18)
    _ready()
    with _engine().begin() as conn:
        conn.execute(clients.insert().values(
            id=client_id, name=name, redirects=json.dumps(redirects), created_at=_now(),
        ))
    write_audit(client_id, None, "oauth.register", None, True, "client_registered")
    return 201, {
        "client_id": client_id,
        "client_name": name,
        "redirect_uris": redirects,
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": " ".join(scopes),
    }


def _client(client_id: str):
    _ready()
    with _engine().connect() as conn:
        return conn.execute(select_client(client_id)).first()


def select_client(client_id: str):
    from sqlalchemy import select
    return select(clients.c.id, clients.c.name, clients.c.redirects).where(clients.c.id == client_id)


def client_redirects(row) -> list[str]:
    try:
        value = json.loads(row.redirects)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def authorize_page(query: dict[str, str]) -> tuple[int, str]:
    error = _authorize_error(query)
    if error:
        return 400, _page("Authorization was not started", error)
    row = _client(query["client_id"])
    host = urlsplit(query["redirect_uri"]).netloc
    configured = bool(os.environ.get("UBUNTU_MCP_OAUTH_OWNER_SECRET", "").strip())
    notice = "The owner secret is not set on the API service, so this client cannot be approved." if not configured else (
        "Enter the Voice Studio owner secret to allow this client to read and verify. "
        "Recording, export, and publication stay closed."
    )
    fields = "".join(
        f'<input type="hidden" name="{html.escape(key, quote=True)}" value="{html.escape(query.get(key, ""), quote=True)}">'
        for key in ("response_type", "client_id", "redirect_uri", "code_challenge", "code_challenge_method", "state", "scope", "resource")
        if query.get(key)
    )
    secret_field = "" if not configured else (
        '<label for="owner_secret">Owner secret</label>'
        '<input id="owner_secret" name="owner_secret" type="password" autocomplete="current-password" required>'
    )
    button = "" if not configured else '<button type="submit">Allow read and verify</button>'
    body = (
        f"<p>{html.escape(notice)}</p>"
        f"<dl><dt>Client</dt><dd>{html.escape(row.name)}</dd>"
        f"<dt>Redirect</dt><dd>{html.escape(host)}</dd>"
        f"<dt>Scopes</dt><dd>{html.escape(' '.join(parse_scopes(query.get('scope')) or ()))}</dd></dl>"
        f"<form method=\"post\" action=\"/oauth/authorize\">{fields}{secret_field}{button}</form>"
    )
    return (503 if not configured else 200), _page("Approve Voice Studio access", body)


def submit_authorization(form: dict[str, str]) -> tuple[int, str, str | None]:
    """Return status, body, and a redirect URL when a code is issued."""
    error = _authorize_error(form)
    if error:
        write_audit(form.get("client_id"), None, "oauth.authorize", None, False, "rejected")
        return 400, _page("Authorization refused", html.escape(error)), None
    if not os.environ.get("UBUNTU_MCP_OAUTH_OWNER_SECRET", "").strip():
        return 503, _page("Owner secret is not configured", "Set UBUNTU_MCP_OAUTH_OWNER_SECRET on the API service."), None
    supplied = form.get("owner_secret", "")
    expected = os.environ.get("UBUNTU_MCP_OAUTH_OWNER_SECRET", "")
    if not supplied or not secrets.compare_digest(supplied, expected):
        write_audit(form.get("client_id"), None, "oauth.authorize", None, False, "owner_rejected")
        return 401, _page("Owner check failed", "The secret did not match. No access was granted."), None
    scopes = parse_scopes(form.get("scope"))
    code = secrets.token_urlsafe(32)
    _ready()
    with _engine().begin() as conn:
        conn.execute(codes.insert().values(
            code_hash=token_hash(code),
            client_id=form["client_id"],
            redirect_uri=form["redirect_uri"],
            challenge=form["code_challenge"],
            scopes=" ".join(scopes or ()),
            expires_at=_now() + CODE_TTL,
            used_at=None,
        ))
    write_audit(form["client_id"], None, "oauth.authorize", None, True, "code_issued")
    params = {"code": code}
    if form.get("state"):
        params["state"] = form["state"]
    return 302, "", form["redirect_uri"] + ("&" if "?" in form["redirect_uri"] else "?") + urlencode(params)


def _authorize_error(query: dict[str, str]) -> str:
    if query.get("response_type") != "code":
        return "Only authorization code is supported."
    if query.get("code_challenge_method") != "S256" or not query.get("code_challenge"):
        return "PKCE S256 is required."
    scopes = parse_scopes(query.get("scope"))
    if scopes is None:
        return "Only the read and verify scopes can be granted."
    resource = query.get("resource")
    if resource and resource.rstrip("/") != resource_url():
        return "The resource does not match this Voice Studio endpoint."
    row = _client(query.get("client_id", ""))
    if row is None or query.get("redirect_uri") not in client_redirects(row):
        return "The client or redirect is not registered."
    return ""


def exchange_token(form: dict[str, str]) -> tuple[int, dict]:
    grant = form.get("grant_type")
    if grant == "authorization_code":
        return _exchange_code(form)
    if grant == "refresh_token":
        return _exchange_refresh(form)
    return 400, {"error": "unsupported_grant_type"}


def _exchange_code(form: dict[str, str]) -> tuple[int, dict]:
    verifier = form.get("code_verifier", "")
    code = form.get("code", "")
    if not code or not VERIFIER.fullmatch(verifier):
        return 400, {"error": "invalid_request"}
    digest = token_hash(code)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")
    _ready()
    with _engine().connect() as conn:
        row = conn.execute(codes.select().where(codes.c.code_hash == digest)).first()
    if row is None or row.used_at is not None or _expired(row.expires_at):
        write_audit(form.get("client_id"), None, "oauth.token", None, False, "invalid_code")
        return 400, {"error": "invalid_grant"}
    if row.client_id != form.get("client_id") or row.redirect_uri != form.get("redirect_uri"):
        return 400, {"error": "invalid_grant"}
    if not secrets.compare_digest(row.challenge.rstrip("="), challenge):
        write_audit(row.client_id, None, "oauth.token", None, False, "pkce_rejected")
        return 400, {"error": "invalid_grant"}
    with _engine().begin() as conn:
        spent = conn.execute(codes.update().where(
            codes.c.code_hash == digest, codes.c.used_at.is_(None),
        ).values(used_at=_now()))
        if spent.rowcount != 1:
            return 400, {"error": "invalid_grant"}
    issued = _issue(row.client_id, row.scopes, secrets.token_urlsafe(16))
    write_audit(row.client_id, None, "oauth.token", None, True, "access_issued")
    return 200, issued


def _exchange_refresh(form: dict[str, str]) -> tuple[int, dict]:
    presented = form.get("refresh_token", "")
    if not presented:
        return 400, {"error": "invalid_request"}
    _ready()
    digest = token_hash(presented)
    with _engine().connect() as conn:
        row = conn.execute(tokens.select().where(tokens.c.token_hash == digest)).first()
    if row is None or row.kind != "refresh" or row.revoked_at is not None or _expired(row.expires_at):
        return 400, {"error": "invalid_grant"}
    if form.get("client_id") and form["client_id"] != row.client_id:
        return 400, {"error": "invalid_grant"}
    with _engine().begin() as conn:
        conn.execute(tokens.update().where(tokens.c.family == row.family, tokens.c.revoked_at.is_(None)).values(revoked_at=_now()))
    issued = _issue(row.client_id, row.scopes, row.family)
    write_audit(row.client_id, None, "oauth.refresh", None, True, "rotated")
    return 200, issued


def _issue(client_id: str, scopes: str, family: str) -> dict:
    access = secrets.token_urlsafe(32)
    refresh = secrets.token_urlsafe(32)
    now = _now()
    with _engine().begin() as conn:
        conn.execute(tokens.insert(), [
            {
                "token_hash": token_hash(access), "kind": "access", "client_id": client_id,
                "scopes": scopes, "family": family, "expires_at": now + ACCESS_TTL, "revoked_at": None,
            },
            {
                "token_hash": token_hash(refresh), "kind": "refresh", "client_id": client_id,
                "scopes": scopes, "family": family, "expires_at": now + REFRESH_TTL, "revoked_at": None,
            },
        ])
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": int(ACCESS_TTL.total_seconds()),
        "refresh_token": refresh,
        "scope": scopes,
    }


def revoke_token(presented: str) -> None:
    if not presented:
        return
    _ready()
    digest = token_hash(presented)
    now = _now()
    with _engine().begin() as conn:
        row = conn.execute(tokens.select().where(tokens.c.token_hash == digest)).first()
        if row is None:
            return
        conn.execute(tokens.update().where(tokens.c.family == row.family, tokens.c.revoked_at.is_(None)).values(revoked_at=now))
    write_audit(row.client_id, None, "oauth.revoke", None, True, "family_revoked")


def access_credential(token: str) -> dict | None:
    if not token:
        return None
    try:
        _ready()
        digest = token_hash(token)
        with _engine().connect() as conn:
            row = conn.execute(tokens.select().where(tokens.c.token_hash == digest)).first()
    except Exception:
        return None
    if row is None or row.kind != "access" or row.revoked_at is not None or _expired(row.expires_at):
        return None
    return {"id": "oauth_" + row.client_id[:24], "label": "oauth-read", "scopes": set(row.scopes.split())}


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:Georgia,serif;background:#f7f3ea;color:#163024;margin:2rem}"
        "form{display:grid;gap:.75rem;max-width:28rem}input,button{font:1rem sans-serif;padding:.6rem}"
        "button{background:#1f6b45;color:#fff;border:0}</style></head>"
        f"<body><main><h1>{html.escape(title)}</h1>{body}</main></body></html>"
    )
