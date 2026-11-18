# Ubuntu Talks — Everyday isiZulu Beginner I: pilot commerce, audio and factory handoff

Date: 2026-11-18. Owner-directed scope: new institutional course ONLY; do not touch legacy Whop Zulu courses or the other platform agent's app infrastructure. Visibility remains HIDDEN. Do not publish until quality gates pass.

## Verified Whop commercial configuration
- Business: `biz_E1ClvLpPiPOdSj`.
- New product: `prod_EBSCxcpCQvcgI` — title `Ubuntu Talks — Everyday isiZulu | Beginner I`.
- Native Courses experience attached to product: `exp_N2y6r4fBZQ7qOv`.
- New course ID previously read back: `cors_EYwVx1BwLtuXB`; its shell has ten chapters and staged Lesson 1 text. Do not confuse with pre-existing course IDs.
- Product visibility: `hidden`. Learner/visitor product page (tested anonymously): https://whop.com/ubuntu-talks/ubuntu-talks-isizulu-beginner-i-instructor-led/
- Introductory paid plan `plan_KhrZ8JGb2YWRt`, $29.99 USD ONE TIME: https://whop.com/checkout/plan_KhrZ8JGb2YWRt
- Whop growth setting discount rate: 38.795918%, resulting in anonymous buyer page display `$49` crossed out, `$29.99` payable, `Save 39%`, `Buy now`. This is an intended/planned standard price, not proof of historical sales at $49. Do not advertise 50% off (mathematically false: $19.01/$49 ~38.8%).
- Existing zero-dollar testing plan `plan_NsCXdzGRAEqvA` is HIDDEN FROM STORE PAGE, not deleted; do not use it as sales CTA.
- Course illustration uploaded to Whop product gallery, product media file `file_YrbXTD2X1rWSC`; current gallery image uses a reduced-resolution Canva thumbnail and requires a full-resolution master replacement.
- Public product title/headline/description have source-grounded greeting demo, explicit not-yet-live audio notice, pricing, and buyer steps. Anonymous browser verified $49/$29.99/39% and Buy now. Checkout payment completion and paid membership entitlement NOT tested.
- Important content gap: native Whop storefront still shows platform-generated cross-sell recommendations not limited to Zulu. Separate platform agent owns custom storefront app; course lane supplies Zulu-only card content and links, does not alter unrelated app.

## Course structure and next level
- Authoritative institutional Beginner I: ten CORE LESSONS in ONE COURSE (approximately 30 minutes of learner experience per lesson). Not ten separate courses. Curriculum: https://github.com/atw-global/ubuntu-spark-forge-573b8ece/blob/atw-global/ubuntu-spark-forge/curriculum/institutional-language-program/languages/zulu/BEGINNER-I-CURRICULUM-v1.md
- Working sequence recommendation: Beginner I -> Beginner II -> Intermediate I -> Intermediate II -> Advanced, subject to separate approved course maps; do NOT infer that Intermediate immediately follows Beginner I without a Beginner II scope decision.
- Legacy courses are a separate inventory and need later content/commerce audit, not overwrite.

## Exact audio source, readiness and blockers
- Lesson 01: 139 approved studio cues, Azure cast Leah (EN), Thando (zu), Themba (zu). Technical master 7,401,068 bytes, 617 seconds, SHA-256 `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`. Native speaker pronunciation QA, Azure commercial entitlement, secure R2/Drive audio binary archival, sample edit, and Whop learner playback still PENDING. Source/recording handoff: https://docs.google.com/document/d/1AKgLf4-FGLbS0EY1NKN0JNmNmUy0HekF3eTY46YrhIM/edit
- Lesson 02: 146 approved source-locked speaking cues, ElevenLabs Studio exact text+voice mappings historically verified. Azure render for this lesson NOT verified. Canonical source: https://github.com/atw-global/ubuntu-spark-forge-573b8ece/blob/atw-global/ubuntu-spark-forge/docs/curriculum/isiZulu-beginner-I/LESSON_02_FULL_SOURCE_LOCKED_CUES.json
- Lesson 03: 134 source-locked draft cues, 6 QA flags; voice staging partially complete, no verified approved recorded audio.
- Lesson 04: 142 draft cues, 3 QA flags.
- Lesson 05: 129 draft cues, 12 QA flags.
- Lesson 06: 146 draft cues, 0 QA flags.
- Lesson 07: 134 draft cues, 3 QA flags.
- Lesson 08: 130 draft cues, 2 QA flags.
- Lesson 09: 129 draft cues, 6 QA flags.
- Lesson 10: 138 draft cues, 7 QA flags.
- Lessons 3–10 are NOT assumed language-approved just because target-language lines are source-locked. Do not upload unverified fragments or claim production readiness. Approved 7-stage lesson cycle: HEAR -> UNDERSTAND -> IMITATE -> MANIPULATE -> RETRIEVE -> CONVERSE -> ASSESS.
- Current Voice Studio production page returned HTTP 401 (nginx) to Voni on 2026-11-18; no authorized direct recording operation performed in this continuation.

## Per-lesson production factory to implement and verify
1. Retrieve frozen source manifest from canonical repo (cue IDs, exact target forms, speaker identity, voice mapping), compute manifest SHA256, compare all target-language cues with original source `model.zu`, reject flagged metadata.
2. Obtain user/native-speaker approval for the exact cue manifest and approved voice cast; protect against subsequent source drift; non-approved lesson manifests must not be automatically rendered for sale.
3. Azure batch worker: deterministic sequential speech synthesis, idempotent clip checkpoints, no regeneration of previously confirmed hashes, rate-limit backoff, resume after Render spin-down, separate English narration and isiZulu voice profiles; collect usage and cost.
4. Assemble validated cue MP3s and learner response pauses into one course master plus a separate *one-minute approved greeting sample* for Lesson 01. Match cue order; record actual durations, content hashes and transcript.
5. Archive to private immutable Cloudflare R2 `ubuntu-talks-instructor-masters/courses/zu/beginner-i/lesson-XX/v1/` and mirror to Drive. Confirm object exists, SHA256 and bytes, MIME `audio/mpeg`; no unverified status claims. The existing R2 manifest is NOT the audio binary.
6. Native QA on pronunciation (especially clicks), pacing, silence, cultural/register accuracy and narrator language separation; rights review on Azure account licensing BEFORE commercial publishing.
7. Attach only QA-approved audio to the correct new Whop lesson ID; test protected entitlement, free sample anonymous playback, purchased learner access, resume/progress, mobile/slow link, refund/revocation. No public product release without owner approval.
8. Reuse same folder/schema/batch runner for all future languages and levels. Track source SHA, cue count, QA status, recording state, MP3 length, audio SHA, R2 key, Drive file ID, Whop lesson ID, rights/QA/release gates and immutable audit log.

## Commercial learning and conversion QA
- Never market incomplete lessons as completed. The paid checkout currently exists on a hidden draft product for testing. Copy describes production status.
- User's intended funnel: anonymous free REAL playable <=60-second native-language greeting sample (after QA), course modules/outcomes, one $29.99 Buy now -> email/Whop checkout -> payment and entitlement, no second cart or login detour.
- No fabricated buyer testimonials, time-limited discounts, or accreditation claims.
- Marketing price should later be adjusted based on pilot conversion/refund and learner completion data, not cosmetic page appearance alone.
