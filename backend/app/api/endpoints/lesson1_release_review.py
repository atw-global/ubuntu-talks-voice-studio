"""Private, gateway-protected Lesson 01 review page and hard release gates.

F0 audio is reference-only. Microsoft paid-tier TTS rights cannot be granted
by a review click, a checksum, an account upgrade, or a product API write.
"""
from __future__ import annotations

from html import escape
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from app.api.endpoints.lesson1_recording import CUES

router = APIRouter(prefix="/api/ubuntu/azure/lesson1/release-review", tags=["ubuntu-lesson1-release-review"])
MASTER = "/api/ubuntu/azure/lesson1/master/listen.mp3"
SAMPLE = "/api/ubuntu/azure/lesson1/sample/qa-preview.mp3"

@router.get("/status")
def release_status():
    return {
        "course_id": "cors_EYwVx1BwLtuXB",
        "whop_lesson_id": "lesn_p61ZUtWXJkEie",
        "reference_master_duration_seconds": 617,
        "reference_sample_duration_seconds": 85.08,
        "reference_audio_technical_integrity": "PASS",
        "reference_audio_license": "F0_INTERNAL_QA_ONLY",
        "azure_commercial_master": "NOT_GENERATED_ON_PAID_TIER",
        "native_speaker_pronunciation_signoff": "NOT_RECEIVED",
        "review_required": ["all 139 cues match source", "isiZulu click consonants c q x", "vowels and stress",
                            "singular/plural and respectful social register", "three-voice consistency",
                            "audible gaps, pacing, duplication and truncation"],
        "whop_lesson_media": "NOT_ATTACHED",
        "free_sales_audio_sample": "BLOCKED",
        "paid_entitlement_test": "PENDING",
        "commercial_publication_allowed": False,
    }

@router.get("/review", response_class=HTMLResponse)
def review_page():
    """Readable inside the existing authenticated Studio API proxy; no public URL.

    QA reviewers record notes outside this page; nothing here can silently
    change publication or rights status.
    """
    rows = []
    for cue in CUES:
        number = int(cue["order"])
        speaker = escape(str(cue.get("azure_voice", "")))
        line = escape(str(cue["text_to_speak"]))
        rows.append(f"<tr><td>{number:03d}</td><td>{speaker}</td><td>{line}</td><td>□</td></tr>")
    table = "\n".join(rows)
    return HTMLResponse(f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>Ubuntu Talks — Lesson 1 Private Quality Review</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;background:#fff9ef;color:#2e201a;max-width:940px;margin:2rem auto;padding:0 1rem}}
h1{{font-size:2rem}}h2{{margin-top:2rem}}audio{{width:100%;max-width:800px}}
section{{padding:1rem 1.4rem;border:1px solid #d7c5af;border-radius:12px;margin:1.25rem 0;background:white}}
table{{border-collapse:collapse;width:100%;font-size:.91rem}}td,th{{padding:.5rem;border-bottom:1px solid #e7ddcf;text-align:left;vertical-align:top}}
th{{position:sticky;top:0;background:#f2ebdf}}.warn{{color:#8b290d;font-weight:700}}
small{{color:#675448}}</style></head><body>
<p>UBUNTU TALKS · EVERYDAY ISIZULU · BEGINNER I</p>
<h1>Lesson 01 — Sounds, Greetings &amp; Respect</h1>
<p class="warn">INTERNAL REVIEW ONLY — F0 reference audio is NOT licensed for commercial distribution.</p>
<section><h2>Listen to full master — 10:17</h2>
<audio controls preload="none" src="{MASTER}"></audio>
<p><small>139 cues, Leah / Thando / Themba. Source hash verified, native-language sign-off pending.</small></p>
<h2>Listen to greeting excerpt — 1:25</h2>
<audio controls preload="none" src="{SAMPLE}"></audio>
<p><small>85.08-second untrimmed-cue reference excerpt. Not a public preview.</small></p></section>
<section><h2>Required native-speaker review</h2>
<p>Listen to the complete lesson against the 139 lines below, then complete a signed external QA report documenting:</p>
<ol><li>Correct words, vowels, syllables and click consonants c, q, x</li>
<li>Singular/plural greetings, cultural and respectful usage</li>
<li>Natural pacing, pause lengths, and turn-taking</li>
<li>Correct Leah / Thando / Themba role assignments</li>
<li>No audible cutoff, distortion, repetition or missing lines</li>
<li>Exact cue numbers, time ranges and replacement wording for every correction</li></ol>
<p class="warn">Do not mark passed until a qualified reviewer signs the report. A paid S0 commercial re-recording and second listening test are also required.</p></section>
<section><h2>Source-exact 139-cue review ledger</h2>
<table><thead><tr><th>Cue</th><th>Voice</th><th>Approved spoken text</th><th>Checked</th></tr></thead>
<tbody>{table}</tbody></table></section>
<p><small>Whop course cors_EYwVx1BwLtuXB · lesson lesn_p61ZUtWXJkEie · protected by StudioGateway.</small></p></body></html>""",headers={"Cache-Control":"private, no-store","X-Robots-Tag":"noindex, nofollow"})
