# Ubuntu Talks Course Factory — isiZulu Beginner I / Whop binding

**Date:** 2026-11-17. **Mode: HIDDEN / INTERNAL QA / NO PUBLICATION.**

## Precise source of truth
- Original 10-lesson course master: [ubuntu-spark-forge](https://github.com/atw-global/ubuntu-spark-forge-573b8ece), `content/zulu/instructor-master/zulu-beginner-i-master-v2.json`.
- Exact approved Lesson 1 139-cue audio source: `auditions/isiZulu-beginner-I/LESSON_01_APPROVED_139_CUES_AZURE_CAST.json`. Original source stored verbatim; approved voice cast Leah (English), Thando and Themba (isiZulu).
- Binding registry (stable 10 lesson IDs, pending Whop IDs): [whop-course-binding-v1.json](whop-course-binding-v1.json).
- Voice Studio Lesson 1 private QA page: https://ubuntu-talks-voice-studio.onrender.com/ubuntu-lesson1-listen.html
- Audio QA master route: authenticated `GET /api/ubuntu/azure/lesson1/master/status` and `/listen.mp3`; temporary storage is PostgreSQL, not a permanent CDN.
- Google Drive course archive: https://drive.google.com/drive/folders/1-3p5LoBg7_Sl3zVft3sR3xEJ84DFHsKR ; Lesson 1: https://drive.google.com/drive/folders/1iM5Re19ZLRUqCvAz9Q64WfdsmG9_FSqD
- Earlier recording handoff: `docs/HANDOFF_ISIZULU_LESSON_01_AZURE_RECORDING.md`.

## Whop live readback and write blocker
Live Whop company `biz_E1ClvLpPiPOdSj`, experience `exp_ZVznpY7tUX6BAm`.
Existing courses (do not alter): 
- Hidden `Ubuntu Talks Zulu`: `cors_0Tkm2Q8CgvwSs` (3 chapters, 24 lessons)
- Hidden `Ubuntu Talks Zulu — Essentials — Beginner Basics`: `cors_2l6hA9d1WQFLJ` (13 chapters, 13 lessons)
- Hidden `Ubuntu Talks Zulu — Foundations — Complete Beginner Course`: `cors_Q2oinJ8k38m0U` (10 chapters, 10 lessons but different chapter titles)
- Hidden `Ubuntu Talks Zulu — Language Essentials`: `cors_uXc18mFllmVDN`
- Hidden `Ubuntu Talks Zulu — Speaking & Listening Accelerator`: `cors_xYGS20WDwt4qR`
- Currently **visible** `Ubuntu Talks Zulu — Complete Audio Mastery Library`: `cors_WO36piASL9vK9`. Must not change.
These are different products/curricula, not a safe one-to-one target for the institutional Beginner I master.

Attempt to create independent **hidden** `Ubuntu Talks — isiZulu Beginner I — Instructor-Led` shell through connected `mcp__Ubuntu_Talks_Whop_Bridge__whop_write` returned `Whop write failed: Migration marker required`, even when providing a standard migration-style tagline and an explicit `migration_marker` key. **NO NEW WHOP COURSE WAS CREATED; DO NOT INVENT ID OR BLINDLY RETRY.** Locate the bridge's exact marker contract in its owner documentation/implementation or have the authorized administrator enable creation. Do not bypass guard or expose any lesson publicly.

## Factory architecture: source → QA → immutable asset → hidden Whop → entitlement
1. **Source lock:** official master JSON + full teaching cues, voice cast, exact target language, seven-stage learner sequence, source SHA.
2. **Recording and QA:** stable cue IDs and retries, 3 voices, validate every source-language literal against canonical master, native-voice pronunciation review (especially clicks), timing and pacing, narrator English-only role.
3. **Audio master:** assemble approved cues and learner response pauses; produce complete MP3 and per-stage or per-cue chapters, transcript, assessment prompts, duration and SHA256. Store `status=QA` first, not `PUBLISHED`.
4. **Immutable media:** upload versioned assets (e.g. `courses/zu/beginner-i/lesson-01/v1/master.mp3`) to private Cloudflare R2 backed by short-lived authenticated access or proper Whop media upload. Confirm real playable end-to-end, retention and content-type. Mirror audio to Drive and keep a SHA256 inventory. Render free PostgreSQL expires on 2026-12-17.
5. **Whop shell:** create one dedicated HIDDEN institutional course with 10 chapters (one chapter per lesson) and 10 lesson entries, or a chapter with seven subsections if Whop lesson UX demands it. The canonical binding controls IDs and ordering and is written only after verified Whop readback. Never duplicate an existing course with same marker.
6. **Lesson page:** intro/can-do goal, secured audio player, structured transcript, repeat/response activities, native-language pronunciation review, challenge and assessment; accessible and mobile friendly. No direct public static temp URLs.
7. **Access/commerce checks:** Whop entitlement before audio fetch, hidden preview, progress/resume, free/paid checkout gating, refund and revoked access testing, mobile + slow connection testing, no public product until authorized.
8. **Release gates:** exact 139-cue audio/master verified; native QA PASS; commercial Azure licensing verified; media persisted with SHA; correct Whop course/lesson IDs readback; playback and resume tests; explicit owner publish approval.

## Status as of preparation
- Existing Whop courses successfully listed with live connector, including institutional alternatives. No new Whop shell created due migration-marker contract.
- Full Lesson 1 master assembler code added in `backend/app/api/endpoints/lesson1_master.py`, with two corrected English narrator cues and all other 137 cues unchanged. Configured `UBUNTU_LESSON1_MASTER_AUTOSTART=true`. Check live `/master/status` before claiming MP3 complete.
- No confirmed upload of final audio to Drive or R2; no attachment to Whop; native-language QA and commercial-use rights pending.
- Whop binding registry file created as an immutable staging contract, with null IDs until real Whop write/readback. **Never silently populate placeholders as Whop IDs.**

## Next-agent exact continuation
1. Read binding JSON and both recording handoffs.
2. Check `/api/ubuntu/azure/lesson1/master/status`, verify `master.cue_count==139`, SHA and duration, download `/master/download.mp3`; archive to Drive/R2 and readback. If build fails inspect Render API logs and repair only needed steps.
3. Obtain documented Whop bridge migration marker precondition; create only a hidden course if authorized. If not, stop writes and report actual blocker. Keep existing visible and hidden courses unchanged.
4. Construct 10 lesson/chapter identities from canonical JSON; readback actual Whop IDs into binding registry. Attach only versioned audio in the appropriate 10-lesson Whop shell.
5. Test locked learner course from Whop before sale. Preserve seven stages and assessment gate across every language.
