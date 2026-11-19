# Mrs Ubuntu — natural instructor delivery (same approved voice)

**Decision:** Preserve the approved three-voice cast. Mrs Ubuntu remains Azure `en-ZA-LeahNeural`, Thando `zu-ZA-ThandoNeural`, Themba `zu-ZA-ThembaNeural`. Do not substitute a new voice or automatically rerecord commercial assets.

## Learner-feedback finding
The private F0 introduction sounded recognizably synthesized. Transitions were good, but the old public-stage excerpt started at cue 3, omitting Mrs Ubuntu's approved contextual cue 2. The page displayed only four phrases while the original ~85-second sample actually contained about 25 full cues, including singular/plural questions and complete responses.

## Immediate controlled stage
A separate **internal-only, original-source** excerpt uses recorded cue 2 and the ordered native greeting clips; the existing R2 original 85-second file is preserved intact. The learner staging page now requests this introduced sample and its authoritative source manifest, falling back to the original sample with a source-locked matching transcript if staging has not completed. This is not a public or commercially licensed release.

## Audio direction for the **future S0 commercial take**
Keep the identical selected Leah voice and core instructional intent. Improve delivery with a brief, conversational opening, natural punctuation and clauses, and controlled pauses rather than a monotonous paragraph. Preferred draft *subject to script approval*:

> "Welcome to Everyday isiZulu. I'm Mrs Ubuntu. Let's listen to a greeting. A neighbour says hello, and then we greet a group. Notice what changes when we speak to one person or to many. Ready? Listen first—then we'll say it together."

Do not silently replace the canonical approved 139-cue source. Review revised intro alongside the original and approve changes in the new S0 source version. Keep the social and language context intact.

### S0 voice A/B settings to audition
- **A — neutral with conversational script:** `en-ZA-LeahNeural` at native prosody, no voice-style tags, with short-sentence text and deliberate punctuation. This may sound most natural without prosody manipulation.
- **B — subtle warm instructor:** same voice and text, with SSML `<prosody rate="-3%" pitch="-1%">...</prosody>`; short breaks around 250–350ms at clear scene/role transitions. Avoid exaggerated emphasis and long robotic pauses.
- Test only settings Azure specifically supports for the actual resource/voice. Do not assume en-ZA-LeahNeural supports an expressive `mstts:express-as` style such as `cheerful`.
- Keep Thando and Themba unchanged, without anglicizing isiZulu or changing their words.

### Approval test
Compare A/B at matched volume, not just synthesis speed. Select the take with natural South African instructor cadence, a distinct welcome, meaningful conversational purpose, and smooth turn transitions. Then verify against the exact written transcript by cue, with a qualified isiZulu-speaking reviewer. Do not declare an AI voice native/human simply because settings were changed.

**Commercial release gate:** the private F0 recordings are QA reference only; make the final commercial version under a properly verified paid Azure S0 resource with the relevant product terms, and check the regenerated audio before publishing.

## Page content strategy
One free **Lesson 1 sample** on the sales page, not separate audio previews for all ten lessons. The lesson list is a syllabus, not an inventory of publicly playable teasers. Every label must distinguish source-locked sample availability from completion of the full gated lesson. No internal `Planned` production status labels on the learner-facing landing page.
