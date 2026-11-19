# Lesson 1 classroom — engineering record, 19 November 2026

This is not a commercial launch record. Azure S0 rights, native-speaker sign-off, and a real paid membership test remain open. See `LESSON_01_NATIVE_QA_AND_COMMERCIAL_RELEASE_GATE.md`.

## What changed

- The classroom is a Vite React application in `frontend/classroom`, built to `frontend/static/classroom/` and published at `/ubuntu-isizulu-beginner-i-classroom.html`.
- The banner is a 38% / 62% grid. Banner copy is the approved three lines. The artwork is a crop of the authorized cover that keeps the round hut and drops the poster title. There is no striped border.
- Mrs Ubuntu is on-screen written guidance. Her approved voice is still `en-ZA-LeahNeural`. No new instructor audio was synthesized, and she is not given isiZulu lines.
- Thando and Themba remain the only speakers on the dialogue cards. Cards come from the verified manifest.
- Hear is the free stage. Understand through Assess are returned by `GET /api/ubuntu/azure/lesson1/classroom/stages/{id}` only after Whop confirms membership `mem_…` on `prod_EBSCxcpCQvcgI` and `plan_KhrZ8JGb2YWRt`. A missing key or a client flag does not enroll anyone.
- The native MP3 is checksum-verified once and then served from memory, including byte ranges. The studio proxy forwards `Range` and does not buffer the audio response.
- Lesson titles 2–10 stay visible and marked not authored.

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
