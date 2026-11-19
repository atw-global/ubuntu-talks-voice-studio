# Adding Lesson 2 to the existing classroom

Lesson 2 uses the Lesson 1 classroom shell. Do not create another app, product, course, or frontend repository.

Lessons 2–10 are **not authored**. This file is the integration path only.

## What stays

- React app in `frontend/classroom`
- Banner, type, and Mrs Ubuntu written guide
- Stage order: Hear, Understand, Imitate, Manipulate, Retrieve, Converse, Assess
- Activity types already implemented: `choice`, `match`, `order`, `self_check`
- Server routes under `/api/ubuntu/azure/lesson1/classroom/` until a shared lesson parameter is added
- Whop product `prod_EBSCxcpCQvcgI`, course `cors_EYwVx1BwLtuXB`, plan `plan_KhrZ8JGb2YWRt`
- Voices: `en-ZA-LeahNeural` for English guidance, `zu-ZA-ThandoNeural` and `zu-ZA-ThembaNeural` for isiZulu dialogue

## What a Lesson 2 change supplies

1. A source-locked cue file, the same shape as `backend/app/data/lesson01_approved_139.json`.
2. A private MP3 and timed manifest in R2, with a checksum check before any byte is returned. Do not publish a public object URL.
3. Activity copy whose isiZulu and English strings are copied from that cue file. `self_check` stays a learner self-assessment and does not report a pronunciation score.
4. An access record that marks lesson `02` as `open` only after the manifest verifies. Until then the catalog keeps `not_authored`.
5. An `instructor_audio` object. Leave `status` as `not_attached` and `media` as `null` unless a separate approval attaches a recording for `en-ZA-LeahNeural`. The proposed audition script in `classroom-lesson-v1.json` is not lesson audio.

## How to wire it

1. Add the verified manifest and media routes beside the Lesson 1 sample routes. Keep range responses on the MP3 route only.
2. Add the lesson's stages to the server catalog. Hear may be the free stage. Every other stage returns 403 with no activity body until `membership_record_grants` is true.
3. Point the classroom lesson loader at the new lesson id. The shell, player, dialogue strip, and practice components stay as they are.
4. Rebuild with `npm run build:classroom` from `frontend/` and deploy the existing Render frontend service. Do not add a second site.
5. Play the private Lesson 2 MP3 in a browser, including seek and caption sync, before calling the lesson open.

## Still blocked for every lesson

Native-speaker sign-off, commercial Azure Speech rights, a commercial master from the eligible paid tier, a real Whop membership test, and owner approval for publication. Staging does not clear those gates.
