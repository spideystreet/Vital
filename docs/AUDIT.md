# V.I.T.A.L — Technical Audit Report

> Generated 2026-04-09 — principal-engineer review of Python + inference stack.

---

## Critical (demo-blocking or data-loss risk)

### C1. Tool use disabled in all streaming paths
**File:** `backend/brain.py:397` (`stream_response`)
**Impact:** The LLM sees 6 tool definitions in its system prompt but `stream_response()` never passes `tools=TOOLS` to `client.chat.stream()`. No tool can execute via WebSocket or `/voice/stream`. The LLM may hallucinate tool results or describe what it *would* do.
**Fix:** Pass `tools=TOOLS` and handle `tool_calls` in the streaming loop, or remove tool references from the system prompt in streaming mode.

### C2. Blocking sync DB calls in async FastAPI handlers
**File:** `backend/health_server.py:48-54, 58-60`
**Impact:** `insert_metrics()`, `get_summary()` call psycopg3 synchronously on the uvicorn event loop. Under concurrent WebSocket + HTTP requests, DB queries block *all* async I/O including the realtime voice pipeline.
**Fix:** Wrap in `await loop.run_in_executor(None, ...)` or use psycopg async API.

---

## High (correctness / reliability)

### H1. Silent TTS failure — audio gaps with no error
**File:** `backend/voxtral.py:374-375`
**Impact:** `except httpx.HTTPError: pass` in `_stream_tts_to_queue`. A TTS failure for any sentence produces a silent gap — no error sent to the client, no retry. User hears partial response with missing chunks.
**Fix:** Log the error, push an `("error", str(exc))` event into the merged queue, notify the client.

### H2. `_produce` thread not cancellable on WS disconnect
**File:** `backend/voice_ws.py:47-62`
**Impact:** When WebSocket disconnects mid-turn, `stt_task` is cancelled but `_produce` daemon thread keeps running until `stream_voice_events` finishes. Holds Mistral API connections open for seconds after disconnect.
**Fix:** Add a `stop_event` / threading.Event that `_produce` checks between iterations, or use `asyncio.to_thread` with cancellation.

### H3. `berries_ledger` table never created on server startup
**File:** `backend/health_server.py:32-34` (lifespan)
**Impact:** `init_berries()` is never called in the server lifespan. First `award()` call will crash with a missing table error.
**Fix:** Add `init_berries()` call in `lifespan`.

### H4. Realtime STT model ID not centralized
**File:** `backend/voice_ws.py:27`
**Impact:** `REALTIME_STT_MODEL = "voxtral-mini-transcribe-realtime-2602"` is defined only in `voice_ws.py`, not in `config.py` where all other model IDs live. Easy to miss during upgrades.
**Fix:** Move to `config.py`.

### H5. Race condition in `_stt_loop` after WS close
**File:** `backend/voice_ws.py:142`
**Impact:** Server log shows `RuntimeError: Unexpected ASGI message 'websocket.send', after sending 'websocket.close'`. The `_stt_loop` tries to send `{"type": "state", "value": "listening"}` after the WS is already closed by the client.
**Fix:** Check WS state before sending, or wrap sends in a try/except for `RuntimeError`.

---

## Medium (quality / maintainability)

### M1. Language hardcoded to French
**Files:** `backend/voxtral.py:31` (batch: `language="fr"`), `backend/voice_ws.py` (realtime: auto-detect)
**Impact:** Inconsistency between batch and realtime STT. No way to override language.
**Fix:** Add `STT_LANGUAGE` to config.py, use consistently.

### M2. `context_bias` unused in STT
**Files:** `backend/voxtral.py:28-33`, `backend/voice_ws.py:117-121`
**Impact:** Mistral realtime STT supports `context_bias` for domain vocabulary boosting. Health terms like "HRV", "SpO2", "variabilité cardiaque" would benefit from hints.
**Fix:** Add a health vocabulary list and pass as `context_bias` parameter.

### M3. No connection pooling for PostgreSQL
**File:** `backend/health_store.py` (`_connect()`)
**Impact:** Every DB call opens/closes a TCP connection. Under load, connection churn becomes a bottleneck.
**Fix:** Use `psycopg_pool.ConnectionPool` (minimal change).

### M4. Nudge thresholds duplicated
**Files:** `backend/nudge.py:14-16`, `backend/brain.py` system prompt
**Impact:** HRV <30ms, sleep <6h, HR >80bpm defined in two places. Manual sync required.
**Fix:** Import from shared constants.

### M5. `speak_streaming` has vestigial `client` parameter
**File:** `backend/voxtral.py:72`
**Impact:** `client: Mistral` parameter is accepted but never used — TTS uses the global httpx client.
**Fix:** Remove the parameter.

---

## Nice-to-Have (polish / future-proofing)

### N1. HTTP/2 for TTS httpx client
`http2=False` in `_get_tts_client()`. HTTP/2 multiplexing would reduce connection overhead for concurrent TTS sentences.

### N3. `import base64 as _b64` inside function bodies
`health_server.py:105, 158` — move to module level.

### N4. `get_summary` correlated subquery
Could be replaced with `DISTINCT ON` or window function for better PostgreSQL performance.

### N5. Unbounded queues in voxtral.py
`sentence_q` and `merged` in `stream_voice_events` have no maxsize. If TTS falls behind, memory grows unbounded.

---

## Issue Count

| Severity | Count |
|----------|-------|
| Critical | 2 |
| High | 5 |
| Medium | 5 |
| Nice-to-have | 4 |
| **Total** | **16** |
