# V.I.T.A.L — Architecture Overview

> Last updated 2026-04-11 — reflects the proactive coach pivot (see `docs/superpowers/specs/2026-04-11-proactive-coach-pivot-design.md`).

## Thesis

V.I.T.A.L is a **proactive life coach with persistent memory**. One brain, one memory spine, three user-facing surfaces: **morning brief**, **stats dashboard + chat**, **memory-driven notifications**. Every insight is grounded in the user's own personal baseline, not population averages.

## System Diagram

```
                       Browser (web app)
                ┌────────┬───────────┬────────────┐
                │        │           │            │
                ▼ fetch  ▼ SSE       ▼ SSE        ▼ SSE
           /dashboard /coach/brief  /coach/reply  /notifications/stream
                │        │           │            │
                └────────┴─────┬─────┴────────────┘
                               │
          ┌────────────────────▼────────────────────┐
          │    FastAPI (backend/health_server.py)   │
          │    OpenAPI UI: /docs   Schema: /openapi │
          └──┬───────────┬───────────┬──────────────┘
             │           │           │
       ┌─────▼────┐ ┌────▼─────┐ ┌──▼──────┐
       │ coach.py │ │ brain.py │ │ nudge.py│
       │          │ │          │ │         │
       │  morning │ │  chat +  │ │ z-score │
       │  brief + │ │  9 tools │ │deviation│
       │ dashboard│ │          │ │detector │
       └─────┬────┘ └────┬─────┘ └────┬────┘
             │           │            │
             │   ┌───────┴───────┐    │
             └──▶│   memory.py   │◀───┘
                 │               │
                 │ data/memory/  │
                 │ <endUserId>.md│
                 │               │
                 │ Sections:     │
                 │ - Baselines   │
                 │ - Events      │
                 │ - Protocols   │
                 │ - Context     │
                 └───────┬───────┘
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
┌──────▼─────┐   ┌───────▼──────┐  ┌───────▼──────┐
│ thryve.py  │   │ burnout.py   │  │ guardrail.py │
│            │   │              │  │              │
│ Async      │   │ Burnout      │  │ Nebius Llama │
│ httpx      │   │ score from   │  │ Guard 3 8B   │
│ two-header │   │ Thryve       │  │              │
│ auth       │   │ analytics    │  │ Checks every │
│            │   │              │  │ LLM response │
│ QA:        │   │              │  │ before reply │
│ api-qa.    │   │              │  │              │
│ thryve.de  │   │              │  │              │
└────────────┘   └──────────────┘  └──────────────┘

          ┌──────────────────────┐
          │  voxtral.py          │  (invoked from coach.py + brain.py)
          │                      │
          │  STT: voxtral-mini-  │
          │       transcribe     │
          │  TTS: voxtral-mini-  │
          │       tts-2603       │
          └──────────────────────┘
```

## Surfaces → modules

| Surface | Entry point | Owning module |
|---|---|---|
| Vocal onboarding (Surface 0, one-time) | `POST /api/onboarding/start/{patient_id}` → `.../answer` → `.../finalize` | `onboarding.start_session()` / `record_answer()` / `finalize()` |
| Morning brief (proactive) | `POST /api/coach/brief` → SSE | `coach.generate_morning_brief()` |
| Morning brief reply | `POST /api/coach/reply` | `coach.record_user_reply()` |
| Stats dashboard (landing) | `GET /api/dashboard/{patient_id}` | `coach.generate_dashboard()` |
| Chat with your data | POST chat endpoint → SSE | `brain.chat_with_tools()` |
| Active notifications | `GET /api/notifications/stream` (SSE subscribe) + `POST /dev/fire-notification` | `nudge.fire_manual()` + `health_server._broadcast_notification()` |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/coach/brief` | Surface 1 — streams `brief` + `audio` + `done` events |
| `POST` | `/api/coach/reply` | Surface 1 — records user reply, appends to memory |
| `GET`  | `/api/dashboard/{patient_id}` | Surface 2 — stats + LLM insights JSON (one round trip) |
| `GET`  | `/api/notifications/stream` | Surface 3 — long-lived SSE subscribe channel |
| `POST` | `/dev/fire-notification` | Demo fallback — manually trigger a notification |
| `POST` | `/api/onboarding/start/{patient_id}` | Surface 0 — begin vocal onboarding session |
| `POST` | `/api/onboarding/answer/{patient_id}` | Surface 0 — record one answer, advance to next question |
| `POST` | `/api/onboarding/finalize/{patient_id}` | Surface 0 — seed `data/memory/<patient_id>.md` with Baselines + Context |
| `POST` | `/dev/onboarding/seed/{patient_id}` | Demo fallback — pre-fill the session from `data/seeds/pierre_onboarding.json` |
| `GET`  | `/api/patients` | Patient registry (demo) |
| `GET`  | `/health/ping` | Liveness |
| `GET`  | `/docs` | FastAPI Swagger UI (auto from Pydantic) |
| `GET`  | `/openapi.json` | OpenAPI schema |

## LLM tools (9, registered in `brain.py`)

| Tool | Purpose |
|---|---|
| `get_user_profile()` | Patient name, age |
| `get_vitals(days)` | HRV, resting HR, sleep, HR during sleep |
| `get_blood_panel(days)` | Glucose, HbA1c + simulated labs |
| `get_burnout_score()` | Burnout score from Thryve analytics |
| `get_trend(metric, days)` | Recent vs baseline for one metric |
| `get_correlation(metric_a, metric_b, days)` | Pearson between two metrics |
| `book_consultation(specialty, urgency, reason)` | Simulated booking |
| `read_memory(section)` | Retrieve a memory section (Baselines / Events / Protocols / Context) |
| `append_memory(section, entry)` | Append new user-stated context mid-conversation |

## Persistent memory (`memory.py`)

Per-user append-only markdown file at `data/memory/<thryve_end_user_id>.md`. The filename is the Thryve `endUserId` hex string — the same identifier used as `patient.token` in `PatientContext`. No second lookup table.

Sections:

| Section | Written by | Read by |
|---|---|---|
| **Baselines** — rolling 14/30-day stats per metric (mean, stddev, n) | `coach.py` on every brief; `nudge.py` on every tick | all surfaces |
| **Events** — every notification that fired, every morning brief diagnosis | `nudge.py`, `coach.py` | all surfaces |
| **Protocols** — proposed protocols with accepted/rejected + observed outcome | `coach.py` + user reply loop | morning brief, chat |
| **Context** — user-stated goals / subjective context from chat or brief replies | user reply loop, chat extraction | morning brief, notifications, chat |

The memory blob is injected directly into system prompts — no JSON serialization overhead. For a 7-day demo, the whole file fits comfortably in context.

## Audio flow

```
Morning brief:
  coach.generate_morning_brief()
    → LLM JSON response { diagnosis, memory_callback, protocol, question, raw_text }
    → health_server streams event: brief
    → voxtral.stream_voice_events(raw_text)
    → base64 PCM chunks streamed as event: audio
    → event: done

Chat:
  brain.chat_with_tools()
    → LLM tokens + tool calls
    → voxtral.stream_voice_events() merges text + TTS
    → SSE: event: emotion, event: text, event: audio, event: done
```

## Notifications broadcast

`health_server.py` holds an in-process `set[asyncio.Queue]` of subscribed SSE clients. `_broadcast_notification(payload)` fan-outs to every queue. `POST /dev/fire-notification` is the demo hook — it calls `nudge.fire_manual()` (which runs the LLM to compose a memory-grounded message) and pushes the result to every subscriber.

Design choice: silent. No TTS on notifications. An interrupting voice is annoying, not coaching.

## Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, `httpx.AsyncClient`, `uvicorn` |
| LLM | Mistral Small 3 (`mistral-small-latest`) with function calling |
| STT | Voxtral (`voxtral-mini-transcribe-2507`) |
| TTS | Voxtral (`voxtral-mini-tts-2603`) via raw SSE |
| Health data | Thryve QA (`api-qa.thryve.de/v5`), two-header auth |
| Safety | Nebius Llama Guard 3 8B |
| Storage | Per-user markdown files in `data/memory/` — no database |
| Tests | `pytest` + `pytest-asyncio` |

## Error handling

| Failure | Behavior |
|---|---|
| Memory file missing on first use | `memory.py` creates an empty file with all four sections |
| Thryve API failure | `coach.py` degrades to *"I couldn't read your biometrics — how are you feeling?"*; chat degrades to memory-only answers |
| LLM returns unsafe content | `guardrail.py` blocks; user sees *"I can't help with that — please consult a professional"* (non-negotiable per CLAUDE.md) |
| TTS stream interruption | Frontend falls back to text-only rendering |
| Dashboard LLM call failure | Empty insights returned; UI still renders the raw numbers and deltas |
| No baseline stored when `/dev/fire-notification` called | Returns 400 with an explicit error — demo-time signal to seed the baseline |

## File inventory (backend)

| File | Role |
|---|---|
| `backend/config.py` | Env vars, constants, Thryve QA URL, model IDs |
| `backend/thryve.py` | Async Thryve client (two-header auth) |
| `backend/memory.py` | Per-user markdown append log, baseline I/O |
| `backend/brain.py` | System prompt, 9 tools, `chat_with_tools()`, `prefetch_session()` |
| `backend/coach.py` | `generate_morning_brief()`, `generate_dashboard()`, `record_user_reply()` |
| `backend/burnout.py` | Burnout score computation |
| `backend/nudge.py` | Memory-driven deviation detector, `fire_manual()` for demo |
| `backend/onboarding.py` | Vocal onboarding session (start / answer / finalize) — writes initial memory file |
| `backend/onboarding_questions.py` | 15-question bank (pure data) sourced from the Alan Precision questionnaire |
| `backend/guardrail.py` | Nebius Llama Guard 3 check |
| `backend/voxtral.py` | STT batch + streaming TTS |
| `backend/health_server.py` | FastAPI app, endpoints, SSE helpers, notification broadcast |
| `backend/thryve_mcp.py` | Thryve MCP server (dev tooling) |
| `backend/seed_data.py` | Test data generator |

## Deprecated / unused

- `backend/health_store.py` — PostgreSQL store from the pre-pivot era. Memory spine replaces it for coaching data; Thryve is the source of truth for biometrics.
- `backend/voice_ws.py` — Realtime WebSocket voice pipeline. The pivot uses SSE-only. File left in place but unreferenced by the new endpoints.
- `backend/berries.py` — **deleted** during the proactive coach pivot along with the `award_berries` tool. Rewards loop was orthogonal to the coaching thesis.

## Key constraints

- **No medical diagnosis** — guardrail on every brief, every chat turn, every notification. Non-negotiable.
- **No secrets in code** — env vars only.
- **Code + comments in English**, product voice in **French**.
- **Thryve QA environment only** during the hackathon.
- **Pre-made Thryve profiles** — we do NOT create users. Demo profile: Active Gym Guy (Whoop), `endUserId = 2bfaa7e6f9455ceafa0a59fd5b80496c`. Catalog: `data/AIHackxThryve_Data_Profiles_Data-Profile.csv`.
