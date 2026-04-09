# V.I.T.A.L — Architecture Overview

> Generated 2026-04-09 — principal-engineer audit of the full stack.

## System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Apple Watch Ultra                        │
│  (placeholder — no mic/HealthKit/WCSession implemented yet) │
└─────────────────────────────────────────────────────────────┘
                          │ (future: WatchConnectivity)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    iPhone App (Swift)                        │
│                                                             │
│  VitalApp.swift ─► ContentView ─► VoiceLoop                │
│                                    │                        │
│  ┌──────────────┐  ┌────────────┐  │  ┌──────────────────┐ │
│  │ captureEngine│  │playbackEng.│  │  │ URLSessionWS     │ │
│  │ (mic→PCM16)  │  │(PCM32→spkr)│  │  │ (bidirectional)  │ │
│  └──────┬───────┘  └─────▲──────┘  │  └───────┬──────────┘ │
│         │                │         │          │             │
│         │    VAD (RMS + silence)   │          │             │
│         └──────────────────────────┘          │             │
│                                               │             │
│  Models: HealthMetric, APIModels,             │             │
│          Conversation*, UserProfile*          │             │
│          (* = dead code, unused)              │             │
└───────────────────────────────────────────────┼─────────────┘
                                                │
                        WebSocket ws://host:8420/voice/ws
                        Binary: PCM16 LE @16kHz (up)
                        Binary: Float32 LE @24kHz (down)
                        Text JSON: state/partial/final/token/error
                                                │
┌───────────────────────────────────────────────┼─────────────┐
│                  FastAPI Backend (Python)      │             │
│                                               ▼             │
│  health_server.py                                           │
│  ├── POST /health        ← Apple Shortcuts (HealthKit)      │
│  ├── GET  /health/summary                                   │
│  ├── GET  /health/ping                                      │
│  ├── POST /voice         ← non-streaming (compat)           │
│  ├── POST /voice/stream  ← streaming frames (fallback)      │
│  └── WS   /voice/ws     ← realtime bidirectional (primary)  │
│                                                             │
│  voice_ws.py ◄── handle_voice_ws()                          │
│  ├── _stt_loop ──► Mistral Realtime STT (voxtral-realtime)  │
│  ├── _run_turn ──► brain.py (LLM) + voxtral.py (TTS)       │
│  │                  ├── stream_response() [no tools!]        │
│  │                  └── stream_voice_events() [clause TTS]   │
│  └── audio_q (asyncio.Queue, backpressure, drop-oldest)     │
│                                                             │
│  brain.py                                                   │
│  ├── build_system_message(hours) ← health context from DB   │
│  ├── stream_response()           ← streaming, NO tool use   │
│  ├── chat_with_tools()           ← non-streaming, 6 tools   │
│  └── TOOLS: get_health_summary, get_latest_readings,        │
│             get_health_trend, compare_periods,               │
│             get_correlation, book_consultation               │
│                                                             │
│  voxtral.py                                                 │
│  ├── transcribe()                ← batch STT (language=fr)   │
│  ├── stream_voice_events()       ← LLM tokens + TTS merged  │
│  ├── _stream_tts_to_queue()      ← httpx SSE to Mistral TTS │
│  └── _get_tts_client()           ← shared httpx pool         │
│                                                             │
│  health_store.py ──► PostgreSQL                              │
│  ├── metric_catalog (20 metrics)                            │
│  ├── health_data (time-series)                              │
│  └── psycopg3, sync, no pool, per-call connections          │
│                                                             │
│  nudge.py   ← daily biometric evaluator (cron)              │
│  berries.py ← Alan Play reward ledger                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Mistral AI APIs                           │
│                                                             │
│  STT batch:    voxtral-mini-transcribe-2507                 │
│  STT realtime: voxtral-mini-transcribe-realtime-2602        │
│  LLM:          mistral-small-latest (+ 6 function tools)    │
│  TTS:          voxtral-mini-tts-2603 (SSE streaming)        │
└─────────────────────────────────────────────────────────────┘
```

## Audio Format Chain

```
iPhone mic (hardware: ~48kHz Float32 stereo)
  → AVAudioConverter → PCM Int16 mono @16kHz (interleaved)
  → WebSocket binary frame
  → Mistral Realtime STT (voxtral-mini-transcribe-realtime-2602)
  → transcription events (partial + done)
  → brain.py stream_response() → Mistral Small LLM tokens
  → voxtral.py stream_voice_events() → clause-based sentence chunking
  → Mistral TTS (voxtral-mini-tts-2603) → SSE → base64 PCM Float32 @24kHz
  → WebSocket binary frame
  → AVAudioPCMBuffer Float32 mono @24kHz
  → AVAudioPlayerNode → AVAudioEngine → speaker
```

## State Machine (WebSocket Turn)

```
IDLE ──[start()]──► CONNECTING
  └──[WS open + mic ready]──► LISTENING
       │                          ▲
       │ (user speaks)            │ (all buffers played + server said listening)
       ▼                          │
  [VAD silence 1.5s]             │
       │                          │
       ▼                          │
  THINKING ──[first audio]──► SPEAKING ──[stream done]──┘
```

Client-side gates for SPEAKING → LISTENING:
1. `serverSaidListening == true` (server finished streaming)
2. `pendingBufferCount <= 0` (all audio buffers consumed by AVAudioPlayerNode)
3. Grace period: `lastBufferFrameCount / 24000 + 0.15s`

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| WebSocket over HTTP streaming | Bidirectional needed for realtime STT + live TTS |
| Client-side VAD (not server) | Server STT never emits `done` without explicit stream end |
| Clause-based TTS chunking | Fire TTS on `[,;:.!?]\s` — cuts 200-400ms dead air vs sentence-end only |
| TTS httpx (not SDK) | Mistral Python SDK doesn't expose streaming TTS; raw SSE needed |
| System message cached per WS session | Avoid DB hit per turn; health data is stale but acceptable for ~5min sessions |
| Separate capture/playback engines | Prevent mic picking up speaker output via `.voiceChat` mode |
| Drop-oldest audio queue | Keep audio fresh; stale chunks degrade STT accuracy |

## File Inventory

### iOS (Swift)

| File | Lines | Role |
|------|-------|------|
| `VitalApp/ContentView.swift` | ~727 | **Entire app**: VoiceLoop, views, audio, WS, VAD |
| `VitalApp/VitalApp.swift` | ~8 | Entry point |
| `Vital/Models/HealthMetric.swift` | ~50 | 20-metric type catalog |
| `Vital/Models/APIModels.swift` | ~40 | REST API contracts |
| `Vital/Models/Conversation.swift` | ~15 | Dead code |
| `Vital/Models/UserProfile.swift` | ~20 | Dead code |
| `VitalWatch/VitalWatchApp.swift` | ~8 | Watch entry point |
| `VitalWatch/WatchContentView.swift` | ~25 | Placeholder tap counter |
| `project.yml` | ~40 | XcodeGen config |

### Python Backend

| File | Lines | Role |
|------|-------|------|
| `vital/health_server.py` | 191 | FastAPI routes, uvicorn entry |
| `vital/voice_ws.py` | 210 | Realtime WS pipeline |
| `vital/voxtral.py` | 376 | STT + TTS + streaming |
| `vital/brain.py` | ~400 | System prompt, tools, LLM |
| `vital/health_store.py` | ~200 | PostgreSQL schema + queries |
| `vital/config.py` | ~60 | Constants, env vars |
| `vital/main.py` | ~200 | CLI entry |
| `vital/nudge.py` | 72 | Daily nudge detector |
| `vital/berries.py` | 99 | Reward ledger |
| `vital/seed_data.py` | 155 | Test data generator |
| `vital/audio.py` | 53 | CLI mic recording |
| `vital/viz.py` | 161 | Terminal waveforms |

## Missing Layers (Declared but Not Implemented)

1. **HealthDataManager** — no Swift HealthKit code exists. No `HKHealthStore`, no authorization, no queries.
2. **WatchConnectivity** — `WCSession` never initialized on either target. Watch cannot talk to iPhone.
3. **HTTP client for POST /health** — `HealthPayload` model exists but no code sends it from iOS.
4. **Watch audio** — no mic access, no `WKExtendedRuntimeSession`, no recording.
5. **Streaming tool use** — `stream_response()` doesn't pass `tools=TOOLS`; LLM tools only work via non-streaming `chat_with_tools()`.
