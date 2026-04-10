# V.I.T.A.L — Context for Mistral Vibe

## Project overview

V.I.T.A.L (Voice-Integrated Tracker & Adaptive Listener) is a vocal health checkup
that crosses what the user feels (voice) with what their body measures (Apple Watch /
HealthKit), to detect burnout before it happens. Python/FastAPI backend + native Swift
web app. Uses Mistral Small 4 (with 6 tools) + Voxtral STT/TTS.

## Architecture

```
Watch (mic + HealthKit) → iPhone (WatchConnectivity) → Backend (FastAPI)
Backend: STT → brain.py (LLM + 6 tools) → TTS → audio response
```

## Key files

- `backend/config.py` — env vars, constants, model IDs
- `backend/health_store.py` — PostgreSQL storage (20 metrics + trend/correlation queries)
- `backend/health_server.py` — FastAPI receiver
- `backend/brain.py` — LLM system prompt (stress/burnout oriented), tool use (6 tools), health context
- `backend/voxtral.py` — STT + streaming TTS
- `backend/seed_data.py` — test data generator (healthy/stressed/athlete/sleep_deprived)

## Constraints

- No medical diagnosis — always redirect to professionals
- No hardcoded secrets — env vars only
- Code and comments in English
- Conventional commits
- Vibe scope: Python only (docs, tests, audit/refactor). No Swift.

## How tasks work

Claude Code (main dev) writes task files in `.vibe/tasks/`.
Run a task: `vibe --prompt "Read .vibe/tasks/<task_file>.md and execute it"`
Each task has acceptance criteria — verify before marking done.
