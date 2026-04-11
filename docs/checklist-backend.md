> **⚠️ SUPERSEDED (2026-04-11).** Reflects the pre-pivot weekly-checkup build. Current backend plan: `docs/superpowers/plans/2026-04-11-proactive-coach-pivot.md`. Current API contract: `HANDOFF.md`.

# Backend Checklist (Hichem)

## APIs
- [ ] Mistral API connected (mistral-large-3)
- [ ] Voxtral STT connected (voxtral-mini-latest)
- [ ] Voxtral TTS connected (voxtral-mini-tts-2603)
- [ ] ElevenLabs TTS fallback tested (Flash v2.5)
- [ ] Thryve API connected (dual auth working)
- [ ] Nebius Llama Guard connected (Llama Guard 3 8B)

## Thryve Adapter
- [ ] Auth: dual Basic Auth + per-user token working
- [ ] Fetch daily values (POST /v5/dailyDynamicValues)
- [ ] Fetch epoch values (POST /v5/dynamicEpochValues)
- [ ] Fetch user info (POST /v5/userInformation)
- [ ] 2-3 sandbox patients created and returning data
- [ ] Core signals confirmed: RMSSD (3100), SleepQuality (2201), RestingHR (3001), BloodGlucose (3302), HeartRateSleep (3002)
- [ ] Bonus signals tested: SickLeavePrediction (2257), SleepRegularity (2220), RMSSD Sleep (3106)
- [ ] Blood panel: glucose/HbA1c from Thryve + simulated ferritin/cortisol/vitD as JSON

## LLM Tools (8)
- [ ] get_user_profile() — returns patient name, age, devices, blood panel
- [ ] get_vitals(days) — returns HRV, resting HR, sleep quality, HR sleep
- [ ] get_blood_panel(days) — returns glucose, HbA1c, blood pressure
- [ ] get_burnout_score() — computes score + fetches 2257 if available
- [ ] get_trend(metric, days) — compares recent vs baseline
- [ ] get_correlation(metric_a, metric_b, days) — crosses two signals
- [ ] award_berries(amount, reason) — logs reward
- [ ] book_consultation(specialty, urgency, reason) — triggers booking

## Brain (LLM)
- [ ] System prompt: burnout detection persona, French voice, no medical diagnosis
- [ ] Function calling works with all 8 tools
- [ ] Contradiction detection: voice sentiment vs biometric data
- [ ] Protocol generation: 3 concrete actions (nutrition, activity, sleep)
- [ ] Emotion state sent with each SSE chunk (thinking, curious, concerned, alert, encouraging, happy)

## Burnout Score
- [ ] Formula: 100 - (45*RMSSD_norm + 35*Sleep_norm + 20*RHR_norm)
- [ ] 7-day baseline computed per user
- [ ] Score classified: 0-30 green, 30-60 orange, 60-100 red
- [ ] AverageStress (6010) used as bonus if Garmin user

## Voice Pipeline
- [ ] Audio in → Voxtral STT → transcript
- [ ] Transcript → LLM reasoning → response text
- [ ] Response text → Voxtral TTS → streaming audio chunks
- [ ] Full loop < 5 seconds latency target

## FastAPI Endpoints
- [ ] POST /api/checkup/start → { session_id }
- [ ] POST /api/checkup/audio → { transcript }
- [ ] POST /api/checkup/respond → SSE stream (health_data, text, audio, burnout_score, protocol, berries, emotion, done)
- [ ] GET /api/patients → list of sandbox patients
- [ ] GET /api/patient/{id}/summary → burnout score, protocol, berries
- [ ] GET /api/nudge/{patient_id} → triggered nudge if any

## Guardrail
- [ ] Every LLM response checked by Nebius Llama Guard before sending
- [ ] Medical diagnosis blocked (S6 category)
- [ ] Safe response returned if blocked

## Daily Nudge
- [ ] Detector checks biometric thresholds (HRV drop, RHR spike, sleep crash)
- [ ] Returns actionable message only when triggered
- [ ] Endpoint returns { triggered: false } when no signal warrants it

## Patient Switching
- [ ] 2-3 Thryve sandbox users with different health profiles
- [ ] Switch returns different data → different protocol
- [ ] One healthy, one stressed/burnout, one moderate
