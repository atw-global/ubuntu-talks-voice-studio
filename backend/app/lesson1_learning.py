"""Lesson 1 learning stages for Everyday isiZulu.

Activity strings are copied from the approved native-model cue list used by
the private MP3. Nothing here is a new translation or a new isiZulu line.
Paid stage bodies stay on the server until a Whop membership is verified.
"""
from __future__ import annotations

import re

COURSE_ID = "cors_EYwVx1BwLtuXB"
LESSON_ID = "lesn_p61ZUtWXJkEie"
PRODUCT_ID = "prod_EBSCxcpCQvcgI"
PLAN_ID = "plan_KhrZ8JGb2YWRt"
CHECKOUT_URL = "https://whop.com/checkout/plan_KhrZ8JGb2YWRt"
PRICE_USD = "29.99"

# Exact text_to_speak values and the meanings already paired with the sample.
PHRASES = {
    "Sawubona.": "Hello (one person).",
    "Sanibonani.": "Hello (a group).",
    "Unjani?": "How are you? (one person)",
    "Ninjani?": "How are you? (a group)",
    "Ngiyaphila.": "I am fine.",
    "Ngiyaphila, wena unjani?": "I'm fine. And how are you?",
    "Sisaphila, nina ninjani?": "We are fine. How are you all?",
    "Ngiyabonga.": "Thank you.",
    "Sala kahle.": "Stay well.",
    "Ngizokubona kusasa.": "See you tomorrow.",
}

SELF_CHECK = (
    "I could follow the model",
    "I need to listen again",
)

LESSONS = (
    {"id": "lesson-01", "title": "Sounds, Greetings & Respect", "state": "open"},
    {"id": "lesson-02", "title": "Introduce Yourself", "state": "not_authored"},
    {"id": "lesson-03", "title": "Family & Community", "state": "not_authored"},
    {"id": "lesson-04", "title": "Requests & Everyday Needs", "state": "not_authored"},
    {"id": "lesson-05", "title": "Food & Home", "state": "not_authored"},
    {"id": "lesson-06", "title": "Numbers & Time", "state": "not_authored"},
    {"id": "lesson-07", "title": "Places & Directions", "state": "not_authored"},
    {"id": "lesson-08", "title": "Shopping & Prices", "state": "not_authored"},
    {"id": "lesson-09", "title": "Everyday Small Talk", "state": "not_authored"},
    {"id": "lesson-10", "title": "Beginner Conversation Capstone", "state": "not_authored"},
)

_STAGES = (
    {
        "id": "hear",
        "index": 1,
        "title": "Hear",
        "free": True,
        "intent": "Listen to Thando and Themba and notice when a greeting is for one person or a group.",
        "activities": [
            {
                "id": "hear-group",
                "type": "choice",
                "prompt": "Which expression greets a group?",
                "choices": ["Sawubona.", "Sanibonani."],
                "correct": 1,
                "success": "Sanibonani greets more than one person.",
                "retry": "Sawubona greets one person. Listen again for the group form.",
                "replay_text": "Sanibonani.",
            },
            {
                "id": "hear-one",
                "type": "choice",
                "prompt": "Which expression greets one person?",
                "choices": ["Sanibonani.", "Sawubona."],
                "correct": 1,
                "success": "Sawubona greets one person.",
                "retry": "Sanibonani is the group greeting.",
                "replay_text": "Sawubona.",
            },
            {
                "id": "hear-fine",
                "type": "choice",
                "prompt": "Someone asks Unjani? Which reply says you are fine?",
                "choices": ["Ngiyaphila.", "Sanibonani."],
                "correct": 0,
                "success": "Ngiyaphila means you are fine.",
                "retry": "Sanibonani opens a greeting. It is not the reply to how you are.",
                "replay_text": "Ngiyaphila.",
            },
        ],
    },
    {
        "id": "understand",
        "index": 2,
        "title": "Understand",
        "free": False,
        "intent": "Match each model line to the meaning and the person it addresses.",
        "activities": [
            {
                "id": "understand-match",
                "type": "match",
                "prompt": "Match each expression to its meaning.",
                "pairs": [
                    {"zu": "Sawubona.", "en": "Hello (one person)."},
                    {"zu": "Sanibonani.", "en": "Hello (a group)."},
                    {"zu": "Ngiyabonga.", "en": "Thank you."},
                ],
                "success": "The meaning and the person being greeted now sit together.",
                "retry": "Listen for whether the line greets one person, a group, or gives thanks.",
            },
            {
                "id": "understand-who",
                "type": "choice",
                "prompt": "Ninjani? is addressed to whom?",
                "choices": ["How are you? (a group)", "How are you? (one person)"],
                "correct": 0,
                "success": "Ninjani? asks a group how they are.",
                "retry": "Unjani? is the form for one person.",
                "replay_text": "Ninjani?",
            },
        ],
    },
    {
        "id": "imitate",
        "index": 3,
        "title": "Imitate",
        "free": False,
        "intent": "Say the model aloud and compare it with what you heard. Pronunciation is not scored automatically.",
        "activities": [
            {
                "id": "imitate-one",
                "type": "self_check",
                "prompt": "Replay Sawubona. Say it aloud, then record what you noticed.",
                "choices": list(SELF_CHECK),
                "note": "This is your own check. The classroom does not grade pronunciation.",
                "replay_text": "Sawubona.",
                "pronunciation_graded": False,
            },
            {
                "id": "imitate-group",
                "type": "self_check",
                "prompt": "Replay Sanibonani. Say it aloud, then record what you noticed.",
                "choices": list(SELF_CHECK),
                "note": "This is your own check. The classroom does not grade pronunciation.",
                "replay_text": "Sanibonani.",
                "pronunciation_graded": False,
            },
        ],
    },
    {
        "id": "manipulate",
        "index": 4,
        "title": "Manipulate",
        "free": False,
        "intent": "Change a one-person form into the group form.",
        "activities": [
            {
                "id": "manipulate-hello",
                "type": "choice",
                "prompt": "You greeted one person with Sawubona. Which form greets a group?",
                "choices": ["Sanibonani.", "Ngiyaphila."],
                "correct": 0,
                "success": "Sanibonani is the group form of the greeting.",
                "retry": "Ngiyaphila talks about how you are. The group greeting is different.",
                "replay_text": "Sanibonani.",
            },
            {
                "id": "manipulate-how",
                "type": "choice",
                "prompt": "You asked one person Unjani? Which form asks a group?",
                "choices": ["Ninjani?", "Sala kahle."],
                "correct": 0,
                "success": "Ninjani? asks a group how they are.",
                "retry": "Sala kahle closes the conversation. It does not ask how a group is.",
                "replay_text": "Ninjani?",
            },
        ],
    },
    {
        "id": "retrieve",
        "index": 5,
        "title": "Retrieve",
        "free": False,
        "intent": "Recall the expression before you lean on the recording.",
        "activities": [
            {
                "id": "retrieve-thanks",
                "type": "choice",
                "prompt": "How do you say thank you?",
                "choices": ["Ngiyabonga.", "Sala kahle."],
                "correct": 0,
                "success": "Ngiyabonga means thank you.",
                "retry": "Sala kahle means stay well.",
                "replay_text": "Ngiyabonga.",
            },
            {
                "id": "retrieve-stay",
                "type": "choice",
                "prompt": "How do you say stay well?",
                "choices": ["Ngizokubona kusasa.", "Sala kahle."],
                "correct": 1,
                "success": "Sala kahle means stay well.",
                "retry": "Ngizokubona kusasa means see you tomorrow.",
                "replay_text": "Sala kahle.",
            },
        ],
    },
    {
        "id": "converse",
        "index": 6,
        "title": "Converse",
        "free": False,
        "intent": "Choose the model line that fits the turn you were given.",
        "activities": [
            {
                "id": "converse-ask",
                "type": "choice",
                "prompt": "Thando has said Sawubona. Which model asks how that one person is?",
                "choices": ["Unjani?", "Ninjani?"],
                "correct": 0,
                "success": "Unjani? asks one person how they are.",
                "retry": "Ninjani? asks a group.",
                "replay_text": "Unjani?",
            },
            {
                "id": "converse-reply",
                "type": "choice",
                "prompt": "Themba asks Unjani? Which model says you are fine and asks the question back?",
                "choices": ["Ngiyaphila, wena unjani?", "Sisaphila, nina ninjani?"],
                "correct": 0,
                "success": "That reply is for one person.",
                "retry": "Sisaphila, nina ninjani? speaks for a group and asks a group.",
                "replay_text": "Ngiyaphila, wena unjani?",
            },
            {
                "id": "converse-order",
                "type": "order",
                "prompt": "Put these model lines in the order they are first taught.",
                "items": ["Sawubona.", "Sanibonani.", "Unjani?", "Ninjani?"],
                "success": "That is the order of the first four models.",
                "retry": "The recording teaches the one-person line, then the group line.",
            },
        ],
    },
    {
        "id": "assess",
        "index": 7,
        "title": "Assess",
        "free": False,
        "intent": "Use the greetings without the recording in front of the question.",
        "activities": [
            {
                "id": "assess-group",
                "type": "choice",
                "prompt": "Greet a group.",
                "choices": ["Sawubona.", "Sanibonani."],
                "correct": 1,
                "success": "Sanibonani greets a group.",
                "retry": "Sawubona greets one person.",
                "replay_text": "Sanibonani.",
            },
            {
                "id": "assess-thanks",
                "type": "choice",
                "prompt": "Thank the person you greeted.",
                "choices": ["Sala kahle.", "Ngiyabonga."],
                "correct": 1,
                "success": "Ngiyabonga means thank you.",
                "retry": "Sala kahle means stay well.",
                "replay_text": "Ngiyabonga.",
            },
            {
                "id": "assess-close",
                "type": "choice",
                "prompt": "Say that you will see them tomorrow.",
                "choices": ["Ngizokubona kusasa.", "Ngiyaphila."],
                "correct": 0,
                "success": "Ngizokubona kusasa means see you tomorrow.",
                "retry": "Ngiyaphila means you are fine.",
                "replay_text": "Ngizokubona kusasa.",
            },
        ],
    },
)


def access_catalog() -> dict:
    return {
        "course_id": COURSE_ID,
        "lesson_id": LESSON_ID,
        "product_id": PRODUCT_ID,
        "plan_id": PLAN_ID,
        "price_usd": PRICE_USD,
        "checkout_url": CHECKOUT_URL,
        "commercial_release": False,
        "audio_kind": "mp3",
        "instructor_audio": {
            "status": "not_attached",
            "voice": "en-ZA-LeahNeural",
            "language": "en",
            "contains_target_language": False,
            "media": None,
            "script_status": "proposed_not_source_locked",
            "audition": "factory/isiZulu-beginner-I/MRS_UBUNTU_VOICE_CASTING_SHORTLIST_2026-11-19.md",
        },
        "lessons": [dict(item) for item in LESSONS],
        "stages": [
            {
                "id": stage["id"],
                "index": stage["index"],
                "title": stage["title"],
                "free": stage["free"],
                "intent": stage["intent"],
            }
            for stage in _STAGES
        ],
    }


def resolve_stage(stage_id: str, enrolled: bool) -> tuple[int, dict]:
    stage = next((item for item in _STAGES if item["id"] == stage_id), None)
    if stage is None:
        return 404, {"error": "unknown_stage"}
    if not stage["free"] and not enrolled:
        return 403, {
            "error": "enrollment_required",
            "stage": stage_id,
            "checkout_url": CHECKOUT_URL,
            "price_usd": PRICE_USD,
            "plan_id": PLAN_ID,
            "commercial_release": False,
            "message": "This stage stays locked until Whop confirms a membership on the Everyday isiZulu plan.",
        }
    return 200, {
        "id": stage["id"],
        "title": stage["title"],
        "intent": stage["intent"],
        "free": stage["free"],
        "activities": stage["activities"],
        "pronunciation_graded": False,
    }


def membership_header_accepted(value: str) -> bool:
    """A membership id is only a lookup key. It never grants access by itself."""
    return bool(re.fullmatch(r"mem_[A-Za-z0-9]+", (value or "").strip()))


def membership_record_grants(record: dict) -> bool:
    """True only for this product, this one-time plan, and a live membership state."""
    status = record.get("status")
    if status not in {"active", "completed", "trialing"}:
        return False
    product = _nested_id(record.get("product")) or record.get("product_id")
    plan = (
        _nested_id(record.get("plan"))
        or _nested_id(record.get("variant"))
        or record.get("plan_id")
        or record.get("variant_id")
    )
    return product == PRODUCT_ID and plan == PLAN_ID


def language_strings(stage_id: str | None = None) -> list[str]:
    """isiZulu and approved English glosses used as answers."""
    found: list[str] = []
    for stage in _STAGES:
        if stage_id and stage["id"] != stage_id:
            continue
        for activity in stage["activities"]:
            for choice in activity.get("choices") or []:
                found.append(choice)
            for item in activity.get("items") or []:
                found.append(item)
            for pair in activity.get("pairs") or []:
                found.append(pair["zu"])
                found.append(pair["en"])
    return found


def _nested_id(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        nested = value.get("id")
        if isinstance(nested, str):
            return nested
    return None
