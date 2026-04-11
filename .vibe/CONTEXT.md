# V.I.T.A.L — Context for Mistral Vibe

## Project overview

V.I.T.A.L (Voice-Integrated Tracker & Adaptive Listener) is a **proactive life coach
with persistent memory** based on wearable health data. One brain, one memory spine,
three user-facing surfaces: **morning brief** (proactive ritual), **stats dashboard +
chat with your data** (on-demand understanding), **memory-driven notifications**
(event-driven, silent). Python/FastAPI backend + web app frontend. Uses Mistral Small
(with 9 tools) + Voxtral STT/TTS + Nebius Llama Guard + Thryve QA API.

## Architecture

```
Browser (mic + UI) → FastAPI backend
Backend: coach.py + brain.py + nudge.py
  → memory.py (per-user markdown at data/memory/<endUserId>.md)
  → thryve.py (Thryve QA wearable data)
  → guardrail.py (every LLM response)
  → voxtral.py (STT / streaming TTS)
  → SSE streams to the frontend (brief / dashboard / notifications / chat)
```

Memory is markdown, append-only, sectioned (Baselines / Events / Protocols / Context).
Every insight the coach produces is grounded in the user's own baseline — never
population averages.

## Key files

- `backend/config.py` — env vars, constants, model IDs, Thryve QA URL
- `backend/thryve.py` — async Thryve client (two-header auth)
- `backend/memory.py` — persistent markdown memory (Baselines / Events / Protocols / Context)
- `backend/brain.py` — LLM system prompt + 9-tool function calling (chat surface)
- `backend/coach.py` — morning brief + dashboard insights orchestrator
- `backend/nudge.py` — memory-driven z-score deviation detector (silent notifications)
- `backend/burnout.py` — burnout score from Thryve analytics
- `backend/guardrail.py` — Nebius Llama Guard check on every response
- `backend/voxtral.py` — STT + streaming TTS
- `backend/health_server.py` — FastAPI endpoints + SSE broadcast

## Constraints

- No medical diagnosis — always redirect to professionals
- No hardcoded secrets — env vars only
- Code and comments in English; product voice in French
- Conventional commits
- Vibe scope: Python only (docs, tests, audit/refactor). No Swift.

## How tasks work

Claude Code (main dev) writes task files in `.vibe/tasks/`.
Run a task: `vibe --prompt "Read .vibe/tasks/<task_file>.md and execute it"`
Each task has acceptance criteria — verify before marking done.
