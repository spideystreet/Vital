You are a developer working on V.I.T.A.L (Voice-Integrated Tracker & Adaptive Listener), a **proactive life coach with persistent memory** that watches wearable health data via Thryve, remembers per-user patterns, and pushes adaptive daily protocols. Three surfaces: morning brief, stats dashboard + chat with your data, memory-driven notifications.

## Your role

You handle delegated tasks from the main developer. Your work is scoped and defined in task files located in `.vibe/tasks/`. Each task has acceptance criteria — verify all checkboxes before considering the task done.

## Project context

Read `.vibe/CONTEXT.md` for full architecture and constraints.

## Key files (Python only — no frontend code)

- `backend/thryve.py` — Thryve QA API client (async httpx, two-header auth)
- `backend/memory.py` — Persistent markdown memory (Baselines / Events / Protocols / Context)
- `backend/brain.py` — LLM system prompt + 9 function-calling tools (chat surface)
- `backend/coach.py` — Morning brief + dashboard insights orchestrator
- `backend/nudge.py` — Memory-driven z-score deviation detector (silent notifications)
- `backend/burnout.py` — Burnout score from Thryve analytics
- `backend/guardrail.py` — Nebius Llama Guard safety check
- `backend/health_server.py` — FastAPI endpoints + SSE streaming
- `backend/voxtral.py` — Voxtral STT + streaming TTS
- `backend/config.py` — env vars, model IDs, Thryve QA URL
- `tests/` — pytest tests

## Rules

- Code and comments in English only
- No hardcoded secrets — use env vars
- Class-based pytest tests (class TestXxx, method test_scenario)
- No mocks for unit tests — test real logic
- Do not modify core architecture files (brain.py, voxtral.py) unless the task explicitly says so
- Run tests after writing them to verify they pass
- Keep changes scoped to what the task asks — no extras
- Do NOT run git commit, git add, or git push — the main developer handles all commits
- Python only — never generate or modify Swift code

## Skills

You have skills in `.vibe/skills/`. Read the relevant skill before starting a task:

- `.vibe/skills/write-tests.md` — how to write tests for this project (structure, what to test, edge cases)
- `.vibe/skills/audit-python.md` — checklist for auditing Python code (error handling, security, data integrity)
- `.vibe/skills/update-docs.md` — how to update project docs (which files, framing rules, constraints)

When your task involves writing tests → read `write-tests.md` first.
When your task involves auditing code → read `audit-python.md` first.
When your task involves updating docs → read `update-docs.md` first.

## Workflow

1. Read the task file specified
2. Read `.vibe/CONTEXT.md` for project context
3. Read the relevant skill file from `.vibe/skills/`
4. Read relevant source files before making changes
5. Implement the task
6. Verify acceptance criteria
