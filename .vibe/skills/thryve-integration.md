# Skill — Thryve integration

**When to read this:** before any task touching `backend/thryve.py`, `backend/brain.py` tools, metric wiring, or new Thryve endpoints.

## What this skill covers

Adding or modifying a Thryve metric end-to-end. Thryve is the source of truth for wearable health data — there is no local database. When a new metric shows up, it has to flow through the whole stack or it's invisible to the user.

## The 7-step wiring path

Walk every step. If any step fails or is unclear, stop and return `STATUS: blocked`. Do NOT improvise the wiring — half-wired metrics cause silent data loss in `coach.py` / `nudge.py`.

### 1. Metric code

- Check the official catalog in `docs/thryve-full-endpoints.md` and `docs/ref-thryve.md` for the right Thryve numeric code and unit.
- Add the name→code mapping to the appropriate dict in `backend/thryve.py`. Names stay snake_case and match the 20-metric list in `CLAUDE.md`.

### 2. Client method

- Add an `async` method to `ThryveClient` (in `backend/thryve.py`). Never bypass the client — no raw `httpx` calls.
- Two-header auth is handled by `ThryveClient.__init__` — don't reimplement it.
- Return a typed dict (or a small dataclass if a dict isn't enough). Shape should mirror what existing client methods return.

### 3. Brain tool (only if user-facing)

If the metric needs to be reachable via chat (user asks "what's my …?"):

- Add a new tool function in `backend/brain.py` alongside the existing 9 tools.
- Update the Mistral system prompt to mention the new tool, briefly.
- Update the tool list / count in:
  - `CLAUDE.md` (tool count + tool table)
  - `docs/ARCHITECTURE.md` (tool list)
  - `.vibe/CONTEXT.md` (9 tools section — increment)
  - `.claude/rules/backend.md` if it mentions the count
- Per `.claude/rules/docs.md`, grep for stale tool count references in all `*.md` files and fix them.

If the metric is NOT user-facing (e.g., only consumed by `coach.py` internally), **skip this step entirely**. Not every metric needs a tool.

### 4. Memory baseline

If the metric deserves a baseline (it's numeric, stable, and the coach needs to compare recent values against the user's personal norm):

- Extend the Baselines writer in `backend/memory.py` to compute and append the baseline.
- Follow the existing Baselines format: `<ISO date> <metric>_<window>_avg = <value> <unit>`.
- Append-only. Never overwrite previous baselines.

### 5. Consumer

Wire the metric into `backend/coach.py` (morning brief / dashboard insight) or `backend/nudge.py` (z-score deviation detector) **only if the task explicitly says so**. Otherwise, leave consumers alone.

When wiring `coach.py` or `nudge.py`:

- Insights must cite the user's baseline or a memory Event — never population averages.
- `nudge.py` triggers only at ≥2σ deviation — don't lower the threshold without task approval.
- Nudge messages must reference a memory Event.

### 6. Tests

For every step that involved code changes:

- **Client method:** unit test with `httpx` mocked — verify the request URL, headers, and the parsed response shape.
- **Brain tool (if added):** integration test with the Mistral client mocked — verify tool call routing and the tool's returned payload.
- **Baseline writer (if added):** unit test using `monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)`.
- **Consumer changes (if any):** unit test covering the new insight / deviation path.

Run: `uv run pytest tests/test_thryve.py tests/test_brain.py tests/test_memory.py tests/test_coach.py tests/test_nudge.py -v` (only the files you touched).

### 7. Doc sync

Per `.claude/rules/docs.md`, check these docs for stale references after changing tools or metric lists:

- `CLAUDE.md` — tool count, tool table, 20-metric list, project layout
- `docs/ARCHITECTURE.md` — tool list, endpoints, diagram
- `.vibe/CONTEXT.md` — tool count, surface map
- `.claude/rules/backend.md` — module table

Fix any stale references silently. Don't announce unless something significant changed.

## Stop rules

- If Thryve catalog lookup is ambiguous (two metric codes could match) → `STATUS: blocked — thryve catalog ambiguous, main dev to confirm`.
- If wiring touches `brain.py` and the task didn't authorize it → `STATUS: blocked — brain.py edits require explicit task approval`.
- If tests fail and the fix is outside the scope of the task → `STATUS: blocked — <reason>`.

## Don't

- Don't add new dependencies.
- Don't touch `backend/voxtral.py`.
- Don't write directly to `data/memory/*.md` — always go through `memory.py`.
- Don't cite population averages in insights.
