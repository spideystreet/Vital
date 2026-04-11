# Skill — Memory invariants

**When to read this:** before any task touching `backend/memory.py`, `backend/coach.py`, `backend/nudge.py`, or files in `data/memory/`.

## What this skill covers

The rules for per-user persistent memory. Memory is the spine of V.I.T.A.L — break it and the coach stops being "proactive" and starts sounding like a generic health app.

Memory files live at `data/memory/<endUserId>.md`. `<endUserId>` is a hex string — it is also `patient.token` in `PatientContext` and it is also the Thryve `endUserId`. **One hex string, no second lookup table.**

## The five invariants

### 1. Append-only

- **Never rewrite** a line in a memory file.
- **Never delete** an entry.
- **Never reorder** sections.
- New information = **new line** with an ISO date prefix.

Why: memory is an evidence trail. Deleting entries destroys the coach's ability to reference past events ("you said you were exhausted after that 2am call last week…").

### 2. Four sections, one schema

Every memory file has exactly these four headed sections, in this order:

- `## Baselines`
- `## Events`
- `## Protocols`
- `## Context`

Never add a fifth section. Never merge two. If a task proposes a new section → `STATUS: blocked — memory schema is fixed at 4 sections`.

### 3. Section contents (good vs bad examples)

**Baselines** — numeric personal norms, time-windowed.

- Good: `2026-04-05 resting_hr_14d_avg = 58 bpm`
- Bad: `resting HR is around 58` (no date, no window, no unit)

**Events** — time-stamped facts the coach should remember.

- Good: `2026-04-08 skipped sleep after 2am client call, reported exhaustion the next day`
- Bad: `user sometimes sleeps badly` (no date, vague)

**Protocols** — active adaptive plans with a start date and duration.

- Good: `2026-04-09 magnesium 300mg before bed for 7 days — to test effect on deep sleep`
- Bad: `try supplements` (no date, no duration, no purpose)

**Context** — stable user facts (job, goals, constraints).

- Good: `software engineer, optimizing for cognitive output, avoids caffeine after 14:00`
- Bad: `tech worker` (too vague to ground an insight)

### 4. Citation rule

Any insight produced by `coach.py`, `nudge.py`, or `brain.py` must reference **either**:

- a Baseline number from the user's memory ("14% below your 14-day baseline of 58 bpm"), **or**
- an Event from the user's memory ("last time this happened, you'd skipped sleep after a 2am call")

**Forbidden in insights:**

- Population averages ("most people sleep 7–9 hours")
- Vague science ("research shows that…")
- Unsourced claims ("this is bad for you")

If an insight can't be grounded in the user's own memory, it shouldn't be in the coach's output. Return `STATUS: blocked — insight cannot be grounded in memory` rather than inventing one.

### 5. File I/O goes through `memory.py`

- Other modules **never** touch `data/memory/*.md` directly.
- All reads go through `memory.read_memory(section)` or equivalent helpers.
- All writes go through `memory.append_memory(section, entry)` or equivalent.
- If you find another module reading/writing memory files directly, that's a **high-severity finding** (for `vital-review`) or a **refactor target** (for `vital-audit`).

## Testing memory code

Use the existing pattern from `tests/test_memory.py`:

```python
def test_something(self, monkeypatch, tmp_path):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    # ... exercise memory.py functions
```

- Never write to the real `data/memory/` during tests.
- Mock nothing inside `memory.py` — test the real logic against a temp directory.
- Assert on file contents, not just on function return values — the markdown shape IS the contract.

## Stop rules

- Task asks to delete or rewrite memory entries → `STATUS: blocked — memory is append-only`.
- Task asks to add a new section → `STATUS: blocked — memory schema is fixed at 4 sections`.
- Task asks to have another module read/write `data/memory/` directly → `STATUS: blocked — memory I/O only through memory.py`.
- Task asks for an insight that can't cite a baseline or event → `STATUS: blocked — insight cannot be grounded in user memory`.
