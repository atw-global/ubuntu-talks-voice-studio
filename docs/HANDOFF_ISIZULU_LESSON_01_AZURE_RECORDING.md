# Ubuntu Talks Voice Studio — isiZulu Beginner I, Lesson 01 recording handoff

**Date:** 2026-11-17. **Read this file first when resuming.**

## Verified milestone
The user explicitly approved the Azure voice cast and authorized recording Lesson 1. On 2026-11-17 at 18:08 UTC the dedicated Render API deployed and started recording the exact 139 approved ElevenLabs speech cues. Azure Speech POST requests returned HTTP 200 with MP3 data; a verified API status shortly afterward showed **7/139 clips**, `state=recording`, `remaining=132`, `bytes=510336`, `last_error=null`. This is an **early checkpoint**, not the final tally. Read live status for latest progress. **Never claim 139/139 without verifying.**

## Canonical source and cast
- Source of truth: [source-exact 139-cue Azure manifest](../auditions/isiZulu-beginner-I/LESSON_01_APPROVED_139_CUES_AZURE_CAST.json); bundled into [backend/app/data](../backend/app/data/lesson01_approved_139.json).
- Source captured directly from original approved [ElevenLabs Studio Lesson 1](https://elevenlabs.io/app/studio/jvjPtDNnRbMiWanGscbb), with exact 139 text blocks, original voice IDs and ordered assignments. Do not use the separate 66-beat master-derived preview to record the approved production script.
- 12 `MRS_UBUNTU` cues: ElevenLabs Thandi → Azure `en-ZA-LeahNeural`.
- 61 `ZULU_A` cues: ElevenLabs Mapendo → Azure `zu-ZA-ThandoNeural`.
- 66 `ZULU_B` cues: ElevenLabs Gawain → Azure `zu-ZA-ThembaNeural`.
- Total manifest text length: 4,394 characters.
- Curriculum canonical repo: https://github.com/atw-global/ubuntu-spark-forge-573b8ece
- Curriculum master: `content/zulu/instructor-master/zulu-beginner-i-master-v2.json`.
- Course handoff in Drive: https://docs.google.com/document/d/1jSG-tv4_UVNKyEz7ATxDhmz9I_WDAfbQ4uxCnIABE_0/edit

## Live recording / export
- Recording dashboard (login required): https://ubuntu-talks-voice-studio.onrender.com/ubuntu-lesson1-production.html
- GET `/api/ubuntu/azure/lesson1/status` through the authenticated frontend shows `recorded`, `remaining`, `state`, `last_error`, `bytes`.
- POST `/api/ubuntu/azure/lesson1/start` resumes missing cues only.
- GET `/api/ubuntu/azure/lesson1/export.zip` downloads all saved clips, including ordered manifest and SHA256 inventory. Verify ZIP `recording_inventory.json` has `count=139` and `complete=true` before claiming delivery.
- Code: `backend/app/api/endpoints/lesson1_recording.py`, source data `backend/app/data/lesson01_approved_139.json`.
- Render frontend: `srv-dbtql9ifngtc739uek90`.
- Render API: `srv-dbttr1psrm7s73e17im0`.
- PostgreSQL resource: `dpg-dbttmmek1f9s739nrs00-a`.
- `UBUNTU_LESSON1_AUTORECORD=true` is set on API. The lifespan starts/resumes recording on Render startup. It requests Azure sequentially at ~4 second intervals (free-tier throttling). Each successful MP3 is immediately persisted to PostgreSQL. On restarts, completed cues are not repeated.
- No Vast.ai GPU or new billable GPU service is used.

## Google Drive organization
- Parent: https://drive.google.com/drive/folders/1-3p5LoBg7_Sl3zVft3sR3xEJ84DFHsKR
- Lesson 01 audio folder: https://drive.google.com/drive/folders/1iM5Re19ZLRUqCvAz9Q64WfdsmG9_FSqD
- Manifests & handoffs: https://drive.google.com/drive/folders/1KryyAEoatd0c0QVw0aQnlofSa5Jb8VpT
- [Native Google Doc handoff](https://docs.google.com/document/d/1AKgLf4-FGLbS0EY1NKN0JNmNmUy0HekF3eTY46YrhIM/edit).

**Important:** Audio is saved in Render PostgreSQL and can be downloaded as ZIP through the authenticated app, but it has **NOT yet been verified uploaded to Drive**. The free Render database expires **December 17, 2026**; export and back up well before expiry.

## Next agent checklist
1. Read this file and the exact 139-cue manifest. Do not change source text.
2. Check live recording dashboard and API status. If `state=interrupted`, read Render logs, fix only the failing operation and resume missing cues.
3. Wait for /status to show `recorded=139`, `remaining=0`, `state=complete`; check ZIP manifest hashes and source count.
4. Download ZIP and store a verified copy in the Lesson 01 Google Drive audio folder and/or Cloudflare R2, then record its actual file ID/URL and SHA256.
5. Have a native isiZulu reviewer inspect clicks, rhythm, pronunciation and pacing. Keep pronunciation QA separate from user voice-casting approval.
6. Azure account currently configured on **Free F0**; the user approved evaluation voice casting, **not unconditional commercial publishing**. Check legal use and switch to the appropriate paid tier before commercial release.
7. Update this handoff and [the original institutional handoff](https://docs.google.com/document/d/1jSG-tv4_UVNKyEz7ATxDhmz9I_WDAfbQ4uxCnIABE_0/edit) with actual verification.
8. Do not paste Azure keys, Basic Auth credentials or other secrets in documents or chat.

The finished lesson must preserve ALL approved 139 cue texts in order; audio master assembly and learner pauses should be validated separately after all clips are recorded.


## 2026-11-17 — PRONUNCIATION QUALITY FLAG (BLOCK COMMERCIAL RELEASE)

User listened to Lesson 1 and reported Mrs Ubuntu pronounces the word **isiZulu** roughly like "eye-sye-Zulu", not native isiZulu. This is a confirmed **user quality rejection** for the narrator's embedded isiZulu term, not a general certification of Thando/Themba's dialogue quality. The source manifest identifies `isiZulu` in exactly the first two Mrs Ubuntu narration cues (orders 1 and 2), both synthesized with the English `en-ZA-LeahNeural` voice.

A text-preserving alternate code-switch audition was implemented in `backend/app/api/endpoints/azure_audition.py`, `POST /api/ubuntu/azure/pronunciation-fix/1` and `/2`, and a listening comparison added to `frontend/static/ubuntu-lesson1-listen.html`. This sends English portions through Leah and only the exact substring `isiZulu` through native-locale Thando. It does NOT overwrite any existing recording. Deployment initiated; check Render live status before claiming samples work. Voice switching may produce an audible timbre change; native speaker must evaluate. If audible voice switching is unsuitable, try SSML pronunciation lexicon and retest within same narrator, keeping the exact source text.

**Do not publish** the lesson until narrator term pronunciation is accepted and actual isiZulu dialogue receives native speaker QA. All existing 139 source cues remain unchanged. User's reported defect is to be preserved in subsequent agent handoffs.

## 2026-11-19 — voice recovery, recording, and classroom (not a completion)

Inspected without generating audio, changing the approved voice, or attaching a file to Whop.

- Original ElevenLabs voice ID `BcpjRWrYhDBHmOnetmBl` is the Mrs Ubuntu / Thandi English guide. The classroom narrator is still Azure `en-ZA-LeahNeural`. The ID does not establish ownership or a commercial license.
- The curriculum repository contains real MP3 objects at `public/audio/guides/`, including `L01A/L01A_slide_1_pre.mp3`. The committed manifest text is a Chitonga alphabet introduction ("Discovering Chitonga"), 270,045 bytes, and the object begins with an ID3 header written by Lavf 60.16.100. Those files are not the isiZulu Lesson 1 script and were not copied into this lesson. A clean local decode was not possible from this workspace: the curriculum repository is not available to this agent's git credential, and the file viewer did not return an intact binary. R2 prefix checks recorded on this date found no `audio/guides/` objects. Restoration of the isiZulu narration without a new recording is therefore not available.
- The 139-cue Azure master is documented from an earlier Render readback as 7,401,068 bytes, 617 seconds, SHA-256 `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`, cue count 139. This session did not re-download the PostgreSQL master, the ZIP, or `courses/zu/beginner-i/lesson-01/v1/master.mp3`. Do not treat that earlier readback as a new verification. The native-only learner sample remains the separate R2 object `v3-stage/native-voices-only.mp3` (28 cues, SHA-256 `9a1e00829c77c6f2dc7646184bd4ad5afae096713f6b3245fe4ef85b57687f3b`). Its private bytes were not played here.
- Reported mismatch: the recording says "Sanibonani" while the screen shows "Ninjani?". In the approved manifest those are orders 4 and 6, with "Unjani?" between them. The caption list is not swapped. The likely cause is concat timing that moves the highlight ahead of the voice. Alignment now joins a breath inside one line when the gap is shorter than the 0.35 second pause between lines, and it still refuses to rewrite timings when the number of spoken regions does not match the cue count. This is not verified against the private MP3.
- Mrs Ubuntu's introduction in the classroom is written and separate from the native greeting recording. Her spoken line does not use personal names or the language name. The approved cue texts, including orders 1 and 2, were not edited.
- Whop course `cors_EYwVx1BwLtuXB`, lesson `lesn_p61ZUtWXJkEie`, still has no verified audio attachment. None was added. Commercial release remains blocked on native-language QA, Azure S0 rights, and owner approval.

## 2026-11-19 — retrieval attempt for the 139-cue master

The historical reference remains version `english-instructor-v1`, SHA-256 `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`, 7,401,068 bytes, 617 seconds, 139 cues. In code, that version replaces orders 1 and 2 with revised English narration and leaves orders 3–139 unchanged. It was not retrieved, decoded, or hashed in this session.

Access blockers, checked directly:

- `GET https://ubuntu-talks-voice-studio-api.onrender.com/health` returned 200.
- `GET /api/ubuntu/azure/lesson1/status` returned 403: “Not authorized to access the Ubuntu Talks Voice Studio backend.” This workspace has no `STUDIO_BACKEND_GATEWAY_TOKEN`.
- `GET https://ubuntu-talks-voice-studio.onrender.com/ubuntu-isizulu-beginner-i-classroom.html` returned 401 from nginx basic auth. No studio password is available here.
- No `UBUNTU_R2_ACCESS_KEY_ID` or `UBUNTU_R2_SECRET_ACCESS_KEY` is present, so `courses/zu/beginner-i/lesson-01/v1/master.mp3` in bucket `ubuntu-talks-instructor-masters` could not be read. The Render Postgres resource `dpg-dbttmmek1f9s739nrs00-a` is also unreachable from this workspace. The only named database secret here is `UBUNTU_STAGING_DB`, and its value is not available to this machine.
- No replacement audio was generated. `POST /api/ubuntu/azure/lesson1/master/start` was not called.

Whop readback the same day: course `cors_EYwVx1BwLtuXB` is `hidden`; lesson `lesn_p61ZUtWXJkEie` has `attachments: []`, `video_asset: null`, and `embed_id: null`; product `prod_EBSCxcpCQvcgI` is `hidden` with `member_count` 0; memberships for that product total 0. Nothing was uploaded or published.

Mrs Ubuntu: no isiZulu introduction MP3 was found to evaluate. The Chitonga guide files were not copied in. Narration audio stays pending. Voice ID `BcpjRWrYhDBHmOnetmBl` stays the historical reference. Leah remains the assigned Azure narrator.

Orders 4, 5, and 6 were not played from the private MP3. If speech-region detection later fails on a retrieved file, the served manifest sets `timing_review_required` and `timing_status: manual_review` instead of treating the stored timestamps as confirmed.
