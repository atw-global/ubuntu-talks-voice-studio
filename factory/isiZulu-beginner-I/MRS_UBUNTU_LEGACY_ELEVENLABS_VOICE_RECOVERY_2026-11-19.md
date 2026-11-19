# Mrs Ubuntu — legacy ElevenLabs voice recovery

**Source-verified on 2026-11-19.** This is a discovery and usage policy, not a license or audio release approval.

## Canonical legacy female guide
- Provider: ElevenLabs
- Voice ID: `BcpjRWrYhDBHmOnetmBl`
- Model used in the legacy worker: `eleven_multilingual_v2`
- Role: English-language Mrs Ubuntu primary narrator; warm, encouraging, conversational.
- Legacy selection explicitly fixed in `atw-global/ubuntu-spark-forge-573b8ece/src/components/experience/journey/narrator.ts`.
- Generation script: `scripts/generate-mrs-ubuntu-audio-v2.mjs`.
- Existing sample/manifest: `public/audio/guides/manifest.json` and `public/audio/guides/L01A/L01A_slide_1_pre.mp3` (Chitonga). A prior production audit records 12 verified pre/post guide MP3s for Chitonga L01A.
- Older, noncanonical script `scripts/generate-mrs-ubuntu-audio.mjs` references stock ElevenLabs Sarah voice ID `EXAVITQu4vr4xnSDxMaL`; **do not accidentally choose Sarah**.
- Secondary *male* narrator ID `Yru1AaCztNSYkMNCbM1k` was an optional structure/emphasis role, not Mrs Ubuntu.

## Private Cloudflare R2 inventory findings
Cloudflare account `4776967df1db80c2a31141343cd113c1` has buckets `ubuntu-talks-media` and `ubuntu-talks-instructor-masters`. Prefix searches `audio/guides/`, `guides/`, and `mrs-ubuntu/` returned no objects in either bucket. `ubuntu-talks-instructor-masters` holds the **Azure mixed** file `courses/zu/beginner-i/lesson-01/v2-stage/mrs-ubuntu-introduced-reference.mp3`; this is not identified as the legacy ElevenLabs voice. The separate legacy guide MP3s exist in the curriculum Git repository, not verified as standalone R2 objects.
The `ubuntu-talks-media` bucket has Hausa final lesson MP3s under `courses/hausa/audio/`. Those may contain a narrator but do not establish reusable ElevenLabs voice rights or stand-alone assets.

## Production policy
- Use neutral English direction (e.g. `Listen to our friends`, `Listen to the conversation`) if Mrs Ubuntu's pronunciation of any names or language names is unverified.
- Keep native target-language greetings and words assigned only to approved target-language speakers.
- Reuse of the ElevenLabs voice across courses is technically possible **only** if the account still has access to that exact voice and the user's specific licensing/consent agreement permits intended commercial use. The existing generated audio cannot be repurposed as new scripts simply because the MP3s are available.
- ElevenLabs states that content generated on paid plans has commercial rights subject to its terms and any voice ownership/library conditions; verify paid tier at the time of generating **each new course recording**, especially if the voice is a shared/professional clone.
- Before generating for the new beginner course: retrieve voice metadata (name/category/ownership/availability), subscription/commercial rights, copy of voice actor license or user consent if applicable; listen blind to a legacy clip; approve the voice for English-only narration; create source-locked guide scripts and versioned segments; store segment MP3 + hash + cue timing privately in R2; insert narration in the lesson sequence without overlapping native dialogue.
- No public or paid distribution until language QA and audio rights signoff.

## Outstanding proof
1. Live ElevenLabs voice ID `BcpjRWrYhDBHmOnetmBl` still belongs to or is usable from the authorized account.
2. Legacy voice's commercial license (or voice actor consent) and current paid generation rights.
3. Approved stand-alone English instructor voice samples for the present isiZulu Lesson 1 — do not claim Chitonga audio is transferable.
4. Actual learner-browser synchronized playback of intro / native exchange / post-guide.
