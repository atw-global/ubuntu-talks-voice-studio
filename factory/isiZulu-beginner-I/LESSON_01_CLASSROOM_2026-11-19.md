# Lesson 1 classroom — engineering record, 19 November 2026

This is not a commercial launch record. Azure S0 rights, native-speaker sign-off, and a real paid membership test remain open. See `LESSON_01_NATIVE_QA_AND_COMMERCIAL_RELEASE_GATE.md`.

## What changed

- The classroom is a Vite React application in `frontend/classroom`, built to `frontend/static/classroom/` and published at `/ubuntu-isizulu-beginner-i-classroom.html`.
- The banner is a 38% / 62% grid. Banner copy is the approved three lines. The artwork is a crop of the authorized cover that keeps the round hut and drops the poster title. There is no striped border.
- Mrs Ubuntu is on-screen written guidance. Her approved voice is still `en-ZA-LeahNeural`. The lesson contract now has an `instructor_audio` object with `status: not_attached` and `media: null`. No instructor recording was synthesized, and she is not given isiZulu lines. The controlled audition remains `MRS_UBUNTU_VOICE_CASTING_SHORTLIST_2026-11-19.md`.
- Thando and Themba remain the only speakers on the dialogue cards. Cards come from the verified manifest.
- Hear is the free stage. Understand through Assess are returned by `GET /api/ubuntu/azure/lesson1/classroom/stages/{id}` only after Whop confirms membership `mem_…` on `prod_EBSCxcpCQvcgI` and `plan_KhrZ8JGb2YWRt`. A missing key or a client flag does not enroll anyone.
- The native MP3 is checksum-verified once and then served from memory, including byte ranges. Nginx disables buffering only on that MP3 path and still forwards `Range`.
- Lesson 2 is not authored. `LESSON_02_CLASSROOM_INTEGRATION.md` says how a later approved lesson uses this shell.
- Lesson titles 2–10 stay visible and marked not authored.

## Live checks on 19 November 2026, after the follow-up

- `GET https://ubuntu-talks-voice-studio.onrender.com/ubuntu-isizulu-beginner-i-classroom.html` returns 401. The studio password is not available in this session, so the deployed page was not opened.
- `GET https://ubuntu-talks-voice-studio-api.onrender.com/health` returns `{"status":"ok"}`. A later request returned in 0.19 seconds.
- `GET https://ubuntu-talks-voice-studio-api.onrender.com/api/ubuntu/azure/lesson1/sample/native-only.mp3` without the gateway token returns 403. The private MP3 was not fetched and was not played.
- Product `prod_EBSCxcpCQvcgI` is still hidden. Plan `plan_KhrZ8JGb2YWRt` is still one-time USD 29.99. Memberships on the product: 0. No charge was made.

## Render audio reliability

The recorded frontend and backend plans are free. Render spins a free web service down after 15 minutes without inbound traffic, and the next request waits about a minute while it starts. That wake, plus a fresh R2 download and checksum after the in-memory cache is discarded, is the infrastructure cause of the intermittent 502. The code cache does not keep a spun-down service awake.

The change that removes the sleep, if the owner approves it, is to move both `ubuntu-talks-voice-studio` (`srv-dbtql9ifngtc739uek90`) and `ubuntu-talks-voice-studio-api` (`srv-dbttr1psrm7s73e17im0`) from compute plan `free` to `0.5c-512mb`. Render lists that plan at $7 per service per month, prorated to the second, so both services are $14 per month on the Hobby workspace. Paid compute does not spin down. This session did not purchase or change either plan. Postgres `ubuntu-voice-studio-db` remains on the free tier and is recorded to expire on 17 December 2026 unless upgraded separately.

## Live Whop read, 19 November 2026

- Product `prod_EBSCxcpCQvcgI` is hidden. Title: Ubuntu Talks — Everyday isiZulu | Beginner I.
- Plan `plan_KhrZ8JGb2YWRt` is one-time, USD 29.99. Checkout: `https://whop.com/checkout/plan_KhrZ8JGb2YWRt`.
- Memberships on that product: 0. No enrolled-learner unlock was exercised, and no test purchase was made.

## Browser evidence

Chromium, against the built page and the real stage-lock functions. The tone used for playback is a generated MP3, not the private R2 master.

Passed: mount, banner ratio 1.63, vertically centered banner text, cover crop, no stripe, play, pause/resume, dialogue seek and highlight, wrong-answer feedback, free Hear completion, locked Understand returning the real checkout URL, no horizontal overflow at 1440, 1024, 768, 390, and 360, and the mobile drawer opening. No page JavaScript exceptions. The expected 403 for a locked stage is logged by the browser.

Not passed: audible playback of the private R2 MP3 in the deployed Render classroom. The public staging URL still answers 401 without the studio password, and this session cannot deploy Render.

## Still blocked

- Qualified native-speaker sign-off.
- Azure S0 commercial rights and a new rendered master. The F0 reference must not be sold.
- A real Whop membership on this plan, then a learner playback and progress test.
- Owner authorization to publish.
- Render deploy of this branch. Staging remains the previous deployment until that happens.
