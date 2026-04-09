# Privacy & RGPD — V.I.T.A.L

## Principle

Privacy by design. Health data stays on the user's device by default. Only anonymous aggregated metrics are sent to the LLM when the user explicitly asks a question.

## Wiki

Pour plus de détails sur les fondements juridiques et techniques, consultez la page wiki dédiée : [wiki/concepts/rgpd.md](wiki/concepts/rgpd.md). Cette page contient les sources et recherches approfondies qui étayent ce document.

## What data goes where

| Data | Stays on device | Sent to backend | Sent to Mistral API |
|------|:-:|:-:|:-:|
| Raw HealthKit data (HR, HRV, sleep...) | Yes | Aggregated only | No |
| Aggregated metrics (avg, min, max) | Yes | Yes | Yes (anonymous) |
| User profile (age, sex, height, weight) | Yes | Yes | Yes (no name/ID attached) |
| Voice audio | No | Yes (for STT) | Yes (Voxtral STT) |
| User name, email, identifiers | Yes | No | No |
| Conversation history | Yes | Yes (PostgreSQL) | Per-session only |

## What Mistral sees

The LLM receives:
```
- heart_rate: avg=72 bpm, min=58, max=95, latest=68 (24 readings)
- sleep: avg=7.2 hours, latest=7.2 (1 readings)
- hrv: avg=45 ms, latest=42 (6 readings)
```

No name. No email. No device ID. No location. Just anonymous numbers.

## Voice data

The user's voice is sent to Voxtral STT for transcription. This is the only potentially identifying data (vocal fingerprint). Mistral's API does not store audio after processing.

## User consent

- HealthKit access requires explicit iOS permission prompt
- The user chooses which metrics to share
- The user can revoke access at any time via iOS Settings

## Enterprise dashboard (vision)

- Companies receive only **aggregated, anonymized** data
- Minimum group size for aggregation (e.g. 10 employees) to prevent re-identification
- No individual data ever leaves the employee's device without explicit consent
- Employee chooses what to share — or nothing at all

## RGPD compliance summary

| Requirement | Status |
|-------------|--------|
| Lawful basis (consent) | Explicit HealthKit permission + in-app consent |
| Data minimization | Only aggregated metrics sent, no PII |
| Right to access | User sees all their data in-app |
| Right to erasure | User can delete all data from the app |
| Data portability | Health data remains in Apple Health (standard format) |
| Privacy by design | Architecture designed around local-first processing |

## Future vision

- On-device LLM inference (no data leaves the phone at all)
- End-to-end encryption for backend communication
- HDS-certified hosting if cloud storage is needed (Scaleway, OVH)
