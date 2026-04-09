# V.I.T.A.L — Technical Audit Report

> Generated 2026-04-09 — principal-engineer review of iOS + Python + inference stack.

---

## Critical (demo-blocking or data-loss risk)

### C1. Tool use disabled in all streaming paths
**File:** `vital/brain.py:397` (`stream_response`)
**Impact:** The LLM sees 6 tool definitions in its system prompt but `stream_response()` never passes `tools=TOOLS` to `client.chat.stream()`. No tool can execute via WebSocket or `/voice/stream`. The LLM may hallucinate tool results or describe what it *would* do.
**Fix:** Pass `tools=TOOLS` and handle `tool_calls` in the streaming loop, or remove tool references from the system prompt in streaming mode.

### C2. Blocking sync DB calls in async FastAPI handlers
**File:** `vital/health_server.py:48-54, 58-60`
**Impact:** `insert_metrics()`, `get_summary()` call psycopg3 synchronously on the uvicorn event loop. Under concurrent WebSocket + HTTP requests, DB queries block *all* async I/O including the realtime voice pipeline.
**Fix:** Wrap in `await loop.run_in_executor(None, ...)` or use psycopg async API.

### C3. Hardcoded LAN IP address
**File:** `ios/VitalApp/ContentView.swift:5-6`
**Impact:** `192.168.1.35:8420` burned into two `let` constants. App fails on any other network. Demo-blocking if presenting from a different WiFi.
**Fix:** Move to build-time config (xcconfig/environment) or a user-editable Settings screen.

### C4. HealthKit completely absent from iOS
**Files:** `ios/project.yml`, entire `ios/Vital/Services/` (missing)
**Impact:** No `NSHealthShareUsageDescription`, no `com.apple.developer.healthkit` entitlement, no `HKHealthStore`. The core value proposition (voice + biometrics) has zero client-side HealthKit integration.
**Fix:** Implement `HealthDataManager` service, add entitlements, request authorization, sync to backend via `POST /health`.

---

## High (correctness / reliability)

### H1. Silent TTS failure — audio gaps with no error
**File:** `vital/voxtral.py:374-375`
**Impact:** `except httpx.HTTPError: pass` in `_stream_tts_to_queue`. A TTS failure for any sentence produces a silent gap — no error sent to the client, no retry. User hears partial response with missing chunks.
**Fix:** Log the error, push an `("error", str(exc))` event into the merged queue, notify the client.

### H2. WebSocket has no reconnection logic
**File:** `ios/VitalApp/ContentView.swift:179`
**Impact:** `URLSession(configuration: .default)` with no custom timeout, no retry, no exponential backoff. A dropped connection kills the session — user must manually restart.
**Fix:** Add reconnection with exponential backoff (1s → 2s → 4s, max 3 attempts).

### H3. `_produce` thread not cancellable on WS disconnect
**File:** `vital/voice_ws.py:47-62`
**Impact:** When WebSocket disconnects mid-turn, `stt_task` is cancelled but `_produce` daemon thread keeps running until `stream_voice_events` finishes. Holds Mistral API connections open for seconds after disconnect.
**Fix:** Add a `stop_event` / threading.Event that `_produce` checks between iterations, or use `asyncio.to_thread` with cancellation.

### H4. `berries_ledger` table never created on server startup
**File:** `vital/health_server.py:32-34` (lifespan)
**Impact:** `init_berries()` is never called in the server lifespan. First `award()` call will crash with a missing table error.
**Fix:** Add `init_berries()` call in `lifespan`.

### H5. Realtime STT model ID not centralized
**File:** `vital/voice_ws.py:27`
**Impact:** `REALTIME_STT_MODEL = "voxtral-mini-transcribe-realtime-2602"` is defined only in `voice_ws.py`, not in `config.py` where all other model IDs live. Easy to miss during upgrades.
**Fix:** Move to `config.py`.

### H6. Race condition in `_stt_loop` after WS close
**File:** `vital/voice_ws.py:142`
**Impact:** Server log shows `RuntimeError: Unexpected ASGI message 'websocket.send', after sending 'websocket.close'`. The `_stt_loop` tries to send `{"type": "state", "value": "listening"}` after the WS is already closed by the client.
**Fix:** Check WS state before sending, or wrap sends in a try/except for `RuntimeError`.

### H7. AVAudioSession not deactivated on stop()
**File:** `ios/VitalApp/ContentView.swift:140-157`
**Impact:** `setActive(false)` is never called. Prevents system from reclaiming audio resources — can interfere with Music, phone calls.
**Fix:** Add `try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)` in `stop()`.

### H8. No AVAudioSession interruption handling
**File:** `ios/VitalApp/ContentView.swift` (VoiceLoop)
**Impact:** If a phone call or Siri interrupts the audio session, the app crashes or hangs silently. No `AVAudioSession.interruptionNotification` observer.
**Fix:** Register for interruption notifications, pause/resume capture and playback.

---

## Medium (quality / maintainability)

### M1. Language hardcoded to French
**Files:** `vital/voxtral.py:31` (batch: `language="fr"`), `vital/voice_ws.py` (realtime: auto-detect)
**Impact:** Inconsistency between batch and realtime STT. No way to override language.
**Fix:** Add `STT_LANGUAGE` to config.py, use consistently.

### M2. `context_bias` unused in STT
**Files:** `vital/voxtral.py:28-33`, `vital/voice_ws.py:117-121`
**Impact:** Mistral realtime STT supports `context_bias` for domain vocabulary boosting. Health terms like "HRV", "SpO2", "variabilité cardiaque" would benefit from hints.
**Fix:** Add a health vocabulary list and pass as `context_bias` parameter.

### M3. No connection pooling for PostgreSQL
**File:** `vital/health_store.py` (`_connect()`)
**Impact:** Every DB call opens/closes a TCP connection. Under load, connection churn becomes a bottleneck.
**Fix:** Use `psycopg_pool.ConnectionPool` (minimal change).

### M4. ContentView.swift is 727 lines — entire app in one file
**File:** `ios/VitalApp/ContentView.swift`
**Impact:** VoiceLoop, all views, audio extensions, palette, state machine — everything in one file. Hard to navigate, test, or review.
**Fix:** Extract `VoiceLoop` → `Services/VoiceLoop.swift`, views → individual files, palette → `Theme.swift`.

### M5. `NSAllowsArbitraryLoads: true` in project.yml
**File:** `ios/project.yml:26`
**Impact:** Disables App Transport Security entirely. App Store rejection if submitted.
**Fix:** Scope to `NSExceptionDomains` for the backend host only.

### M6. Dead code in Models/
**Files:** `Conversation.swift`, `UserProfile.swift`, `AskRequest` in `APIModels.swift`
**Impact:** Unused types that diverge from actual data flow (raw strings in VoiceLoop).
**Fix:** Delete or integrate when needed.

### M7. Nudge thresholds duplicated
**Files:** `vital/nudge.py:14-16`, `vital/brain.py` system prompt
**Impact:** HRV <30ms, sleep <6h, HR >80bpm defined in two places. Manual sync required.
**Fix:** Import from shared constants.

### M8. `speak_streaming` has vestigial `client` parameter
**File:** `vital/voxtral.py:72`
**Impact:** `client: Mistral` parameter is accepted but never used — TTS uses the global httpx client.
**Fix:** Remove the parameter.

### M9. Force-unwrap on `ttsFormat`
**File:** `ios/VitalApp/ContentView.swift:60-65`
**Impact:** `AVAudioFormat(...)!` — safe in practice but violates project Swift conventions.
**Fix:** Use `guard let` with error handling.

### M10. Screen navigation before mic permission granted
**File:** `ios/VitalApp/ContentView.swift:474-476`
**Impact:** `onStart()` (screen transition) executes before `loop.start()` task awaits mic permission. If denied, user briefly sees conversation screen.
**Fix:** Navigate only after `start()` confirms success via a callback/published property.

---

## Nice-to-Have (polish / future-proofing)

### N1. Use `@Observable` macro instead of `ObservableObject`
`VoiceLoop` inherits `NSObject` for no reason — blocks Swift 5.9 `@Observable` adoption. Drop `NSObject`, switch to `@Observable`.

### N2. `.cornerRadius(16)` deprecated in iOS 17+
Replace with `.clipShape(.rect(cornerRadius: 16))`.

### N3. HTTP/2 for TTS httpx client
`http2=False` in `_get_tts_client()`. HTTP/2 multiplexing would reduce connection overhead for concurrent TTS sentences.

### N4. Prewarm CLI creates a real TTS request
`main.py` warms up by sending `"."` via `_stream_tts_to_queue` — a billable API call. Server uses `prewarm_tts()` (HEAD request only). Unify.

### N5. `import base64 as _b64` inside function bodies
`health_server.py:105, 158` — move to module level.

### N6. `get_summary` correlated subquery
Could be replaced with `DISTINCT ON` or window function for better PostgreSQL performance.

### N7. Unbounded queues in voxtral.py
`sentence_q` and `merged` in `stream_voice_events` have no maxsize. If TTS falls behind, memory grows unbounded.

### N8. Add `vital-seed` CLI entry point
`seed_data.py` requires `python vital/seed_data.py <scenario>` — should be a `pyproject.toml` script.

---

## Issue Count

| Severity | Count |
|----------|-------|
| Critical | 4 |
| High | 8 |
| Medium | 10 |
| Nice-to-have | 8 |
| **Total** | **30** |
