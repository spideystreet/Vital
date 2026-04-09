# V.I.T.A.L — Privacy & RGPD Review

> Generated 2026-04-09. Review of health data handling for hackathon demo + production readiness.

## Data Classification

| Data Type | Sensitivity | RGPD Category | Current Storage |
|-----------|------------|---------------|-----------------|
| Health metrics (HR, HRV, sleep, etc.) | **High** — Article 9 special category | Health data | PostgreSQL (local) |
| Voice audio (PCM chunks) | **High** — biometric data | Biometric + Health | Transient (not stored) |
| STT transcripts | **Medium** — subjective wellbeing | Health data (contextual) | Transient (not stored) |
| LLM responses | **Low** — generated content | N/A | Transient (not stored) |
| Berries ledger | **Low** — engagement data | Personal data | PostgreSQL (local) |

## Current State Assessment

### What's Good

1. **Voice audio is not persisted** — PCM chunks flow through the WebSocket pipeline and are never written to disk or database. Audio exists only in memory during the turn.

2. **Transcripts are not stored** — STT output (`final_text`) is used for the LLM turn then discarded. No conversation history is persisted server-side.

3. **No user accounts / no PII stored** — single-user design, no email/name/phone in the database. `health_data` table has no `user_id` column.

4. **Database is local** — PostgreSQL runs on the same machine as the server. No cloud database, no third-party hosting.

5. **No secrets in code** — API keys via env vars, `.env` is gitignored.

### What's Concerning

#### P1. Health data sent to Mistral AI (third-party processor)

**Issue:** All 20 health metrics are injected into the LLM system prompt (`brain.py:build_system_message`). Every LLM call sends the user's heart rate, HRV, sleep duration, SpO2, etc. to Mistral's API.

**RGPD impact:** Under Article 9, processing special category data (health) requires explicit consent + a lawful basis. Sending health data to a third-party API processor requires:
- A Data Processing Agreement (DPA) with Mistral
- The user's explicit informed consent
- Data minimization — only send what's strictly necessary

**Current state:** No consent flow exists. No DPA documented. The full health summary (all metrics, min/max/avg/latest) is sent every turn.

**Recommendation:**
- Add a consent screen on first launch explaining what data is shared and with whom
- Document Mistral as a sub-processor in a privacy policy
- Consider sending only relevant metrics per query instead of the full summary

#### P2. Voice audio sent to Mistral STT (biometric processing)

**Issue:** Raw voice audio (PCM16 @16kHz) is streamed to Mistral's realtime STT API. Voice is classified as biometric data under RGPD.

**RGPD impact:** Same Article 9 requirements as health data. Additionally, voice can potentially identify the speaker.

**Current state:** Audio is transient (not stored locally) but is transmitted to Mistral for processing. Mistral's data retention policy applies.

**Recommendation:**
- Verify Mistral's STT data retention policy (do they store audio? for how long?)
- Include voice processing in the consent flow
- Consider on-device STT as a future privacy enhancement (Apple Speech framework)

#### P3. `NSAllowsArbitraryLoads: true` — no transport encryption enforcement

**File:** `ios/project.yml:26`

**Issue:** App Transport Security is completely disabled. All HTTP traffic (including health data in `POST /health` and voice audio) can be intercepted on the network.

**RGPD impact:** Article 32 requires "appropriate technical measures" including encryption in transit. Disabling ATS violates this.

**Recommendation:**
- For hackathon (LAN demo): acceptable with explicit documentation
- For production: enforce HTTPS, use TLS certificates, scope ATS exceptions

#### P4. No data deletion mechanism

**Issue:** No way for the user to delete their health data from the database. No `DELETE /health` endpoint, no "erase my data" feature.

**RGPD impact:** Article 17 — right to erasure. Users must be able to request deletion of their data.

**Recommendation:** Add a `DELETE /health/all` endpoint and a "Delete My Data" button in the app.

#### P5. No data export mechanism

**Issue:** No way for the user to export their health data in a portable format.

**RGPD impact:** Article 20 — right to data portability. Users must be able to receive their data in a structured, machine-readable format.

**Recommendation:** Add a `GET /health/export` endpoint returning JSON or CSV.

#### P6. Health thresholds visible in system prompt

**Issue:** The system prompt in `brain.py` contains hardcoded medical thresholds (HRV <30ms = "stress signal", sleep <6h = "insufficient"). These are sent to the LLM and could surface in responses as medical advice.

**Impact:** The "no medical diagnosis" constraint is enforced via prompt instructions, but thresholds in the prompt create an implicit diagnostic framework.

**Recommendation:** Frame thresholds as "wellness indicators" not "diagnostic criteria" in the prompt. Add stronger disclaimers.

## Hackathon Demo Checklist

For the 2026-04-11 demo, minimum viable privacy:

- [ ] Add a brief consent splash: "V.I.T.A.L sends your health data and voice to Mistral AI for analysis. No data is stored on Mistral's servers beyond processing." (verify with Mistral's ToS)
- [ ] Document that this is a demo/prototype — not for production health use
- [ ] Ensure the LLM always says "consult a professional" for medical questions (already in prompt)
- [ ] Keep `NSAllowsArbitraryLoads` but document it as hackathon-only

## Production Readiness Checklist

For eventual App Store / public release:

- [ ] Privacy policy document (website-hosted URL required for App Store)
- [ ] DPA with Mistral AI
- [ ] Explicit consent flow with granular toggles (health data, voice, analytics)
- [ ] HTTPS everywhere (TLS certificates for backend)
- [ ] Scoped ATS exceptions (no blanket `NSAllowsArbitraryLoads`)
- [ ] Data deletion endpoint + UI
- [ ] Data export endpoint (JSON/CSV)
- [ ] Data retention policy (auto-purge after N days?)
- [ ] HealthKit usage descriptions in project.yml
- [ ] On-device STT option (Apple Speech) for privacy-conscious users
- [ ] Audit log for data access
- [ ] Rate limiting on health data endpoints
- [ ] Authentication (current setup has zero auth — anyone on the network can POST health data)

## Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Health data intercepted (no TLS) | Medium (LAN only) | High | HTTPS for production |
| Mistral stores/uses voice data | Low (check ToS) | High | DPA, consent |
| User can't delete data | Certain | Medium | Add deletion endpoint |
| LLM gives medical advice | Low (prompt guard) | Critical | Keep "consult professional" constraint, add disclaimers |
| No auth on API | Certain (LAN) | Medium | Add API key / token auth for production |
