# V.I.T.A.L — Context for Mistral Vibe

## What V.I.T.A.L is

V.I.T.A.L (Voice-Integrated Tracker & Adaptive Listener) is a **proactive life coach with persistent memory** built on wearable health data. One brain, one memory spine, three durable user-facing surfaces + a one-time vocal onboarding:

0. **Vocal onboarding (Surface 0, one-time)** — ~15 spoken questions on first run, seeds the memory file (Baselines + Context)
1. **Morning brief** — proactive daily ritual (diagnosis + memory callback + adaptive protocol + one question)
2. **Stats dashboard + chat with your data** — on-demand understanding, each stat has an LLM insight
3. **Memory-driven notifications** — silent nudges when a biometric deviates ≥2σ from the user's baseline

Stack: Python/FastAPI backend + web frontend. Mistral Small (9 function-calling tools) + Voxtral STT/TTS + Nebius Llama Guard (safety) + Thryve QA API (wearables).

## Backend surface map

Every module's purpose and the invariants Vibe must respect.

| File | Responsibility | Invariants Vibe must respect |
|------|----------------|------------------------------|
| `backend/config.py` | Env vars, model IDs, Thryve QA URL | No hardcoded secrets. Never commit `.env`. All config via env vars. |
| `backend/thryve.py` | Async Thryve QA client | All Thryve calls go through `ThryveClient` — never raw `httpx`. Two-header auth. |
| `backend/memory.py` | Per-user markdown memory (Baselines / Events / Protocols / Context) | Append-only. 4 sections. Other modules never touch `data/memory/*.md` directly — only via `memory.py`. |
| `backend/brain.py` | LLM system prompt + 9 function-calling tools (chat surface) | Don't modify system prompt or tool list without explicit task approval. Tool count must stay in sync with `CLAUDE.md`. |
| `backend/coach.py` | Morning brief + dashboard insights orchestrator | Insights must cite the user's baseline or a memory Event — never population averages ("14% below your 14-day baseline", not "lower than average"). |
| `backend/nudge.py` | Memory-driven z-score deviation detector (silent notifications) | Triggers only on ≥2σ deviation. Messages must reference a memory Event. Silent — no TTS. |
| `backend/burnout.py` | Burnout score from Thryve analytics (+ raw biometric fallback) | Pure computation, no side effects. |
| `backend/guardrail.py` | Nebius Llama Guard safety check | Every LLM response (brief, chat, notifications) passes through before reaching the user. |
| `backend/health_server.py` | FastAPI endpoints + SSE streaming + notification broadcast | SSE format: `event: {type}\ndata: {json}\n\n`. `patient.token` IS the Thryve `endUserId` IS the memory file key — one hex, no second lookup table. |
| `backend/voxtral.py` | Voxtral STT + streaming TTS | Don't touch without an explicit task saying so. |
| `backend/onboarding.py` | Vocal onboarding session (Surface 0) — start / answer / finalize | Session state is a module-level dict keyed by `endUserId`. `finalize()` writes the initial memory file via `memory.py` only. |
| `backend/onboarding_questions.py` | 15-question bank from the Alan Precision questionnaire | Pure data module. Adding/removing a question is a one-line change — no logic, no side effects. |

## Memory schema

Memory files live at `data/memory/<endUserId>.md`. Four append-only sections:

- **Baselines** — numeric personal norms. *Good:* `2026-04-05 resting_hr_14d_avg = 58 bpm`. *Bad:* `resting HR is around 58`.
- **Events** — time-stamped facts the coach should remember. *Good:* `2026-04-08 skipped sleep after 2am client call, reported exhaustion the next day`. *Bad:* `user sometimes sleeps badly`.
- **Protocols** — active adaptive plans. *Good:* `2026-04-09 magnesium 300mg before bed for 7 days — to test effect on deep sleep`. *Bad:* `try supplements`.
- **Context** — stable user context (job, goals, constraints). *Good:* `software engineer, optimizing for cognitive output, avoids caffeine after 14:00`. *Bad:* `tech worker`.

Rules: **append-only**, **cite in insights** (any LLM output grounded in the user's own history), **never delete** — new info = new line with ISO date prefix.

## 9 tools exposed to Mistral via function calling

Names + one-liners (defined in `backend/brain.py`):

1. `get_user_profile()` — patient age / info
2. `get_vitals(days)` — HRV, resting HR, sleep, HR-during-sleep
3. `get_blood_panel(days)` — glucose, HbA1c + simulated labs
4. `get_burnout_score()` — burnout from Thryve analytics
5. `get_trend(metric, days)` — recent vs baseline comparison
6. `get_correlation(metric_a, metric_b, days)` — Pearson correlation
7. `book_consultation(specialty, urgency, reason)` — simulated booking
8. `read_memory(section)` — Baselines / Events / Protocols / Context
9. `append_memory(section, entry)` — append user-stated context mid-conversation

## Hard constraints

- **No medical diagnosis** — always redirect to a professional
- **Code and comments in English** — product voice is French
- **No Swift** — Vibe handles Python only
- **No git** — never run `git add`, `git commit`, `git push` — main developer handles all commits
- **Pytest class-style** — `class TestXxx`, method `test_scenario`
- **Unit-test mocks** — only mock Mistral and Thryve clients; test real logic otherwise
- **Conventional commits** — used by the main developer (Vibe doesn't commit)

## How tasks work

Main developer writes task files in `.vibe/tasks/`. Run with:

```bash
vibe --agent <agent-name> --prompt "Read .vibe/tasks/<task_file>.md and execute it"
```

Each task has acceptance criteria — verify all before marking done. Return a clear `done` / `blocked` / `wrong-agent` marker at the end.
