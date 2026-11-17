# Ubuntu Talks Voice Studio — isiZulu Beginner I casting research

Research date: 2026-11-17. **Research shortlist, not approved voice casting and not exported audio.**

## Source-locked reference voices
Canonical cast: `docs/curriculum/isiZulu-beginner-I/AGENT_HANDOFF_START_HERE.md` in `atw-global/ubuntu-spark-forge-573b8ece`.
- MRS_UBUNTU / Thandi, ElevenLabs ID `BcpjRWrYhDBHmOnetmBl`: narrated English coaching, language `en-ZA`.
- ZULU_A / Mapendo, ElevenLabs ID `dOqxOZEisn8SiUH1dPCC`: spoken isiZulu demonstrations, language `zu-ZA`.
- ZULU_B / Gawain, ElevenLabs ID `x52Gqgso2pdbdr7KngsJ`: spoken isiZulu demonstrations, language `zu-ZA`.

These are source-role assignments, **not** proof that any alternative voice sounds like an ElevenLabs voice. No properly licensed reference clips were auditioned in this assessment. Do not clone third-party stock voices without the relevant rights/consent.

## Actual language-capable voice candidates

| Role | Audition priority | Voice / locale | Notes |
| --- | --- | --- | --- |
| Thandi / Mrs Ubuntu | 1 | Microsoft Azure `en-ZA-LeahNeural` | Female South African English; strong accent fit for English lesson guidance, not an acoustic match yet |
| Thandi / Mrs Ubuntu | 2 | Microsoft Azure `zu-ZA-ThandoNeural` | Female isiZulu voice for Zulu narration; not automatically correct for English instruction |
| Mapendo / ZULU_A | 1 (casting unconfirmed) | Microsoft Azure `zu-ZA-ThandoNeural` | Female native-locale Zulu voice, candidate only pending reference audition |
| Mapendo / ZULU_A | 2 (casting unconfirmed) | Microsoft Azure `zu-ZA-ThembaNeural` | Male native-locale Zulu voice, candidate only pending reference audition |
| Gawain / ZULU_B | 1 (casting unconfirmed) | Microsoft Azure `zu-ZA-ThembaNeural` | Male native-locale Zulu voice, candidate only pending reference audition |
| Gawain / ZULU_B | 2 (casting unconfirmed) | Microsoft Azure `zu-ZA-ThandoNeural` | Female native-locale Zulu voice, candidate only pending reference audition |

**Important:** The named ElevenLabs stock voices do not establish each speaker's gender, timbre, vocal age or sound. Azure presently publishes only TWO distinct `zu-ZA` neural identities (female Thando and male Themba); it is **not** an equivalent three-voice substitute. We must obtain authorized audition recordings and compare timbre with native-speaker judgment before assigning Mapendo/Gawain. No claim of "closest" beyond language/role constraints is made.

Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support

## Self-hosted options and licensing

- OpenSpeakers ships Qwen3, Chatterbox, Kokoro, VibeVoice, and others, but none has verified native `zu-ZA` support for commercial-quality isiZulu lessons. Qwen3-TTS explicitly advertises ten non-Zulu languages: https://github.com/QwenLM/Qwen3-TTS
- Africa TTS provides `zul` and default voices on CPU, but **its model and default voices are CC-BY-NC-4.0**. This is not cleared for sold lessons or commercial studio operation. Code is MIT, distinct from model weights: https://github.com/AfriSpeech/africa-tts
- Meta MMS TTS weights are CC-BY-NC-4.0; fine-tuned derivatives remain non-commercial. No commercial deployment without explicit rights: https://github.com/AfriSpeech/afri-vits-finetuner
- Fish S2-Pro weights' research license requires separate commercial rights. Do not activate it for sold courses by default: https://huggingface.co/AEmotionStudio/fish-speech-s2-pro/blob/main/LICENSE
- An MIT/Apache code license does not automatically clear model checkpoint or recording rights.
- Azure `zu-ZA-ThandoNeural`, `zu-ZA-ThembaNeural`, `en-ZA-LeahNeural` are **cloud voices, NOT downloadable Vast.ai GPU models**. They need a separate Azure Speech service and API adapter integrated into the Voice Studio; no such adapter is installed yet. Review Microsoft service terms, pricing, and intended recorded-content use before launch.
- Microsoft lists an F0 free tier of 500,000 neural-TTS characters/month, subject to Azure account eligibility and quotas: https://azure.microsoft.com/en-us/pricing/details/speech/

## Benchmark before approving

1. Obtain authorized reference audio for Thandi/Mapendo/Gawain or ask a native speaker who knows the original casting to audition.
2. Select a source-locked short English narration cue and at least six isiZulu cues (click consonants, noun-class agreement, names, phrase and slow/normal speed).
3. Generate consistent auditions from Azure's three candidates using own authorized Azure connection and from any rights-cleared self-hosted language model.
4. Blind-review for Zulu phonetics, intelligibility, voice/persona match, voice distinction and fatigue over a full lesson, not mere generic naturalness.
5. Preserve role mapping in a versioned manifest, **do not overwrite** lesson speech cues or original ElevenLabs IDs until approval.
6. Only after commercial/licensing approval generate full lessons and stage exports in Cloudflare R2.

## Current deployment / cost position
- Ubuntu Talks Voice Studio frontend, isolated OpenSpeakers API, PostgreSQL and Redis are deployed on Render.
- Vast.ai API read-only connectivity verified. **No Vast.ai GPU worker, audio model, Azure integration, generated audio or approved substitute cast yet.**
- Do not rent GPUs merely to use Azure voices; those voices run on Microsoft's cloud.
