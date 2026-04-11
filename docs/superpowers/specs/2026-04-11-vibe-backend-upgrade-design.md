# Design — Vibe Backend Upgrade

**Date:** 2026-04-11
**Scope:** `.vibe/` configuration only (backend/API concern)
**Goal:** Make Vibe genuinely useful on V.I.T.A.L backend tasks — tests, reviews, audits, docs — without silent failures and without expanding the agent count.

## Problem

The 4 existing Vibe agents (`vital`, `vital-tests`, `vital-review`, `vital-audit`) share a single generic system prompt and differ only in tool permissions. As a result:

- Vibe has no V.I.T.A.L-specific invariants to enforce (Thryve two-header auth, memory append-only, insights must cite baselines, SSE event format, patient.token == endUserId).
- `vital-review` produces vague "looks good" output without file:line citations.
- `vital-tests` has hit silent failures — handing back failing tests claiming success.
- `vital-audit` has `bash = always`, broader than an audit role needs.
- No skill covers the two backend pain points that bite repeatedly: wiring a new Thryve metric through the `thryve → brain tool → memory → coach/nudge` path, and respecting memory schema invariants.

Out of scope: frontend, Swift, orchestration layers, adding more agents.

## Design

Four changes, all inside `.vibe/`:

### 1. Rewrite `.vibe/CONTEXT.md` as a backend surface map

Replace the prose overview with enforceable facts Vibe can cite:

1. **One-liner** — V.I.T.A.L = proactive life coach, 3 surfaces (brief / dashboard+chat / nudges), stack (FastAPI + Mistral Small + Voxtral + Thryve + Llama Guard).
2. **Backend surface map** — table with columns `File | Responsibility | Invariants Vibe must respect`. Rows: `thryve.py`, `memory.py`, `brain.py`, `coach.py`, `nudge.py`, `burnout.py`, `guardrail.py`, `health_server.py`, `voxtral.py`, `config.py`.
3. **Memory schema** — Baselines / Events / Protocols / Context with one good example line each, append-only rule, citation rule.
4. **9-tool signatures** — just names + one-liners so agents know what exists without reading `brain.py`.
5. **Hard constraints** — no medical diagnosis, English code / French product voice, no Swift, no git commits from Vibe, pytest class-style, no unit-test mocks except Mistral/Thryve clients.

### 2. Split the shared prompt into 4 per-agent prompts

Create `.vibe/prompts/vital-tests.md`, `vital-review.md`, `vital-audit.md`. Slim the existing `.vibe/prompts/vital.md` to be the docs/general fallback only.

All four share common foot-rules (linked from CONTEXT.md): no git commits, no Swift, English code, return a clear `done` / `blocked` / `wrong-agent` marker.

**`vital.md`** — docs + README + small general tasks. Scope: `docs/`, `README.md`, `.vibe/`. Refuses tasks that touch `backend/`.

**`vital-tests.md`** — write/update pytest tests only. Scope: `tests/` (write), `backend/*.py` (read). Must read `write-tests.md` skill first. Canonical reference: `tests/test_memory.py` (class `TestXxx`, method `test_scenario`, `monkeypatch` for file I/O, mock only Mistral/Thryve clients). **Hard rule**: after writing, run `uv run pytest <new_file> -v` and include output in the response. If tests fail, fix or return blocked — never hand back failing tests claiming success.

**`vital-review.md`** — read-only review against CONTEXT invariants. Scope: read everywhere, no writes, no bash. **Forced output format**: each finding is `file.py:line — <invariant violated> — <quote or short explanation>`. No "looks good" without citations. Uses the invariants column of the CONTEXT surface map as its checklist.

**`vital-audit.md`** — scoped single-file audit + refactor. Scope: exactly one file per task, declared in the task file — refuse if the task names more than one. Workflow: output a **diff plan** (bullet list of intended changes) at the top of the response, then the diff below, so Claude can review both in one shot. If audit surfaces problems outside the target file, report as findings — do not fix.

### 3. Two new skills targeting real pain

**`.vibe/skills/thryve-integration.md`** — how to add or modify a Thryve metric end-to-end:

1. Metric code — add to `thryve.py` metric map (check `docs/thryve-full-endpoints.md` / Thryve catalog).
2. Client method — async, uses `ThryveClient`, two-header auth, typed-dict return.
3. Brain tool (if user-facing) — add to 9-tool list in `brain.py`, update system prompt, update `CLAUDE.md` tool table + count per `.claude/rules/docs.md`.
4. Memory baseline — extend `memory.py` Baselines writer if a baseline is needed.
5. Consumer — wire into `coach.py` / `nudge.py` only if the task explicitly says so.
6. Tests — unit test for the client method (mock httpx), integration test for the tool call (mock Mistral).
7. Doc sync — grep for stale tool counts in `*.md` and fix.

Stop rule: if any step fails or is unclear, return blocked — don't improvise.

**`.vibe/skills/memory-invariants.md`** — rules for touching `memory.py` and `data/memory/*.md`:

- **Append-only**: never rewrite, never delete — new info = new line with ISO date prefix.
- **Four sections** — Baselines / Events / Protocols / Context — with one good and one bad example each.
- **Citation rule**: any insight produced by `coach.py` / `nudge.py` / `brain.py` must reference a baseline number OR a memory Event. No population averages, no vague "research shows".
- **Patient identity**: `patient.token` IS the Thryve `endUserId` IS the memory file key. One hex, no second lookup table.
- **File I/O**: only through `memory.py`. Other modules never touch `data/memory/*.md` directly.
- **Tests**: use `monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)` to isolate (copy pattern from existing `test_memory.py`).

Each skill ends with a "when to read this" line so agent prompts can reference them:

- `thryve-integration.md` — read before tasks touching `thryve.py`, brain tools, or metric wiring.
- `memory-invariants.md` — read before tasks touching `memory.py`, `coach.py`, `nudge.py`, or `data/memory/`.

### 4. Permission tightening + config

- `vital-audit.toml`: `[tools.bash].permission = "ask"` (was `always`).
- `vital-tests.toml`: keep `bash = always`, `write = always` (needs pytest + writes).
- `vital-review.toml`: keep read-only.
- `vital.toml`: keep `bash = ask`, `write = ask`.
- All four `.toml` files update `system_prompt_id` to match their file: `vital`, `vital-tests`, `vital-review`, `vital-audit`.
- `.vibe/config.toml`: add `prompt_paths = [".vibe/prompts"]` alongside `skill_paths` so per-agent prompts resolve from the project.

## Files touched

**Modified:**
- `.vibe/CONTEXT.md`
- `.vibe/config.toml`
- `.vibe/prompts/vital.md`
- `.vibe/agents/vital.toml`
- `.vibe/agents/vital-tests.toml`
- `.vibe/agents/vital-review.toml`
- `.vibe/agents/vital-audit.toml`

**Created:**
- `.vibe/prompts/vital-tests.md`
- `.vibe/prompts/vital-review.md`
- `.vibe/prompts/vital-audit.md`
- `.vibe/skills/thryve-integration.md`
- `.vibe/skills/memory-invariants.md`

## Acceptance criteria

- [ ] CONTEXT.md contains the surface map with invariants column.
- [ ] Four per-agent prompts exist, each with distinct scope + rules.
- [ ] `vital-review` prompt forces `file:line — invariant — quote` output format.
- [ ] `vital-tests` prompt includes the post-write `uv run pytest` rule.
- [ ] `vital-audit` prompt enforces single-file scope + diff-plan-first output.
- [ ] Two new skills created with V.I.T.A.L-specific content (not generic).
- [ ] `vital-audit.toml` has `bash = ask`.
- [ ] `.vibe/config.toml` has `prompt_paths = [".vibe/prompts"]`.
- [ ] All four agent `.toml` files reference their matching `system_prompt_id`.
- [ ] No backend code changes — `.vibe/` only.

## Out of scope

- New agents (no `vital-api-contract`, no `vital-memory-keeper`).
- Orchestration / task templates.
- Changes to `backend/` or `tests/`.
- Frontend or Swift.
