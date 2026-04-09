---
title: Voice Biomarkers
created: 2026-04-07
updated: 2026-04-09
type: concept
tags: [voice-biomarker, biomarker, mistral, voxtral]
sources:
  - voxtral_tts.md
  - raw/articles/04_vital_app_design.md
---

# Voice Biomarkers

## Voxtral TTS

- Neural TTS model in Mistral ecosystem
- arXiv: 2603.25551
- **TTS choice for V.I.T.A.L agent voice response**

### Key Properties
- End-to-end audio generation (architecture details in paper)
- French language support crucial for [[alan]] market
- Consistency: 100% [[mistral]] stack (LLM + TTS)

## Voice as Diagnostic Medium for Burnout

### Why Voice Works
1. **Reduced friction:** Speaking is faster than typing — critical for fatigued users
2. **Richer signal:** Prosodic features (speech rate, pause duration, vocal tone) are validated stress markers in NLP research — Voxtral can extract these beyond text content
3. **Clinical parallel:** Structured clinical interviews are the gold standard for burnout assessment (MBI is interviewer-administered in clinical settings)
4. **Dual function:** Voice provides both subjective answers (what user says) AND objective biomarkers (how user says it)

### Prosodic Features as Stress Markers
- **Speech rate:** Slower speech = fatigue proxy
- **Pause duration:** Longer pauses = cognitive load / exhaustion
- **Vocal tone:** Flat affect = cynicism/depersonalization marker
- **Pitch variance:** Reduced range = emotional exhaustion

### V.I.T.A.L Use
- Weekly check-up via Voxtral (see [[weekly-vocal-checkup]])
- 2-3 minute structured interview covering MBI 3 dimensions
- Voice data processed → structured JSON scores (audio not stored)
- Future: voice biomarkers as additional objective input to risk score

## Related Pages
- [[weekly-vocal-checkup]] — Implementation protocol
- [[vital-app-design]] — Full app architecture
- [[vital-app-design]] — Voxtral prompt design
- [[vital-app-design]] — App architecture

---
**Status:** Updated with prosodic features evidence
**Confidence:** Medium
