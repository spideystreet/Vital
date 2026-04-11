# V.I.T.A.L — Voice-Integrated Tracker & Adaptive Listener

## What is this

A **proactive life coach** based on wearable health data that:
1. Reads health data from wearables via Thryve API (20 metrics, QA environment)
2. Uses Mistral Small LLM with **10 tools** for conversational analysis + persistent memory
3. Keeps a **per-user persistent memory** (Baselines, Events, Protocols, Context, Challenges) as append-only markdown — the Openclaw / Hermes agent pattern — so insights are grounded in the user's own history
4. Runs a **daily morning brief** with diagnosis + memory callback + adaptive protocol + one question. See `backend/coach.py`.
5. Exposes a **stats dashboard + chat-with-your-data** surface: each stat shows delta vs personal baseline plus an LLM insight phrase. Tap a stat to open the chat with that context pre-loaded.
6. Sends **memory-driven notifications** (silent, no TTS) when a biometric deviates ≥2σ from the user's baseline, with messages that reference past events. See `backend/nudge.py`.
7. **Vocal onboarding (Surface 0)** — first-run flow that collects ~15 high-signal answers by voice and seeds the memory file (Baselines + Context). See `backend/onboarding.py`.
8. Web app (frontend/) with Python/FastAPI backend. Three durable surfaces + one-time onboarding share one brain and one memory spine.

## Architecture

```
Browser (mic + UI) → frontend/ (web app)
                          ↓
                    FastAPI backend (Python)
                          ↓
  coach.py (brief + dashboard) ─┐
  brain.py (chat + 10 tools)    ├─► memory.py (data/memory/<endUserId>.md)
  nudge.py (z-score deviation)  ─┘          ▲
                          ↓                  │
              Mistral LLM + Voxtral STT/TTS  │
                          ↓                  │
              thryve.py ──► Thryve QA API ───┘
                          ↓
              SSE stream → frontend (brief / dashboard / notifications / chat)
```

## Project layout

```
backend/                     # Python backend
├── config.py                # Env vars, constants, model IDs, Thryve QA URL
├── voxtral.py               # STT transcription + streaming TTS
├── brain.py                 # System prompt, health context, 10-tool function calling
├── coach.py                 # Morning brief + dashboard insights orchestrator
├── memory.py                # Persistent markdown memory (Baselines/Events/Protocols/Context/Challenges)
├── burnout.py               # Burnout score from Thryve analytics (+ fallback)
├── guardrail.py             # Nebius Llama Guard safety check
├── thryve.py                # Thryve Health API client (async, two-header auth)
├── health_server.py         # FastAPI endpoints + SSE streaming
├── nudge.py                 # Memory-driven z-score deviation detector
├── onboarding.py            # Rigid Q&A onboarding session (Surface 0) — writes initial memory
├── onboarding_questions.py  # 15 high-signal question bank (Alan Precision)
├── vocal_intake.py          # Free-speech vocal intake — 5-category form, LLM field extraction
├── blood_ocr.py             # Blood panel PDF OCR via Mistral files + OCR + biomarker extraction
├── thryve_mcp.py            # Thryve MCP server (dev tooling)
└── seed_data.py             # Test data generator
data/memory/                 # Per-user markdown memory files (gitignored except demo profile)
frontend/                    # Web app (team builds during hackathon)
tests/                       # Python tests
```

## LLM Tool Use

brain.py exposes 10 tools to Mistral Small via function calling:

| Tool | Purpose |
|------|---------|
| `get_user_profile()` | Patient age, info |
| `get_vitals(days)` | HRV, resting HR, sleep, HR-during-sleep, steps |
| `get_blood_panel(days)` | Glucose, HbA1c + simulated lab values |
| `get_burnout_score()` | Burnout score from Thryve analytics |
| `get_trend(metric, days)` | Trend comparison (recent vs baseline) |
| `get_correlation(metric_a, metric_b, days)` | Pearson correlation between two metrics |
| `book_consultation(specialty, urgency, reason)` | Book the right specialist (ORL, cardiologue, ...) with an Alan-covered simulated booking |
| `propose_challenge(title, metric, target, reason)` | Create a personalized micro-challenge calibrated on the user's baseline |
| `read_memory(section)` | Read Baselines / Events / Protocols / Context / Challenges from persistent memory |
| `append_memory(section, entry)` | Append user-stated context discovered mid-conversation |

## Health Metrics (20)

**Vitals (8):** heart_rate, resting_hr, hrv, spo2, respiratory_rate, wrist_temperature, vo2_max, walking_hr_avg
**Activity (7):** steps, active_calories, resting_energy, distance, workout, stand_time, exercise_time
**Sleep (3):** sleep, sleep_deep, sleep_rem
**Environment (1):** audio_exposure
**Mindfulness (1):** mindful_minutes

## Commit scopes

| Scope | Covers |
|-------|--------|
| `tts` | voxtral.py TTS |
| `stt` | voxtral.py STT |
| `brain` | brain.py, system prompt, LLM, tool calling |
| `coach` | coach.py, morning brief, dashboard insights |
| `memory` | memory.py, persistent memory sections |
| `server` | health_server.py, API endpoints, SSE |
| `config` | config.py, env vars |
| `nudge` | nudge.py, memory-driven notification detector |
| `onboarding` | onboarding.py, onboarding_questions.py, first-run vocal flow |
| `front` | frontend/ web app |

## Commands

```bash
# Run the health data server (exposes /docs OpenAPI UI)
uv run vital-server

# Run tests
uv run pytest

# Lint
uv run ruff check backend/
```

## Authorship

Git commit authorship reflects who wrote the code:

| Scenario | git `--author` | Co-Authored-By |
|----------|----------------|----------------|
| User codes alone | project owner | none |
| Claude codes directly | project owner | `claude-code <noreply@anthropic.com>` |
| User delegates to Vibe | project owner | `Mistral Vibe <vibe@mistral.ai>` |
| Claude orchestrates Vibe (background) | `Mistral Vibe <vibe@mistral.ai>` | `claude-code <noreply@anthropic.com>` |
| Mixed (Claude + Vibe both write code) | project owner | both co-authors |

Project owner identity is configured in `.claude/rules/authorship.md` (local, not committed).

## Key constraints

- **No medical diagnosis** — the LLM must ALWAYS recommend a professional for medical concerns
- No secrets in code — everything via env vars
- Code and comments in English
