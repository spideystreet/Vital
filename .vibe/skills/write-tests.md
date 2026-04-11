# Skill: Write Tests

## Before writing

1. Read the source file you're testing — understand every function, its inputs, outputs, and edge cases
2. Read `.vibe/CONTEXT.md` for project constraints
3. Check if tests already exist in `tests/` for this module — extend, don't duplicate

## Test structure

- Class-based: `class TestFunctionName`
- Method names: `test_<scenario>` — describe the behavior, not the implementation
- One assertion focus per test
- No mocks — test real logic with real inputs
- Use `backend/seed_data.py` scenarios for realistic health data inputs

## What to test per module

### thryve.py
- Daily/epoch fetch helpers parse Thryve payloads into expected shapes
- Unknown metric codes are ignored gracefully
- Auth headers are attached (Basic + endUserId)
- Edge cases: empty `dynamicValues`, missing sections, non-200 responses

### memory.py
- `read_memory(user_id)` returns empty sections dict when file is missing
- `append_memory(user_id, section, entry)` creates the file on first write
- Parser tolerates missing sections and preserves unknown headings
- `upsert_baseline` updates an existing metric row instead of duplicating

### brain.py / coach.py
- `build_system_message()` includes health context, profile, and memory excerpt
- `build_system_message()` without profile/memory falls back to safe defaults
- `execute_tool()` dispatches correctly to each of the 9 tools
- `_execute_tool()` returns valid JSON for all tools, error for unknown tool
- `read_memory` / `append_memory` round-trip through `memory.py`

### burnout.py / nudge.py
- Burnout score handles empty baselines (no division by zero)
- Nudge detector returns `{ triggered: false }` when no threshold is crossed
- Trigger reasons reference the correct metric

### health_server.py
- `GET /api/dashboard/{patient_id}` returns `{ stats, generated_at }` with delta_pct = 0.0 when baseline is missing
- `POST /api/coach/brief` streams `brief` → `audio` → `done` SSE events
- `POST /api/coach/reply` stores the turn and returns `{ ok: true }`
- `GET /api/notifications/stream` emits `ready` then holds the connection open
- `/docs` and `/openapi.json` are reachable (FastAPI auto-exposed)

## After writing

1. Run `uv run pytest <test_file> -v`
2. All tests must pass
3. If a test fails, fix the test (not the source code) unless you found a real bug
