"""Machine credentials for the Voice Studio MCP endpoint.

Tokens are read from the API process environment and stored only as SHA-256
hashes. Nothing in this module writes a token to git, logs, or a response
except `issue` is intentionally absent: rotation is an environment change.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, select, update
READ_VERIFY = ("read", "verify")
ALL_SCOPES = ("read", "verify", "export", "record", "attach", "publish", "admin")

_meta = MetaData()
credentials = Table(
    "ubuntu_mcp_credentials", _meta,
    Column("id", String(40), primary_key=True),
    Column("label", String(80), nullable=False),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("scopes", String(160), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
)
audit_log = Table(
    "ubuntu_mcp_audit", _meta,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("at", DateTime(timezone=True), nullable=False),
    Column("credential_id", String(40)),
    Column("session_id", String(40)),
    Column("method", String(80), nullable=False),
    Column("tool", String(80)),
    Column("ok", Integer, nullable=False),
    Column("detail", String(240), nullable=False),
)
_engines: dict[str, object] = {}


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def database_url() -> str:
    override = os.environ.get("UBUNTU_MCP_DATABASE_URL", "").strip()
    if override:
        return override
    from app.core.config import settings
    return settings.DATABASE_URL


def _engine():
    url = database_url()
    engine = _engines.get(url)
    if engine is None:
        args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        engine = create_engine(url, pool_pre_ping=True, connect_args=args)
        _meta.create_all(engine)
        _engines[url] = engine
    return engine


def _split_tokens(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def desired_credentials() -> dict[str, tuple[str, tuple[str, ...]]]:
    """Map token hash to label and scopes from the current process environment."""
    desired: dict[str, tuple[str, tuple[str, ...]]] = {}
    bootstrap = os.environ.get("UBUNTU_MCP_BOOTSTRAP_TOKEN", "").strip()
    if bootstrap:
        desired[token_hash(bootstrap)] = ("bootstrap", READ_VERIFY)
    for index, token in enumerate(_split_tokens(os.environ.get("UBUNTU_MCP_READ_TOKENS", "")), start=1):
        desired.setdefault(token_hash(token), (f"read-token-{index}", READ_VERIFY))
    admin = os.environ.get("UBUNTU_MCP_ADMIN_TOKEN", "").strip()
    if admin:
        desired[token_hash(admin)] = ("admin", ALL_SCOPES)
    return desired


def sync_credentials() -> None:
    """Activate env credentials and revoke machine credentials removed from the environment."""
    desired = desired_credentials()
    now = datetime.now(timezone.utc)
    engine = _engine()
    with engine.connect() as conn:
        rows = conn.execute(select(
            credentials.c.id, credentials.c.label, credentials.c.token_hash, credentials.c.revoked_at,
        )).all()
    known = {row.token_hash: row for row in rows}
    for token_hash_value, (label, scopes) in desired.items():
        current = known.get(token_hash_value)
        if current and current.revoked_at is None and current.label == label:
            continue
        with engine.begin() as conn:
            if current:
                conn.execute(update(credentials).where(
                    credentials.c.token_hash == token_hash_value,
                ).values(revoked_at=None, label=label, scopes=" ".join(scopes)))
            else:
                conn.execute(credentials.insert().values(
                    id="mcp_" + uuid.uuid4().hex[:16],
                    label=label,
                    token_hash=token_hash_value,
                    scopes=" ".join(scopes),
                    created_at=now,
                    revoked_at=None,
                ))
    with engine.begin() as conn:
        for row in rows:
            managed = row.label == "bootstrap" or row.label == "admin" or str(row.label).startswith("read-token-")
            if managed and row.revoked_at is None and row.token_hash not in desired:
                conn.execute(update(credentials).where(credentials.c.id == row.id).values(revoked_at=now))


def authenticate(token: str) -> dict | None:
    if not token:
        return None
    from app.mcp.oauth import access_credential
    oauth = access_credential(token)
    if oauth:
        return oauth
    sync_credentials()
    digest = token_hash(token)
    with _engine().connect() as conn:
        row = conn.execute(select(
            credentials.c.id, credentials.c.label, credentials.c.scopes, credentials.c.revoked_at,
        ).where(credentials.c.token_hash == digest)).first()
    if not row or row.revoked_at is not None:
        return None
    return {"id": row.id, "label": row.label, "scopes": set(row.scopes.split())}


def write_audit(credential_id: str | None, session_id: str | None, method: str, tool: str | None, ok: bool, detail: str) -> None:
    try:
        with _engine().begin() as conn:
            conn.execute(audit_log.insert().values(
                at=datetime.now(timezone.utc),
                credential_id=credential_id,
                session_id=session_id,
                method=method[:80],
                tool=(tool or "")[:80] or None,
                ok=1 if ok else 0,
                detail=detail[:240],
            ))
    except Exception:
        # An audit-store failure must not become an authentication bypass.
        return


def recent_audit(limit: int = 20) -> list[dict]:
    with _engine().connect() as conn:
        rows = conn.execute(select(
            audit_log.c.credential_id, audit_log.c.method, audit_log.c.tool, audit_log.c.ok, audit_log.c.detail,
        ).order_by(audit_log.c.id.desc()).limit(limit)).all()
    return [
        {"credential_id": row.credential_id, "method": row.method, "tool": row.tool, "ok": bool(row.ok), "detail": row.detail}
        for row in rows
    ]
