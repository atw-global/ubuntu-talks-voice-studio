"""Lesson 1 audio ranges and enrollment decisions. No network and no R2."""
from app.lesson_audio import clip_audio
from app.lesson1_learning import (
    PHRASES,
    SELF_CHECK,
    language_strings,
    membership_record_grants,
    resolve_stage,
)

PRODUCT = "prod_EBSCxcpCQvcgI"
PLAN = "plan_KhrZ8JGb2YWRt"


def test_full_audio_response_has_no_range_header():
    status, body, extra = clip_audio(b"abcdef", None)
    assert status == 200 and body == b"abcdef" and extra == {}


def test_byte_range_matches_mobile_playback():
    blob = b"0123456789"
    status, body, extra = clip_audio(blob, "bytes=0-3")
    assert status == 206 and body == b"0123"
    assert extra["Content-Range"] == "bytes 0-3/10"


def test_open_range_and_suffix_and_rejection():
    blob = b"0123456789"
    status, body, extra = clip_audio(blob, "bytes=8-")
    assert (status, body, extra["Content-Range"]) == (206, b"89", "bytes 8-9/10")
    status, body, extra = clip_audio(blob, "bytes=-4")
    assert (status, body, extra["Content-Range"]) == (206, b"6789", "bytes 6-9/10")
    status, body, extra = clip_audio(blob, "bytes=20-30")
    assert status == 416 and body == b"" and extra["Content-Range"] == "bytes */10"
    status, _, extra = clip_audio(blob, "bytes=-")
    assert status == 416


def test_visitor_receives_hear_and_not_paid_answers():
    status, hear = resolve_stage("hear", enrolled=False)
    assert status == 200 and hear["activities"][0]["choices"] == ["Sawubona.", "Sanibonani."]
    status, locked = resolve_stage("assess", enrolled=False)
    assert status == 403 and locked["error"] == "enrollment_required"
    assert "activities" not in locked and "Ngizokubona" not in str(locked)


def test_enrollment_returns_assess_without_invented_lines():
    status, body = resolve_stage("assess", enrolled=True)
    assert status == 200
    assert body["pronunciation_graded"] is False
    allowed = set(PHRASES) | set(PHRASES.values()) | set(SELF_CHECK)
    for text in language_strings():
        assert text in allowed


def test_unknown_stage_and_membership_binding():
    status, body = resolve_stage("lesson-02", enrolled=True)
    assert status == 404 and body["error"] == "unknown_stage"
    assert membership_record_grants(
        {"status": "completed", "product": {"id": PRODUCT}, "plan": {"id": PLAN}}
    )
    assert not membership_record_grants(
        {"status": "completed", "product": {"id": PRODUCT}, "plan": {"id": "plan_other"}}
    )
    assert not membership_record_grants(
        {"status": "canceled", "product_id": PRODUCT, "plan_id": PLAN}
    )
    assert not membership_record_grants({"status": "active", "product_id": PRODUCT})
