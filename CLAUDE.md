# V.I.T.A.L — Voice-Integrated Tracker & Adaptive Listener

## What is this

A CLI Python health assistant that:
1. Receives Apple Watch data via Apple Shortcuts → POST JSON → local FastAPI server → PostgreSQL
2. Uses Mistral LLM with health context for conversational analysis
3. Supports voice interaction via Voxtral STT/TTS with streaming playback
4. Displays health data + waveform viz in terminal (Mistral orange aesthetic)

## Architecture

```
iPhone Shortcut (HealthKit) → POST /health → health_server.py → PostgreSQL (health_store.py)
                                                                      ↓
CLI: audio.py → voxtral.py (STT) → brain.py (LLM + health ctx) → voxtral.py (TTS) → viz.py
                                                                      ↓
                                                              main.py (orchestrator)
```

## Project layout

```
vital/
├── main.py          # CLI entry point, conversation loop
├── config.py        # Env vars, constants, model IDs
├── audio.py         # Microphone recording, silence detection
├── voxtral.py       # STT transcription + streaming TTS
├── brain.py         # System prompt, health context, LLM streaming
├── viz.py           # Terminal waveforms, health banner
├── health_server.py # FastAPI endpoint for Apple Shortcuts
└── health_store.py  # PostgreSQL storage and queries
tests/
```

## Commit scopes

| Scope | Covers |
|-------|--------|
| `audio` | audio.py, recording, mic |
| `tts` | voxtral.py TTS |
| `stt` | voxtral.py STT |
| `brain` | brain.py, system prompt, LLM |
| `viz` | viz.py, terminal UI |
| `server` | health_server.py, API endpoints |
| `store` | health_store.py, PostgreSQL |
| `config` | config.py, env vars |
| `cli` | main.py, arg parsing |

## Commands

```bash
# Run the CLI (voice mode)
uv run vital

# Run the CLI (text mode)
uv run vital --text

# Run the health data server
uv run vital-server

# Run tests
uv run pytest

# Lint
uv run ruff check vital/
```

## Authorship

Git commit authorship reflects who wrote the code:

| Scenario | git `--author` | Co-Authored-By |
|----------|----------------|----------------|
| User codes alone | project owner | none |
| Claude codes directly | project owner | `claude-code <noreply@anthropic.com>` |
| User delegates to Vibe | project owner | `Mistral Vibe <vibe@mistral.ai>` |
| Claude orchestrates Vibe (background) | `Mistral Vibe <vibe@mistral.ai>` | `claude-code <noreply@anthropic.com>` |
| Mixed (Claude + Vibe both write code) | project owner | both co-authors |

Project owner identity is configured in `.claude/rules/authorship.md` (local, not committed).

## Key constraints

- **No medical diagnosis** — the LLM must ALWAYS recommend a professional for medical concerns
- No secrets in code — everything via env vars
- Code and comments in English
- Terminal aesthetic: Mistral orange `#ff7000`, block chars, animated waveforms
