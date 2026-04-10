# V.I.T.A.L — Voice-Integrated Tracker & Adaptive Listener

## What is this

A vocal health checkup for stress and burnout prevention that:
1. Reads health data from wearables via Thryve API (20 metrics)
2. Uses Mistral Small 4 LLM with 6 tools for conversational analysis
3. Crosses subjective well-being (voice) with objective biometrics to detect burnout
4. Runs a **weekly vocal checkup ritual** (3 structured questions × 7-day biometric trends → score + action). See `wiki/concepts/weekly-vocal-checkup.md`.
5. Sends **biometric-triggered daily nudges** (only when stress signals warrant) via `vital-nudge`.
6. Tracks engagement via **Alan Play berries** — verifiable rewards only (`backend/berries.py`).
7. Web app (frontend/) with Python/FastAPI backend

## Architecture

```
Browser (mic + UI) → frontend/ (web app)
                          ↓
                    FastAPI backend (Python)
                          ↓
              Mistral LLM + Voxtral STT/TTS → SSE stream → frontend
                          ↓
              health_store.py → PostgreSQL (Thryve + HealthKit data)
```

## Project layout

```
backend/                     # Python backend
├── config.py                # Env vars, constants, model IDs
├── voxtral.py               # STT transcription + streaming TTS
├── brain.py                 # System prompt, health context, LLM tool use
├── health_server.py         # FastAPI endpoint
├── health_store.py          # PostgreSQL storage and queries
├── nudge.py                 # Daily biometric-triggered nudge detector
├── berries.py               # Alan Play berries ledger (verifiable rewards)
├── thryve_mcp.py            # Thryve MCP server (dev tooling)
└── seed_data.py             # Test data generator (4 scenarios)
frontend/                    # Web app (team builds during hackathon)
tests/                       # Python tests
```

## LLM Tool Use

brain.py exposes 6 tools to Mistral Small 4 via function calling:

| Tool | Purpose |
|------|---------|
| `get_health_summary(hours)` | Aggregated metrics over a time window |
| `get_latest_readings(metric, limit)` | N most recent raw readings |
| `get_health_trend(metric, days)` | Trend comparison (last 24h vs previous days) |
| `compare_periods(metric, ...)` | Compare two time periods |
| `get_correlation(metric_a, metric_b, days)` | Pearson correlation between two metrics |
| `book_consultation(specialty, urgency, reason)` | Book a health professional (simulated for demo) |

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
| `brain` | brain.py, system prompt, LLM |
| `server` | health_server.py, API endpoints |
| `store` | health_store.py, PostgreSQL |
| `config` | config.py, env vars |
| `nudge` | nudge.py, daily biometric nudge detection |
| `berries` | berries.py, Alan Play rewards ledger |
| `front` | frontend/ web app |

## Commands

```bash
# Run the daily biometric nudge detector (cron / Shortcut hook)
uv run vital-nudge

# Run the health data server
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
