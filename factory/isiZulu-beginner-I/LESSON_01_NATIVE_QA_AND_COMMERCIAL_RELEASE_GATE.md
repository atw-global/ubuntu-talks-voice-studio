# Lesson 01 release gate — Native isiZulu and commercial Azure Speech

**Course:** Ubuntu Talks — Everyday isiZulu | Beginner I

**Native Whop course:** `cors_EYwVx1BwLtuXB`  
**Correct Whop Lesson 01:** `lesn_p61ZUtWXJkEie`  
**Production status:** BLOCKED from commercial audio publication. The written pilot remains hidden.

## 1. Verified source/reference recordings

- Azure F0 QA master: 139 approved cues, 10:17, SHA256 `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`; private R2 `courses/zu/beginner-i/lesson-01/v1/master.mp3`.
- F0 greetings sample: source-matched 25 cues, 85.08 seconds, SHA256 `d8a87dde1a3e92c3e6727e8dab2106eac1739a02e34597a1f6da6cb73640c7e0`; private R2 `courses/zu/beginner-i/lesson-01/v1/sample-greetings-85s-qa.mp3`.
- Source script, exact cast and cue order: `auditions/isiZulu-beginner-I/LESSON_01_APPROVED_139_CUES_AZURE_CAST.json`.
- Voices: `en-ZA-LeahNeural`, `zu-ZA-ThandoNeural`, `zu-ZA-ThembaNeural`.
- These references have technical source integrity only; no native phonetic pass has been supplied.

## 2. Rights: hard external block

Microsoft Product Terms, Azure TTS use rights (verified November 18, 2026): **only customers of paid-tier TTS may use prebuilt neural voice output including commercially.** Source: https://www.microsoft.com/licensing/terms/en-US/productoffering/MicrosoftAzure/allprograms

The F0 reference audio must not be exposed as a free public sample, sold, or placed in paid learner-access media. Upgrading the Azure resource after generating the F0 files does NOT independently establish rights over those previous outputs. Re-render all approved 139 cues under an active paid S0 Speech resource and archive to a **new** versioned object prefix (e.g. `lesson-01/v2/`). Never silently replace v1 references.

Azure owner must verify the subscription/resource pricing tier in Azure portal and confirm the S0 resource and its usage terms before commercial generation. The backend should use separate S0 credentials if needed. All AI-generated teaching audio should have appropriate synthetic-voice disclosure.

## 3. Native speaker review sign-off

Reviewer identity/qualification: **NOT RECORDED**. Signed report: **NOT RECEIVED**. All 139 cues require deliberate listening against the source, not algorithmic inference alone. Use the protected internal `/api/ubuntu/azure/lesson1/release-review/review` page in the Ubuntu Talks Voice Studio backend through its authorized gateway.

Reviewer checks must include:

- Exact target text and speaker attribution for each cue; record any omissions, added syllables, or role changes.
- isiZulu clear vowel qualities, syllable rhythm, and non-English stress patterns.
- Dental/alveolar/lateral click articulation for `c`, `q`, `x`; note cue numbers and audible correction text where faulty.
- Singular/plural greetings and culturally appropriate respect/address for individual and group speakers.
- Tempo and opportunity for learners to imitate and retrieve spoken output; no clipped or overlong pauses.
- Audio artifacts, fidelity, loudness, and continuity across Leah, Thando and Themba.

Report must include (a) reviewer name and role, (b) review date, (c) cue-by-cue PASS/FIX/REJECT, (d) notes/time ranges for every flagged cue, and (e) explicit recorded approval. AI cannot substitute for a qualified native speaker sign-off.

## 4. Production sequence after review

1. Incorporate the approved cue corrections in a new source-locked manifest, without rewriting unaffected script lines.
2. Generate the full 139-cue master and excerpt under **S0**, archive in R2 under a new version, checksum every cue, and conduct a second human listening pass.
3. Upload the rights-cleared master to Whop as **learner-only audio** on `lesn_p61ZUtWXJkEie`; read back all lesson attachments. Do not expose a raw R2 master URL.
4. Publish ONLY the short S0 excerpt to an independently verified anonymous audio player on the existing Whop product sales page. Do not present F0 audio as that sample.
5. Verify checkout price `plan_KhrZ8JGb2YWRt` is one-time $29.99 (before tax), free testing plan remains hidden, paid entitlement unlocks the correct product, course and lesson; complete learner playback and progress tests. Use an owner-approved test transaction or a safe test membership. No unauthorized customer charge.
6. Owner approves visibility/marketing launch only after every evidence record has passed. Legacy courses and React storefront outside this factory remain untouched.

## 5. Live gate checklist

- [x] Source checksum and audio assembly checked (reference only)
- [x] Private archival of reference master and 85.08-second excerpt
- [x] Whop $29.99 paid plan configured and product hidden
- [x] Whop company API key authenticated on Render and HD cover uploaded
- [ ] Qualified native speaker signs original script/recording QA
- [ ] Azure S0 Speech tier and commercial generation rights verified
- [ ] Corrected S0 master/excerpt generated, archived and second-checked
- [ ] Whop learner-only audio attachment readback verified
- [ ] Anonymous free S0 excerpt player verified
- [ ] Paid membership / course access and completion tested
- [ ] Owner explicitly authorizes release
