# V.I.T.A.L — Prioritized TODO

> Generated 2026-04-09. Ordered by impact × effort ratio for hackathon demo (2026-04-11).

## P0 — Must fix before demo (< 2h total)

- [ ] **C3. Configurable backend URL** — extract hardcoded IP from ContentView.swift into build config or editable constant. *30min*
- [ ] **C2. Async DB calls** — wrap `health_store.*` calls in `run_in_executor` in health_server.py. *30min*
- [ ] **H6. Fix WS send-after-close crash** — guard `_send_text` with WS state check in voice_ws.py. *15min*
- [ ] **H4. Init berries table** — add `init_berries()` to server lifespan. *5min*
- [ ] **H5. Centralize realtime STT model** — move to config.py. *5min*
- [ ] **H7. Deactivate AVAudioSession** — add `setActive(false)` in VoiceLoop.stop(). *10min*
- [ ] **M1. STT language config** — add `STT_LANGUAGE` env var, use in both STT paths. *15min*

## P1 — High impact, do if time allows (hackathon day)

- [ ] **C1. Enable tool use in streaming** — pass `tools=TOOLS` in `stream_response`, handle `tool_calls` in voice_ws.py turn loop. *2-3h*
- [ ] **H1. TTS error propagation** — log + push error event on httpx failure in `_stream_tts_to_queue`. *30min*
- [ ] **H2. WS reconnection** — add retry with backoff in VoiceLoop.connectWebSocket(). *1h*
- [ ] **H8. Audio interruption handling** — register for AVAudioSession interruption notifications. *1h*
- [ ] **M2. Add context_bias** — health vocabulary hints for STT. *30min*
- [ ] **H3. Cancel _produce thread** — add threading.Event for cancellation on WS disconnect. *30min*

## P2 — Quality improvements (post-hackathon)

- [ ] **C4. HealthKit integration** — implement HealthDataManager, add entitlements, authorization, sync to backend. *1-2 days*
- [ ] **M3. Connection pooling** — switch to psycopg_pool.ConnectionPool. *1h*
- [ ] **M4. Split ContentView.swift** — extract VoiceLoop, views, theme into separate files. *2h*
- [ ] **M5. Scope ATS exceptions** — replace NSAllowsArbitraryLoads with domain-specific rules. *30min*
- [ ] **M7. Shared nudge thresholds** — extract to config constants imported by both brain.py and nudge.py. *30min*
- [ ] **M10. Fix navigation timing** — navigate to conversation only after start() succeeds. *30min*

## P3 — Polish (nice-to-have)

- [ ] **M6. Remove dead code** — delete Conversation.swift, UserProfile.swift, AskRequest
- [ ] **M8. Remove vestigial client param** — clean up speak_streaming signature
- [ ] **M9. Remove force-unwrap** — guard let on ttsFormat
- [ ] **N1. @Observable migration** — drop NSObject, switch to @Observable macro
- [ ] **N2. Deprecated cornerRadius** — use clipShape
- [ ] **N3. HTTP/2 for TTS** — enable in httpx client
- [ ] **N4. Unify prewarm** — use HEAD for CLI warmup too
- [ ] **N5-N8.** Minor cleanups (imports, queries, queue bounds, CLI entry point)

## Effort Summary

| Priority | Items | Est. Total |
|----------|-------|------------|
| P0 | 7 | ~2h |
| P1 | 6 | ~6h |
| P2 | 6 | ~2-3 days |
| P3 | 8+ | ongoing |
