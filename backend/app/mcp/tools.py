"""Voice Studio MCP tools.

Read tools never synthesize audio. Controlled tools refuse unless the
credential has the required scope and the service flag is on. Publication
stays closed while the Lesson 1 release gates are open.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

from app.mcp.auth import ALL_SCOPES

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "data" / "lesson01_approved_139.json"
MASTER_KEY = "courses/zu/beginner-i/lesson-01/v1/master.mp3"
HISTORICAL_SHA256 = "ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a"
COURSE_ID = "cors_EYwVx1BwLtuXB"
LESSON_ID = "lesn_p61ZUtWXJkEie"
PRODUCT_ID = "prod_EBSCxcpCQvcgI"

READ_TOOLS = {
    "studio_health": "read",
    "list_courses": "read",
    "list_lessons": "read",
    "get_recording_status": "read",
    "get_master_metadata": "read",
    "verify_master_sha256": "verify",
    "get_audio_manifest": "read",
    "get_cue_alignment": "read",
    "get_r2_archive_status": "read",
    "get_whop_attachment_status": "read",
}
CONTROLLED_TOOLS = {
    "export_verified_master": "export",
    "stage_audio_for_whop": "attach",
    "run_recording": "record",
    "replace_recording": "record",
    "publish_course": "publish",
}
TOOL_SCOPE = {**READ_TOOLS, **CONTROLLED_TOOLS}

RELEASE_GATES = (
    "verified_master_sha256",
    "native_speaker_pronunciation_signoff",
    "commercial_use_permission",
    "mrs_ubuntu_introduction_audio_approval",
    "enrolled_learner_test",
)


def tool_definitions() -> list[dict]:
    descriptions = {
        "studio_health": "Report whether this MCP endpoint is authenticated. Does not read audio.",
        "list_courses": "List the existing isiZulu course binding. Does not create a course.",
        "list_lessons": "List the existing ten-lesson shell. Does not create a lesson.",
        "get_recording_status": "Read the saved Lesson 1 recording checkpoint. Does not start Azure.",
        "get_master_metadata": "Read stored master metadata. A historical checksum is not a new verification.",
        "verify_master_sha256": "Hash, decode, and time the private master if this process can read it.",
        "get_audio_manifest": "Return the source-locked 139-cue manifest and its file SHA-256.",
        "get_cue_alignment": "Report caption alignment for the greeting cues. Unheard audio stays manual review.",
        "get_r2_archive_status": "Report whether R2 credentials exist and whether the archive was verified.",
        "get_whop_attachment_status": "Read Whop attachment status. Does not upload or publish.",
        "export_verified_master": "Return a private receipt for a hash-matched master. Does not return audio bytes or a public URL.",
        "stage_audio_for_whop": "Prepare a verified master for the hidden lesson. Does not attach or publish while release gates are open.",
        "run_recording": "Resume missing Lesson 1 cues only when recording is explicitly enabled. Default is off.",
        "replace_recording": "Refuse replacement. Approved recordings stay in place.",
        "publish_course": "Refuse publication until every release gate has passed. The course stays hidden.",
    }
    tools = []
    for name, scope in TOOL_SCOPE.items():
        tools.append({
            "name": name,
            "description": descriptions[name],
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            "annotations": {"readOnlyHint": name in READ_TOOLS, "destructiveHint": name == "replace_recording"},
            "_scope": scope,
        })
    return tools


def public_tool_definitions() -> list[dict]:
    return [{key: value for key, value in tool.items() if key != "_scope"} for tool in tool_definitions()]


def call_tool(name: str, scopes: set[str]) -> dict:
    required = TOOL_SCOPE.get(name)
    if required is None:
        return {"ok": False, "error": "unknown_tool", "tool": name}
    if required not in scopes:
        return {
            "ok": False,
            "error": "permission_denied",
            "tool": name,
            "required_scope": required,
            "granted_scopes": sorted(scopes),
        }
    handler = globals()["_tool_" + name]
    return handler()


def _source() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def _tool_studio_health() -> dict:
    return {
        "ok": True,
        "service": "ubuntu-talks-voice-studio-api",
        "mcp_path": "/api/ubuntu/mcp/v1",
        "transport": "streamable-http",
        "gateway_token_accepted_from_client": False,
        "default_profile": ["read", "verify"],
        "controlled_scopes": sorted(set(CONTROLLED_TOOLS.values())),
        "known_scopes": list(ALL_SCOPES),
    }


def _tool_list_courses() -> dict:
    return {"ok": True, "courses": [{
        "course_id": COURSE_ID,
        "product_id": PRODUCT_ID,
        "title": "Ubuntu Talks — Everyday isiZulu | Beginner I",
        "visibility": "hidden",
        "created_by_this_call": False,
    }]}


def _tool_list_lessons() -> dict:
    lessons = []
    binding = pathlib.Path(__file__).resolve().parents[3] / "factory" / "isiZulu-beginner-I" / "whop-course-binding-v1.json"
    if binding.exists():
        for item in json.loads(binding.read_text(encoding="utf-8")).get("lessons", []):
            lessons.append({
                "order": item.get("order"),
                "lesson_id": item.get("whop_lesson_id"),
                "title": item.get("title"),
                "publishing_state": item.get("publishing_state"),
            })
    return {"ok": True, "course_id": COURSE_ID, "lessons": lessons, "created_by_this_call": False}


def _tool_get_recording_status() -> dict:
    try:
        from app.api.endpoints.lesson1_recording import _progress
        status = _progress()
    except Exception as exc:
        return {"ok": True, "available": False, "reason": type(exc).__name__, "recording_started": False}
    status["recording_started"] = False
    status["ok"] = True
    status["available"] = True
    return status


def _tool_get_master_metadata() -> dict:
    verified = _load_master_record()
    if verified.get("available"):
        record = dict(verified)
        record.pop("blob", None)
        record["ok"] = True
        record["bytes_included"] = False
        return record
    return {
        "ok": True,
        "available": False,
        "object_key": MASTER_KEY,
        "historical_reference_sha256": HISTORICAL_SHA256,
        "historical_reference_verified_now": False,
        "reason": verified.get("reason"),
    }


def _tool_verify_master_sha256() -> dict:
    loaded = _load_master_record()
    if not loaded.get("available"):
        return {
            "ok": True,
            "available": False,
            "object_key": MASTER_KEY,
            "sha256": None,
            "duration_seconds": None,
            "cue_count": None,
            "decoded": False,
            "alignment_status": "not_checked",
            "historical_reference_sha256": HISTORICAL_SHA256,
            "historical_reference_matches": False,
            "reason": loaded.get("reason"),
            "regenerated": False,
        }
    blob = loaded["blob"]
    digest = hashlib.sha256(blob).hexdigest()
    decoded = _decode(blob)
    cue_count = loaded.get("cue_count")
    source_count = len(_source()["spoken_cues"])
    return {
        "ok": True,
        "available": True,
        "object_key": MASTER_KEY,
        "source": loaded.get("source"),
        "sha256": digest,
        "stored_sha256": loaded.get("stored_sha256"),
        "bytes": len(blob),
        "duration_seconds": decoded.get("duration_seconds"),
        "decoded": decoded.get("ok", False),
        "decode_error": decoded.get("error"),
        "cue_count": cue_count,
        "source_manifest_cue_count": source_count,
        "cue_count_matches_source": cue_count == source_count,
        "historical_reference_sha256": HISTORICAL_SHA256,
        "historical_reference_matches": digest == HISTORICAL_SHA256,
        "alignment_status": "manual_review",
        "regenerated": False,
        "public_url": None,
    }


def _tool_get_audio_manifest() -> dict:
    raw = SOURCE.read_bytes()
    data = json.loads(raw)
    cues = data["spoken_cues"]
    return {
        "ok": True,
        "path": "backend/app/data/lesson01_approved_139.json",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "cue_count": len(cues),
        "lesson_id": data.get("lesson_id"),
        "cues": [
            {"order": cue["order"], "speaker": cue["speaker"], "text": cue["text_to_speak"], "voice": cue["azure_voice"]}
            for cue in cues
        ],
    }


def _tool_get_cue_alignment() -> dict:
    cues = {cue["order"]: cue["text_to_speak"] for cue in _source()["spoken_cues"]}
    return {
        "ok": True,
        "source_order": [{"order": order, "text": cues[order]} for order in (4, 5, 6)],
        "timing_status": "manual_review",
        "reason": "Caption times are not marked verified until the private master has been decoded and reviewed.",
        "audio_regenerated": False,
    }


def _tool_get_r2_archive_status() -> dict:
    configured = bool(os.environ.get("UBUNTU_R2_ACCESS_KEY_ID", "").strip() and os.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY", "").strip())
    try:
        from app.api.endpoints.lesson1_archive import status
        current = status()
    except Exception as exc:
        current = {"state": "unavailable", "last_error": type(exc).__name__}
    current["ok"] = True
    current["credentials_configured"] = configured
    current["secret_values_included"] = False
    current["public_url"] = None
    return current


def _tool_get_whop_attachment_status() -> dict:
    if not os.environ.get("WHOP_API_KEY", "").strip():
        return {
            "ok": True,
            "live_read": False,
            "credentials_configured": False,
            "course_id": COURSE_ID,
            "lesson_id": LESSON_ID,
            "product_id": PRODUCT_ID,
            "expected_visibility": "hidden",
            "attachment_changed": False,
        }
    try:
        from app.api.endpoints.whop_course_factory import release_preflight
        preflight = release_preflight()
    except Exception as exc:
        return {"ok": True, "live_read": False, "reason": type(exc).__name__, "attachment_changed": False}
    preflight["ok"] = True
    preflight["live_read"] = True
    preflight["attachment_changed"] = False
    return preflight


def _tool_export_verified_master() -> dict:
    verified = _tool_verify_master_sha256()
    if not verified.get("available") or not verified.get("decoded") or verified.get("cue_count") != 139:
        return {"ok": False, "error": "master_not_verified", "exported": False, "verification": _public_verification(verified)}
    if verified.get("sha256") != HISTORICAL_SHA256:
        return {"ok": False, "error": "sha256_mismatch", "exported": False, "sha256": verified.get("sha256")}
    return {
        "ok": True,
        "exported": False,
        "receipt_only": True,
        "sha256": verified["sha256"],
        "bytes": verified["bytes"],
        "duration_seconds": verified["duration_seconds"],
        "cue_count": verified["cue_count"],
        "public_url": None,
        "audio_bytes_included": False,
        "whop_attached": False,
    }


def _tool_stage_audio_for_whop() -> dict:
    if os.environ.get("UBUNTU_MCP_WHOP_STAGE_ENABLED", "").lower() != "true":
        return {"ok": False, "error": "staging_disabled", "attached": False, "visibility": "hidden"}
    verified = _tool_verify_master_sha256()
    open_gates = [gate for gate in RELEASE_GATES if gate != "verified_master_sha256" or not verified.get("historical_reference_matches")]
    return {
        "ok": False,
        "error": "release_gates_open",
        "attached": False,
        "visibility": "hidden",
        "open_gates": open_gates,
        "course_id": COURSE_ID,
        "lesson_id": LESSON_ID,
    }


def _tool_run_recording() -> dict:
    if os.environ.get("UBUNTU_MCP_RECORDING_ENABLED", "").lower() != "true":
        return {"ok": False, "error": "recording_disabled", "started": False, "clips_changed": False}
    return {"ok": False, "error": "recording_not_started", "started": False, "clips_changed": False,
            "reason": "The MCP server does not call Azure. Use the existing authenticated studio control after a separate owner approval."}


def _tool_replace_recording() -> dict:
    return {
        "ok": False,
        "error": "replacement_refused",
        "replaced": False,
        "reason": "Approved recordings are preserved. This tool does not overwrite or regenerate audio.",
    }


def _tool_publish_course() -> dict:
    return {
        "ok": False,
        "error": "publication_refused",
        "published": False,
        "visibility": "hidden",
        "open_gates": list(RELEASE_GATES),
        "course_id": COURSE_ID,
        "lesson_id": LESSON_ID,
        "product_id": PRODUCT_ID,
    }


def _public_verification(verified: dict) -> dict:
    hidden = dict(verified)
    hidden.pop("blob", None)
    return hidden


def _load_master_record() -> dict:
    database = _load_from_database()
    if database.get("available"):
        return database
    remote = _load_from_r2()
    if remote.get("available"):
        return remote
    return {"available": False, "reason": database.get("reason") or remote.get("reason") or "master_not_in_database_or_r2"}


def _load_from_database() -> dict:
    try:
        from sqlalchemy import select
        from app.api.endpoints.lesson1_master import VERSION, _init, engine, masters
        _init()
        with engine.connect() as conn:
            row = conn.execute(select(
                masters.c.mp3, masters.c.sha256, masters.c.size_bytes, masters.c.duration_sec, masters.c.cue_count,
            ).where(masters.c.version == VERSION)).first()
    except Exception as exc:
        return {"available": False, "reason": "database_unreachable", "detail": type(exc).__name__}
    if not row or not row[0]:
        return {"available": False, "reason": "database_row_missing"}
    blob = bytes(row[0])
    return {
        "available": True,
        "source": "postgresql",
        "blob": blob,
        "stored_sha256": row[1],
        "stored_bytes": row[2],
        "stored_duration": row[3],
        "cue_count": row[4],
    }


def _load_from_r2() -> dict:
    if not (os.environ.get("UBUNTU_R2_ACCESS_KEY_ID", "").strip() and os.environ.get("UBUNTU_R2_SECRET_ACCESS_KEY", "").strip()):
        return {"available": False, "reason": "r2_credentials_not_configured"}
    try:
        from app.api.endpoints.lesson1_archive import BUCKET, KEY, _r2_client
        obj = _r2_client().get_object(Bucket=BUCKET, Key=KEY)
        blob = obj["Body"].read()
    except Exception as exc:
        return {"available": False, "reason": "r2_" + type(exc).__name__}
    return {"available": True, "source": "r2", "blob": blob, "stored_sha256": None, "cue_count": None, "object_key": MASTER_KEY}


def _decode(blob: bytes) -> dict:
    with tempfile.TemporaryDirectory(prefix="ubuntu_mcp_master_") as temp:
        path = pathlib.Path(temp) / "master.mp3"
        path.write_bytes(blob)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        decoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-i", str(path), "-f", "null", "-"],
            capture_output=True, timeout=120,
        )
    if probe.returncode != 0 or decoded.returncode != 0:
        return {"ok": False, "error": "decode_failed"}
    try:
        duration = round(float(probe.stdout.strip()), 3)
    except ValueError:
        return {"ok": False, "error": "duration_unreadable"}
    return {"ok": True, "duration_seconds": duration}
