# V.I.T.A.L — Proactive Life Coach Pivot

**Date:** 2026-04-11
**Status:** Design — awaiting user approval before implementation plan
**Context:** Hackathon Alan × Mistral, 12h build, pivot from reactive weekly vocal checkup to proactive life coach with persistent memory.

## Why we're pivoting

The original V.I.T.A.L product was a **reactive** weekly vocal checkup: the user opened the app, answered 3 questions, got a burnout score. It was a ritual the user had to initiate.

Alan's organizer's framing on stage — *"healthcare cost reduction through self-adjustment of daily habits"* — reframes what's needed: not a weekly assessment, but a **coach that watches the user's data continuously, remembers their patterns, and proposes adaptive protocols before problems compound into doctor visits.**

The differentiator vs existing dashboard apps (Bevel, Whoop, Oura) is **persistent memory in the Openclaw / Hermes agent style** — the agent doesn't just show today's numbers, it says *"three weeks ago I saw this exact pattern, here's what we tried, here's what worked."* That's what makes the coaching personal, what makes protocol adherence likely, and what reduces the need to consult a human professional.

## Goals

1. **Proactive, not reactive** — the agent reaches the user; the user doesn't have to ask
2. **Personalized via memory** — every insight is grounded in the user's own past, not population averages
3. **Reduces healthcare friction** — adaptive daily protocols the user can run themselves, documented so a doctor could review them later
4. **Demo-ready in 12h** — 3 surfaces, 1 shared spine, heavy reuse of existing backend modules
5. **Preserve voice identity** — Voxtral stays prominent (Mistral track), but only where voice genuinely adds value

## Non-goals

- Medical diagnosis (hard constraint from CLAUDE.md — agent always recommends a professional for medical concerns)
- Population-level analytics or multi-user features
- Native iOS/watchOS client (web app only for hackathon)
- Retraining the LLM — pure prompt + tool-use + memory injection
- Carrying forward the weekly vocal checkup ritual, berries rewards loop, or standalone nudge cron

## Product surfaces

The pivoted product has exactly **four user-facing surfaces**, all powered by one shared brain + memory:

### Surface 0 — Vocal onboarding (one-time, first-use)

**Why it exists:** Alan Precision's current onboarding is a ~150-question form. V.I.T.A.L's differentiator is a voice-first experience, so the first time a user opens the app we collect their profile by talking with them instead of presenting a wall of inputs. This doubles as a deeper Voxtral integration (partner score) and seeds the memory spine with the exact context Alan already asks members for.

**Trigger:** first app open for a patient whose memory file is empty. The frontend checks memory state on load and routes to onboarding if empty; otherwise it goes straight to the dashboard.

**Flow:**
1. Backend reads the question bank (~15 high-signal questions from the Alan Precision questionnaire — age, sex, weight, height, job, weekly endurance hours, average sleep duration, sitting hours/day, smoking, alcohol frequency, sleep satisfaction 1-10, dominant emotion past 30d, work mental impact 1-10, family CVD y/n, current medications)
2. Backend TTS-streams the first question via Voxtral; frontend plays it and shows the current question text + progress (e.g. `3/15`)
3. User speaks the answer; frontend uploads the audio chunk
4. Backend runs Voxtral STT → transcript, then calls Mistral Small with a structured extraction prompt to pull the typed field value (integer, string, enum) from the transcript
5. Backend SSE-emits `{transcript, extracted, next_question}` + streams the next TTS audio
6. On the last question, backend writes `data/memory/<endUserId>.md` with pre-filled **Baselines** + **Context** sections derived from the extracted answers, then SSE `done` with a redirect hint to the dashboard

**Demo beat:** on stage, the presenter answers **3-5 live questions** (mic on, fields pop into the UI as they're extracted — visible proof Mistral + Voxtral are working together). The remaining ~10 questions are pre-seeded from `data/seeds/pierre_onboarding.json` so the demo stays under ~90 seconds. Immediately after onboarding ends, the morning brief references what the user just said out loud — the single strongest moment in the pitch.

**Scope discipline:** the onboarding question bank is data, not code. It lives in `backend/onboarding_questions.py` (or a JSON file) as a list of `{id, text_fr, text_en, field, type, extraction_hint}` dicts. Adding or removing questions is a one-line data change, not a code change.

**Error handling:** if Voxtral STT fails mid-flow, the frontend falls back to a text input for that one question; the rest of the flow continues by voice. If Mistral extraction returns an unparseable value, the backend re-asks the same question once; on second failure, stores the raw transcript as-is under Context.

### Surface 1 — Morning brief (proactive, ritual)

### Surface 1 — Morning brief (proactive, ritual)

**Trigger:** daily cron at a fixed time (default 08:00 local) *and* a manual "Start my day" button in the web UI. The button is what fires on stage; the cron proves the proactive claim for non-demo use.

**Flow:**
1. Coach reads last 24h biometrics via `thryve.py`
2. Coach reads the user's memory (baselines, past events, protocols tried, stated goals)
3. LLM composes a brief with structure: **diagnosis → memory callback → adaptive protocol for today → one question for the user**
4. Voxtral TTS streams the brief as audio to the web UI; a card renders in parallel with the same content as text
5. User records a spoken reply ("ok I'll skip the workout") or types it
6. Voxtral STT transcribes the reply; coach appends it to memory as the day's intent

**Demo beat:** the "three weeks ago I saw this exact pattern…" line inside the brief is the moment that sells persistent memory to judges. The memory file visibly updates on screen when the user replies.

### Surface 2 — Chat with your data, entered from a stats dashboard (reactive, on-demand)

**Trigger:** user opens the app and lands on a **stats dashboard** showing current Thryve metrics. Each stat has an LLM-generated insight phrase next to it. Tapping a stat opens the chat pre-loaded with that stat's context; the user can also speak/type any question directly.

**Dashboard flow:**
1. Frontend calls `GET /api/dashboard/{patient_id}` on view load (and on refresh)
2. Backend fetches recent vitals from Thryve, reads the user's memory (baselines + recent events), and makes **one LLM call** that returns a JSON list of insights — one per stat — in a single round trip
3. Each insight is grounded in the user's own baseline, not population averages ("*14% below your 14-day baseline*" not "*lower than average*")
4. Response shape:
   ```json
   {
     "stats": [
       {"metric": "hrv", "value": 38, "unit": "ms", "delta_pct": -14,
        "insight": "14% sous ta moyenne 14j — meme pattern que le 21 mars."},
       {"metric": "sleep_quality", "value": 58, "unit": "/100", "delta_pct": -8,
        "insight": "Nuit courte, probablement liee a la baisse de HRV ce matin."}
     ],
     "generated_at": "2026-04-11T09:15:00Z"
   }
   ```

**Chat flow (same as before):**
1. Reuses `brain.py` function-calling loop with the existing tools, extended with `read_memory` and `append_memory`
2. Voxtral STT for voice input, Voxtral TTS for voice output, text fallback available
3. Every response passes through `guardrail.py` (Nebius Llama Guard) before reaching the user
4. Chat can reference events from memory — e.g. *"why did you nudge me yesterday afternoon?"* → agent reads memory → answers with context
5. When the user taps a dashboard stat, the frontend opens the chat with a pre-filled first message (e.g. *"Parle-moi de mon HRV"*) — no backend change needed, it's just a seeded user message

**Reuse note:** the chat path is ~80% free. `brain.py` + `health_server.py` SSE + `voxtral.py` already work end-to-end today. New backend work: the two memory tools + one dashboard endpoint + one small insight-generation helper in `coach.py`. Tap-to-chat is pure frontend.

### Surface 3 — Active notifications (event-driven, silent)

**Trigger:** `nudge.py`, rewired to read the user's **personal baseline from memory** instead of hardcoded thresholds. Fires when a biometric deviates meaningfully from that baseline.

**Flow:**
1. `nudge.py` runs on a short interval (or ticks on new Thryve data)
2. For each metric of interest, compares current value against the 14-day rolling baseline stored in memory
3. On deviation, the LLM composes a message that **references the memory** — not just *"your HRV is low"* but *"3rd time this month your HRV drops the day after <4h deep sleep — same pattern as mid-March"*
4. Message is pushed to the frontend via the existing SSE channel and renders as a silent toast/card — **no TTS**
5. Event is appended to memory so the morning brief and chat can both reference it later

**Deliberate constraint:** notifications do NOT use voice. An interrupting voice is annoying, not coaching. Silent cards preserve the user's focus.

**Demo risk:** needs live biometric movement. If Thryve test data is static during the hackathon, we seed a deviation at demo time or stub a webhook. See "Open risks" below.

## The shared spine — `memory.py`

Every surface reads and writes the same persistent memory store. This is what makes the three surfaces feel like one coach instead of three disconnected features.

**Storage format:** append-only markdown file per user, with structured sections. Markdown chosen over JSON because:
- Human-readable — on stage we can show the file scrolling and judges immediately understand what the agent "remembers"
- LLM-friendly — we can inject relevant sections directly into the system prompt without serialization overhead
- Append-only — no schema migrations, no locking concerns, simple to reason about

**Sections stored:**

| Section | What it holds | Written by | Read by |
|---|---|---|---|
| **Baselines** | Rolling 14/30-day stats per metric (mean, stddev, last-seen) | `coach.py` on every morning brief; `nudge.py` on every tick | all surfaces |
| **Events** | Every notification that fired, every morning brief diagnosis — timestamp + metric + value + interpretation | `nudge.py`, `coach.py` | all surfaces |
| **Protocols tried** | Adaptive protocols the agent proposed, user's accepted/rejected state, observed outcome 3–7 days later | `coach.py` (proposal + outcome check), user reply loop | morning brief (for callbacks), chat |
| **User context** | Goals and subjective context the user stated in chat or morning reply ("I'm training for a marathon", "feeling wired after meetings") | user reply loop, chat extraction | morning brief, notifications, chat |

**Location:** `data/memory/<thryve_end_user_id>.md` — one file per user, gitignored (with a hand-authored un-ignore for the demo profile). The filename uses the Thryve `endUserId` (a hex string) rather than a friendly persona name so memory lookups never need a second lookup table. The demo profile is one of the pre-made Thryve profiles listed in `docs/thryve-hackathon-guide.md`.

**Size management:** for hackathon scope we do not compact or summarize memory. A 7-day demo file is small enough to inject wholesale into the LLM context. Summarization is a post-hackathon concern.

## New modules

### `backend/memory.py` (~80 lines)

Pure functions over the markdown file. No LLM calls, no side effects beyond file I/O.

```
append_event(user_id, section, entry)
read_section(user_id, section) -> str
read_all(user_id) -> str                 # for LLM injection
compute_baseline(user_id, metric, days)  # reads biometrics, writes baseline section
```

### `backend/onboarding.py` (~120 lines) + `backend/onboarding_questions.py` (~80 lines of data)

Drives the one-time vocal onboarding flow. Owns a tiny session state (which question index the user is on), runs each turn through Voxtral STT → Mistral structured extraction → next question TTS, and on completion writes the initial `data/memory/<endUserId>.md` with Baselines + Context sections. No persistence beyond the memory file itself; the in-flight session is kept in memory for the duration of the call.

```
async def start_session(user_id) -> OnboardingSession
async def answer_current(user_id, audio_bytes) -> OnboardingStep  # STT + extract + next question
async def finalize(user_id) -> None                                # write memory file
```

The question bank (`onboarding_questions.py`) is a flat list of dicts keeping the question bank as data, not code. Adding a question is a one-line change.

### `backend/coach.py` (~180 lines)

Orchestrates the morning brief and the dashboard insights — both are memory-grounded LLM generations, so they share a module.

```
async def generate_morning_brief(user_id) -> BriefPayload
async def record_user_reply(user_id, reply_text) -> None
async def generate_dashboard(user_id) -> DashboardPayload      # Surface 2 landing
```

`generate_dashboard` fetches vitals once, reads memory once, and makes a single LLM call that returns insights for every watched metric in one JSON object. No per-stat API calls.

### Rewired `backend/nudge.py` (~60 new lines, removes ~40 old lines)

- Drops the old hardcoded-threshold logic
- Reads baselines from `memory.py`
- On deviation, calls a small LLM prompt (same `brain.py` infrastructure) to compose a memory-grounded nudge
- Pushes via the existing SSE channel in `health_server.py`
- Appends the event to memory

### Two new tools added to `backend/brain.py`

| Tool | Purpose |
|---|---|
| `read_memory(section)` | LLM can retrieve baselines, past events, protocols tried, or user context on demand during chat |
| `append_memory(section, entry)` | LLM can store new user context discovered mid-conversation (e.g. user says "I'm starting a new job next week") |

Because `award_berries` is cut along with `berries.py` (see "What gets cut"), the tool count goes **8 → 9**: `get_user_profile`, `get_vitals`, `get_blood_panel`, `get_burnout_score`, `get_trend`, `get_correlation`, `book_consultation`, `read_memory`, `append_memory`. CLAUDE.md, `docs/ARCHITECTURE.md`, `.vibe/CONTEXT.md`, and `.claude/rules/backend.md` must be updated to reflect this (per `.claude/rules/docs.md`).

## New frontend views (owned by frontend team, in parallel)

0. **Vocal onboarding view (first-open only)** — full-screen mic button + current question text (FR/EN toggle) + `3/15` progress dots. On each question: plays TTS, records reply, displays transcript + extracted field as a toast, advances to next. At the end, redirects to the dashboard.
1. **Stats dashboard (landing view)** — grid of Thryve stat cards, each showing value, unit, delta vs baseline, and the LLM insight phrase. Fetches `GET /api/dashboard/{patient_id}` on load. Tap a stat → opens the chat view with a pre-filled first message about that stat.
2. **Morning brief card** — triggered by "Start my day" button. Plays audio via streaming TTS, shows diagnosis + protocol + memory callback as text. Captures voice reply.
3. **Chat view** — textbox + mic button, streams responses via SSE. Reuses the existing streaming pattern in `health_server.py`.
4. **Live memory panel** — a scrolling log showing recent memory appends in real time. This is the judging moment — visible proof of persistence. Can be a simple reverse-chronological list; no fancy visualization needed.

Notifications render into whatever toast/card component the frontend team chooses — no separate view required.

## What gets cut

| Cut | Reason |
|---|---|
| Weekly vocal checkup ritual | Replaced by the daily morning brief — same purpose, higher frequency, proactive |
| `berries.py` rewards loop | Orthogonal to the coaching thesis; costs time without adding to the demo story |
| Old `nudge.py` cron + hardcoded thresholds | Logic replaced by memory-driven nudges |
| `wiki/concepts/weekly-vocal-checkup.md` | Document now describes a killed surface; keep file but mark as archived or delete |

## Architecture diagram

```
                    ┌──────────────────────────────────┐
                    │         Frontend (web app)       │
                    │  ┌─────────┐ ┌─────┐ ┌─────────┐ │
                    │  │ Morning │ │Chat │ │ Memory  │ │
                    │  │  Brief  │ │ view│ │  panel  │ │
                    │  └────┬────┘ └──┬──┘ └────▲────┘ │
                    └───────┼─────────┼─────────┼──────┘
                            │ SSE     │ SSE     │ SSE
                    ┌───────▼─────────▼─────────┴──────┐
                    │       FastAPI (health_server)    │
                    └───┬───────────┬───────────┬──────┘
                        │           │           │
                ┌───────▼──┐  ┌─────▼─────┐ ┌───▼──────┐
                │ coach.py │  │ brain.py  │ │ nudge.py │
                │ (brief)  │  │  (chat)   │ │ (notifs) │
                └────┬─────┘  └─────┬─────┘ └────┬─────┘
                     │              │            │
                     │     ┌────────┴──────┐     │
                     └────▶│   memory.py   │◀────┘
                           │ (markdown    │
                           │  append log) │
                           └───────┬──────┘
                                   │
                    ┌──────────────┼─────────────┐
              ┌─────▼────┐  ┌──────▼────┐ ┌─────▼──────┐
              │thryve.py │  │burnout.py │ │guardrail.py│
              │(Thryve)  │  │(score)    │ │(Nebius)    │
              └──────────┘  └───────────┘ └────────────┘
```

Voxtral (STT/TTS) is invoked from the morning brief and chat paths; omitted from the diagram for clarity.

## Error handling

- **Memory file missing on first use:** `memory.py` creates it with empty sections on first read.
- **Thryve API failure:** `coach.py` falls back to "I couldn't read your biometrics this morning — how are you feeling?" and logs the error. Chat gracefully degrades to memory-only answers.
- **LLM returns unsafe content:** `guardrail.py` already blocks this; on block, the user sees a generic "I can't help with that — please consult a professional" message. Non-negotiable per CLAUDE.md.
- **TTS stream interruption:** frontend falls back to text-only rendering of the brief/chat response.

## Testing

- **`memory.py`:** unit tests for append, read, baseline computation — no DB, no API, pure file I/O.
- **`coach.py`:** integration test with a mocked `brain.py` and a seeded memory file — asserts brief contains diagnosis + memory callback + protocol.
- **Rewired `nudge.py`:** unit test with a seeded baseline and a fabricated deviation — asserts a message is generated and the event is appended to memory.
- **New brain tools:** unit tests asserting `read_memory`/`append_memory` are correctly called by the LLM loop when the prompt references past events.
- Existing tests (`test_burnout.py`, `test_health_server.py`, `test_nudge.py`) updated for the new signatures.

## Open risks

1. **Live biometric movement for notifications demo.** Thryve provides pre-made data profiles (`docs/thryve-hackathon-guide.md`) with rich historical data, but we can't guarantee a live deviation during the 3-minute stage slot. **Decision (2026-04-11): accept a scripted fallback.** We seed the history we want to reference in the demo user's memory file and ship a hidden `POST /dev/fire-notification` endpoint so the presenter can trigger the notification on cue. The endpoint is dev-only and not documented in the public README.
2. **Thryve QA environment and credentials.** The hackathon runs against `https://api-qa.thryve.de` (not the production URL currently hardcoded in `backend/config.py`). Partner credentials (`THRYVE_USER`/`THRYVE_PASSWORD`) and app credentials (`THRYVE_APP_ID`/`THRYVE_APP_SECRET`) are provided by the organizer at the start of the hackathon. **Mitigation:** Task 0 of the implementation plan switches the base URL to QA and wires one pre-made profile's `endUserId` into the patient registry before anything else depends on live Thryve data.
3. **Pre-made profile selection.** The profiles table in the Thryve guide offers 8 personas (Whoop athlete, Apple sedentary techie, Withings senior heart patient, etc.). The demo narrative ("HRV dropped 14%, same pattern as 3 weeks ago") fits the **Active Gym Guy (Whoop)** profile best because Whoop produces reliable HRV data. **Decision pending user input:** which profile anchors the demo? Defaulting to Active Gym Guy / `2bfaa7e6f9455ceafa0a59fd5b80496c` unless user says otherwise.
2. **12h budget pressure.** Three surfaces + memory spine + frontend is tight. **Mitigation:** surfaces ranked by demo value — morning brief > chat > notifications. If we slip, notifications get cut first. Chat is nearly free so it stays.
3. **Memory file becoming the LLM context bottleneck.** For a 7-day demo this is fine, but injecting a full 30-day log into every prompt is wasteful. **Mitigation:** for hackathon, inject only the last 7 days + current baselines. Full summarization is post-hackathon.
4. **Medical-diagnosis drift under proactive framing.** A proactive coach is more tempted to prescribe. **Mitigation:** reinforce the "always recommend a professional for medical concerns" rule in the new `coach.py` system prompt, and keep `guardrail.py` in the path for every brief and every notification, not just chat.
5. **Numeric claims in morning brief vs. real Thryve data shape.** The demo narrative assumes the LLM will produce lines like *"HRV at 38ms, 14% below your 14-day baseline"*. The numbers must actually match the real Thryve profile data or the demo loses credibility. **Mitigation:** during dress rehearsal, read the real `get_vitals` response for the chosen profile and verify the seeded memory baselines are inside ±1σ of the real mean. If the real profile has HRV mean=60 but we seeded mean=51, the LLM's delta math will contradict the displayed numbers on screen.

## Build sequence (for the plan phase)

1. `memory.py` + tests (nothing else depends on this → build first)
2. New brain tools `read_memory` / `append_memory` + tests
3. `coach.py` morning brief generator + tests
4. Morning brief endpoint in `health_server.py` + SSE wiring
5. Rewire `nudge.py` to use memory + push via SSE
6. Doc sync (CLAUDE.md, ARCHITECTURE.md, CONTEXT.md, backend.md) per `.claude/rules/docs.md`
7. Frontend views (in parallel with 3–6, owned by frontend team)
8. Demo data seeding + dress rehearsal

## Commit scopes (new)

| Scope | Covers |
|---|---|
| `memory` | `memory.py`, memory section schemas |
| `coach` | `coach.py`, morning brief logic |

Existing scopes (`brain`, `server`, `nudge`, `front`) stay as defined in CLAUDE.md.
