# V.I.T.A.L — Latency Budget

> Generated 2026-04-09. All measurements from real-device testing on local LAN.

## End-to-End Turn Latency (User stops speaking → first audio plays)

**Current:** ~1.5–2.5s (good for voice assistant, target <2s)

```
User stops speaking
  │
  ├── VAD silence detection .................. 1500ms (configurable, was 700ms)
  │   └── vadSilenceDuration=1.5s — intentionally long to avoid mid-sentence cuts
  │
  ├── end_speech signal → server ............. ~5ms (WebSocket RTT on LAN)
  │
  ├── STT finalization ....................... ~50-150ms
  │   └── Mistral processes remaining buffer, emits transcription.done
  │
  ├── LLM TTFT (Time to First Token) ........ 500-800ms ← BOTTLENECK
  │   └── Mistral Small latest, ~2K token system prompt + health context
  │   └── No tool use in streaming path (would add 1-3s per tool call)
  │
  ├── First clause accumulation .............. 50-200ms
  │   └── Wait for ≥4 chars at clause boundary [,;:.!?]\s
  │   └── e.g., "Ok," fires immediately, "Bonjour," at ~100ms
  │
  ├── TTS request + first audio .............. 200-400ms
  │   └── First sentence/clause → Mistral TTS API
  │   └── TLS handshake saved by connection prewarming (~80-150ms saved)
  │
  ├── Audio scheduling ....................... ~5ms
  │   └── AVAudioPlayerNode.scheduleBuffer()
  │
  └── Speaker output ......................... ~10-20ms
      └── AVAudioEngine hardware latency

TOTAL (speech end to first audio): ~800ms–1600ms
TOTAL (including VAD wait):        ~2300ms–3100ms
```

## Latency Optimizations Already Applied

| Optimization | Savings | Where |
|-------------|---------|-------|
| Clause-based TTS chunking | 200-400ms | voxtral.py:173 — fire on `[,;:.!?]\s` not just `.!?` |
| TTS connection prewarming | 80-150ms | voxtral.py:331 — HEAD request at turn start |
| Shared httpx keep-alive pool | 50-100ms/sentence | voxtral.py:315 — reuse TLS connections |
| System message cached per WS session | 50-100ms/turn | voice_ws.py:94 — build once at connect |
| Reuse Mistral client per WS session | ~50ms/turn | voice_ws.py:91 — HTTP pool reuse |

## Remaining Optimization Opportunities

### High Impact

| Opportunity | Est. Savings | Effort | Notes |
|-------------|-------------|--------|-------|
| **Reduce VAD silence to 1.0s** | 500ms | 5min | Risk: more false triggers. Mitigated by manual send toggle. |
| **`context_bias` for STT** | 50-100ms | 30min | Fewer corrections → faster finalization |
| **Speculative TTS on partial transcript** | 200-400ms | 2h | Start TTS on high-confidence partial before `done` — risky, may waste API calls |

### Medium Impact

| Opportunity | Est. Savings | Effort | Notes |
|-------------|-------------|--------|-------|
| **HTTP/2 for TTS** | 20-50ms/sentence | 15min | Multiplexing avoids connection head-of-line |
| **Reduce system prompt length** | 50-100ms TTFT | 1h | Currently ~2K tokens; trim health context to top-5 relevant metrics |
| **Server-side VAD** | Variable | 3h | Detect silence server-side using STT partial timing gaps — eliminates fixed 1.5s wait |

### Low Impact / Already Optimized

| Area | Status |
|------|--------|
| Audio format conversion | Already minimal: single AVAudioConverter call per chunk |
| WebSocket frame overhead | Negligible on LAN (~5ms RTT) |
| JSON parsing | Negligible (<1ms per message) |
| Buffer scheduling | Already immediate — no queuing delay |

## Bottleneck Analysis

```
Component          Time (ms)   % of Total   Controllable?
─────────────────────────────────────────────────────────
VAD silence wait   1500        48%          Yes (config)
LLM TTFT           500-800     25%          No (API)
TTS first audio    200-400     13%          Partial (prewarming helps)
STT finalization   50-150      5%           No (API)
Clause accumulate  50-200      6%           Yes (min chars)
Network + audio    20-40       1%           No (physics)
```

**Verdict:** 73% of perceived latency is either the VAD wait (user-configurable tradeoff) or Mistral API TTFT (not controllable). The Python backend adds <50ms of overhead — language/runtime is not the bottleneck.

## API Cost Per Turn

| API Call | Est. Cost | Notes |
|----------|-----------|-------|
| Realtime STT | ~$0.002 | ~5s of audio per turn |
| LLM (Mistral Small) | ~$0.001 | ~2K prompt + ~100 completion tokens |
| TTS (2-3 clauses) | ~$0.003 | ~50-100 chars per turn |
| **Total per turn** | **~$0.006** | |
| **10-turn session** | **~$0.06** | |
