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

## 2026-11-17/18 — executed factory storage preflight

- Read back and verified full 139-cue internal master from Render logs: `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`, 7,401,068 bytes, duration 617 seconds; this is **technical** validation only, not native-language certification.
- Connected Cloudflare account `FOH Sub Accounts` (`4776967df1db80c2a31141343cd113c1`) already owns private R2 bucket `ubuntu-talks-instructor-masters`; do not create another bucket.
- Created and R2-list-verified `courses/zu/beginner-i/lesson-01/v1/qa-manifest.json` (488 bytes, R2 ETag `a437f9d12d02171ab85bc12b03d8ffd7`). It records SHA/duration and expressly says audio `MASTER_GENERATED_NOT_UPLOADED`, native QA pending, commercial release false, no Whop course ID.
- **The actual MP3 is not uploaded** to this R2 prefix. Browser/Render-only access to the 7.4 MB MP3 and the Cloudflare administration connector are separate; no verified secure binary transfer bridge is configured. Avoid replacing this gap with an external unauthenticated URL or fictional upload receipt. Integrate a server-to-server R2 upload credential/bridge with least-privilege and verify returned object `Content-Type: audio/mpeg`, size and SHA before marking archived.
- Prepared the complete ten-lesson, seven-stage hidden shell template: `factory/isiZulu-beginner-I/whop-hidden-course-shell-spec-v1.json`. Existing Whop courses were inventoried; the protected Whop bridge continues to reject creation with `Migration marker required`. No new course or lessons were created, and no existing Whop content was modified. Resolve the bridge's documented migration allowlist with its administrator rather than guessing markers or writing into unrelated existing courses.

## 2026-11-18 — Secure R2 archive integration implemented

The backend now contains `backend/app/api/endpoints/lesson1_archive.py` and `boto3` in `backend/requirements.txt`, with a restricted, authenticated `POST /api/ubuntu/azure/lesson1/archive/upload` and a GET status route. The production dashboard provides an archive control. When the dedicated backend is configured with `UBUNTU_R2_ACCESS_KEY_ID` and `UBUNTU_R2_SECRET_ACCESS_KEY`, the archive route reads the already-persisted Lesson 1 master from PostgreSQL, confirms full 7,401,068-byte contents and SHA-256 `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`, and privately uploads to the **existing** bucket `ubuntu-talks-instructor-masters` at `courses/zu/beginner-i/lesson-01/v1/master.mp3`. It reads back object size, checksum metadata and content type. If the key exists with unexpected identity, it refuses overwrite. It does not publish a URL or touch Whop. **Credentials are not yet configured**, so the actual 7.4 MB MP3 is still **NOT confirmed in R2**.

To complete the upload, create or use a restricted S3-compatible R2 token with object read/write permission on the existing bucket only, then enter its access-key ID and secret in the **Render Voice Studio API environment**, not frontend, chat, or GitHub. Verify both deploys are live before using the new archive control. Never disclose the credentials. Google Drive binary archive is also pending.

Whop is separately blocked by a connected bridge's `Migration marker required` guard. Creating an independent hidden course through this bridge requires its documented marker contract or administrative authorization; the attempted markers did not pass. Do not bypass or mutate existing Whop Zulu products. The complete canonical ten-lesson seven-stage shell is prepared as `factory/isiZulu-beginner-I/whop-hidden-course-shell-spec-v1.json`.
