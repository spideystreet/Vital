# Proactive Coach Pivot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-04-11-proactive-coach-pivot-design.md`

**Goal:** Pivot V.I.T.A.L from a reactive weekly vocal checkup to a proactive life coach with three surfaces (morning brief, chat with your data, memory-driven notifications) sharing one persistent markdown memory store.

**Architecture:** All three surfaces read/write a shared markdown memory file per user (`data/memory/<user_id>.md`) with four sections: Baselines, Events, Protocols, Context. A new `memory.py` module owns the file; `coach.py` orchestrates the morning brief; `nudge.py` is rewired to read baselines from memory and compose personalized notifications via the LLM; `brain.py` gains two tools (`read_memory`, `append_memory`) so chat can reference the same spine. `berries.py` and the weekly vocal checkup ritual are cut.

**Tech Stack:** Python 3.12, FastAPI, Mistral Small 3 (LLM), Voxtral (STT/TTS), Nebius Llama Guard (safety), Thryve API (biometrics), pytest, `uv` for deps. No new third-party dependencies.

---

## Thryve integration notes (read before starting)

The Thryve API is documented in `docs/thryve-hackathon-guide.md` (provided by the hackathon organizer). Key facts that shape this plan:

1. **Use pre-made data profiles — do NOT create users.** The organizer provides a set of `endUserId`s with rich historical data already populated. The full table lives at `data/AIHackxThryve_Data_Profiles_Data-Profile.csv` (committed) and in `docs/thryve-hackathon-guide.md`. We pick one row and plug its `EndUserID` into the `PATIENTS` registry as the `token` field. No call to `/v5/accessToken`, no connection widget.

2. **Two auth headers on every call.** `backend/thryve.py` already implements this correctly — `Authorization: Basic base64(user:password)` and `AppAuthorization: Basic base64(appId:appSecret)`. No code change needed for the auth layer.

3. **Base URL must be the QA environment** — `https://api-qa.thryve.de`, not `https://api.thryve.de`. `backend/config.py` currently points at prod; Task 0 fixes this.

4. **Credentials come from the organizer** and live in `.env` (gitignored). Four env vars: `THRYVE_USER`, `THRYVE_PASSWORD`, `THRYVE_APP_ID`, `THRYVE_APP_SECRET`. If any is missing at startup, the Thryve client silently returns 401s — fail loudly at server startup instead of at the first API call.

5. **`patient.token` in `PatientContext` IS the Thryve `endUserId`.** The same hex string is used as the memory-file key (`data/memory/<token>.md`). This keeps the code simple — no second identifier to plumb through. The friendly id `"patient-1"` lives only in the frontend-facing REST URL (`/api/coach/brief` with `{"patient_id":"patient-1"}`), never in memory or Thryve.

6. **Default demo profile: Active Gym Guy (Whoop), `2bfaa7e6f9455ceafa0a59fd5b80496c`.** Whoop produces reliable HRV data, which is the center of the demo narrative. If the user picks a different profile at Task 0, update the registry and the seed file accordingly.

7. **Daily vs. epoch data.** We use `POST /v5/dailyDynamicValues` for all Thryve calls (the existing `ThryveClient` methods already wrap this). Epoch data is not needed for the pivot.

---

## File Structure

**New files:**

| Path | Responsibility |
|---|---|
| `backend/memory.py` | Pure markdown file I/O + baseline computation. No LLM calls. |
| `backend/coach.py` | Morning brief orchestrator: reads biometrics + memory → LLM → brief payload. |
| `tests/test_memory.py` | Unit tests for memory append/read/baseline. Pure file I/O, no network. |
| `tests/test_coach.py` | Integration test for morning brief with a mocked LLM and seeded memory file. |
| `data/memory/.gitkeep` | Ensures the memory directory exists in the repo; individual `.md` files are gitignored. |
| `data/memory/patient-1.md` | Seeded demo memory for the stage slot. Not gitignored — this IS the demo. |

**Modified files:**

| Path | Change |
|---|---|
| `backend/brain.py` | Remove `award_berries` tool + import; add `read_memory` and `append_memory` tools; drop `WEEKLY_CHECKUP_BLOCK` from `build_system_message`. |
| `backend/nudge.py` | Replace hardcoded thresholds with memory-based baselines; compose message via LLM; append fired events to memory. |
| `backend/health_server.py` | Remove `berries` import + endpoints; add `POST /api/coach/brief`, `POST /api/coach/reply`, `POST /dev/fire-notification`. |
| `tests/test_nudge.py` | Rewrite for memory-driven signatures. |
| `.gitignore` | Add `data/memory/*.md` (then un-ignore `data/memory/patient-1.md`). |
| `CLAUDE.md` | Tool count 8 → 9, drop berries scope/module, add memory+coach scopes/modules, replace weekly checkup with daily brief. |
| `docs/ARCHITECTURE.md` | Tool list, endpoints, module table, diagram. |
| `.vibe/CONTEXT.md` | Tool count, architecture summary. |
| `.claude/rules/backend.md` | Module table, patterns. |

**Deleted files:**

| Path | Reason |
|---|---|
| `backend/berries.py` | Cut per spec — not in demo story. |
| `tests/test_berries.py` | Tests a deleted module. |
| `wiki/concepts/weekly-vocal-checkup.md` | Surface is killed (leave it if the directory isn't currently committed; mark archived otherwise). Check before deleting. |

---

## Task 0: Thryve setup — QA base URL, credentials, and registry wiring

Before anything else depends on live Thryve data, point the client at the QA environment, fail loudly on missing credentials, and wire the chosen pre-made profile's `endUserId` into the patient registry.

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/health_server.py` (patient registry)
- Modify: `.env.example`

- [ ] **Step 0.1: Switch the Thryve base URL to QA**

In `backend/config.py`, change:

```python
THRYVE_BASE_URL = "https://api.thryve.de/v5"
```

to:

```python
THRYVE_BASE_URL = os.environ.get("THRYVE_BASE_URL", "https://api-qa.thryve.de/v5")
```

The env var override lets us swap to prod later without code changes. The default is the hackathon QA URL.

- [ ] **Step 0.2: Verify `backend/thryve.py` builds request paths correctly against the new base URL**

Use the Read tool on `backend/thryve.py` and check each `_post()` call. The endpoint strings must NOT duplicate `/v5`. For example:

- Correct: `self._post("/dailyDynamicValues", data)` (because `THRYVE_BASE_URL` ends in `/v5`)
- Wrong: `self._post("/v5/dailyDynamicValues", data)` (would produce `/v5/v5/...`)

If any path duplicates `/v5`, fix it. If all paths are relative like `/dailyDynamicValues`, nothing to change.

- [ ] **Step 0.3: Add a startup check for missing Thryve credentials**

In `backend/config.py`, append:

```python
def require_thryve_credentials() -> None:
    """Fail loudly at startup if Thryve credentials are missing.

    Called from the FastAPI lifespan so the server refuses to boot without them.
    """
    missing = [
        name
        for name, value in [
            ("THRYVE_USER", THRYVE_USER),
            ("THRYVE_PASSWORD", THRYVE_PASSWORD),
            ("THRYVE_APP_ID", THRYVE_APP_ID),
            ("THRYVE_APP_SECRET", THRYVE_APP_SECRET),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing Thryve env vars: {', '.join(missing)}. "
            "Copy .env.example to .env and fill them in. "
            "Credentials are provided by the hackathon organizer."
        )
```

- [ ] **Step 0.4: Call `require_thryve_credentials()` from the FastAPI lifespan**

Read `backend/health_server.py` and find the existing `@asynccontextmanager` / `lifespan` function (search for `lifespan` or `asynccontextmanager`). Add the credential check at the start of the lifespan:

```python
from backend.config import require_thryve_credentials

@asynccontextmanager
async def lifespan(app: FastAPI):
    require_thryve_credentials()
    # ... existing lifespan code ...
    yield
    # ... existing teardown ...
```

If there's no existing lifespan, create one and wire it into `FastAPI(lifespan=lifespan)` at app construction.

- [ ] **Step 0.5: Wire the pre-made profile into the patient registry**

In `backend/health_server.py`, replace the `PATIENTS` list with:

```python
# Pre-made Thryve data profile — see docs/thryve-hackathon-guide.md
# Default: "Active Gym Guy" (Whoop) — rich HRV data fits the demo narrative.
# Override via env var if a different profile is chosen at demo time.
_DEMO_THRYVE_END_USER_ID = os.environ.get(
    "VITAL_DEMO_THRYVE_TOKEN",
    "2bfaa7e6f9455ceafa0a59fd5b80496c",
)

PATIENTS = [
    {
        "id": "patient-1",
        "name": "Sophie Martin",  # Persona name — the Thryve profile is anonymous
        "age": 34,
        "token": _DEMO_THRYVE_END_USER_ID,
    },
]
```

We drop the second and third hardcoded patients — the demo runs on one profile. If a second profile is added later, extend this list.

Also add `import os` at the top of `health_server.py` if it isn't already imported.

- [ ] **Step 0.6: Update `.env.example`**

Read `.env.example` and ensure it contains (add any missing lines):

```bash
# Thryve — credentials provided by the hackathon organizer
THRYVE_USER=
THRYVE_PASSWORD=
THRYVE_APP_ID=
THRYVE_APP_SECRET=
# QA environment for the hackathon. Override with https://api.thryve.de/v5 for prod.
THRYVE_BASE_URL=https://api-qa.thryve.de/v5

# Optional: override the pre-made profile used for the demo
# Default is Active Gym Guy (Whoop) — see docs/thryve-hackathon-guide.md
VITAL_DEMO_THRYVE_TOKEN=2bfaa7e6f9455ceafa0a59fd5b80496c
```

- [ ] **Step 0.7: Smoke test the Thryve connection**

With real credentials filled into `.env`, run:

```bash
uv run python -c "
import asyncio
from backend.thryve import ThryveClient

async def main():
    client = ThryveClient()
    vitals = await client.get_vitals('2bfaa7e6f9455ceafa0a59fd5b80496c', days=14)
    print('keys:', list(vitals.keys())[:10])
    hrv = vitals.get('hrv', [])
    print('hrv points:', len(hrv))
    if hrv:
        nums = [v['value'] for v in hrv if isinstance(v.get('value'), (int, float))]
        if nums:
            print(f'hrv mean: {sum(nums)/len(nums):.1f}, last: {nums[-1]}')

asyncio.run(main())
"
```

Expected: prints at least some vitals keys (`hrv`, `resting_hr`, `sleep_quality` etc.) and shows >0 HRV data points for the profile. **Write down the HRV mean — you'll need it when seeding the memory file in Task 9 so the seeded baseline matches the real profile (±1σ).** If the call 401s, credentials are wrong; if it 404s, the base URL is wrong; if the profile has no HRV data, pick a different profile from the guide.

- [ ] **Step 0.8: Run existing tests to confirm nothing regressed**

Run: `uv run pytest -v`
Expected: all existing tests pass (the config change is non-breaking because `THRYVE_BASE_URL` still has a default).

- [ ] **Step 0.9: Lint**

Run: `uv run ruff check backend/`
Expected: clean.

- [ ] **Step 0.10: Commit**

```bash
git add backend/config.py backend/health_server.py .env.example
git commit -m "chore(config): switch Thryve to QA env and wire pre-made profile

Points backend/config THRYVE_BASE_URL at the hackathon QA environment
(https://api-qa.thryve.de/v5) via env var with a sane default.
Replaces the empty-token placeholder patients with the chosen pre-made
Thryve profile (default: Active Gym Guy / Whoop). Adds a startup
check that fails loudly when Thryve credentials are missing, so the
server never silently 401s against the Thryve API.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 1: Memory module — file I/O and section parsing

Build the spine first. Pure markdown file I/O, no LLM, no network. Everything else depends on this.

**Files:**
- Create: `backend/memory.py`
- Create: `tests/test_memory.py`
- Create: `data/memory/.gitkeep` (empty sentinel file)
- Modify: `.gitignore`

- [ ] **Step 1.1: Add `data/memory/` to gitignore with explicit un-ignore for the demo seed**

Modify `.gitignore` to append:

```gitignore
# Per-user memory files — gitignored by default, except the chosen demo profile.
# Task 9 adjusts the un-ignore line if a profile other than the default is chosen.
data/memory/*.md
!data/memory/2bfaa7e6f9455ceafa0a59fd5b80496c.md
```

Memory files are keyed by Thryve `endUserId` — see the Thryve integration notes above.

- [ ] **Step 1.2: Create the memory directory sentinel**

Create `data/memory/.gitkeep` as an empty file so the directory exists when cloned.

Run: `ls data/memory/.gitkeep`
Expected: file listed.

- [ ] **Step 1.3: Write the failing test for `memory_path()` and section constants**

Create `tests/test_memory.py`:

```python
"""Unit tests for backend.memory — pure file I/O, no network."""

from pathlib import Path

import pytest

from backend import memory


def test_memory_path_returns_expected_location(tmp_path, monkeypatch):
    """memory_path(user_id) returns data/memory/<user_id>.md under MEMORY_DIR."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    result = memory.memory_path("patient-1")
    assert result == tmp_path / "patient-1.md"


def test_section_constants_are_defined():
    """Four sections expected by the spec."""
    assert memory.SECTION_BASELINES == "Baselines"
    assert memory.SECTION_EVENTS == "Events"
    assert memory.SECTION_PROTOCOLS == "Protocols"
    assert memory.SECTION_CONTEXT == "Context"
    assert memory.ALL_SECTIONS == [
        "Baselines",
        "Events",
        "Protocols",
        "Context",
    ]
```

Run: `uv run pytest tests/test_memory.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.memory'`.

- [ ] **Step 1.4: Create `backend/memory.py` with constants and `memory_path()`**

```python
"""Persistent memory store for V.I.T.A.L — one markdown file per user.

Sections: Baselines, Events, Protocols, Context. All reads/writes happen
through this module; no other file touches the markdown directly.

Format:
    # <user_id>

    ## Baselines
    <entries...>

    ## Events
    <entries...>

    ## Protocols
    <entries...>

    ## Context
    <entries...>

Append-only. No locking — single-user hackathon scope.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path(__file__).resolve().parent.parent / "data" / "memory"

SECTION_BASELINES = "Baselines"
SECTION_EVENTS = "Events"
SECTION_PROTOCOLS = "Protocols"
SECTION_CONTEXT = "Context"

ALL_SECTIONS: list[str] = [
    SECTION_BASELINES,
    SECTION_EVENTS,
    SECTION_PROTOCOLS,
    SECTION_CONTEXT,
]


def memory_path(user_id: str) -> Path:
    """Return the path to the memory file for a given user."""
    return MEMORY_DIR / f"{user_id}.md"
```

- [ ] **Step 1.5: Run tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: 2 tests pass.

- [ ] **Step 1.6: Write the failing test for `ensure_memory_file()`**

Append to `tests/test_memory.py`:

```python
def test_ensure_memory_file_creates_empty_skeleton(tmp_path, monkeypatch):
    """If the file is missing, ensure_memory_file creates it with all sections."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    path = memory.ensure_memory_file("patient-1")
    assert path.exists()
    content = path.read_text()
    assert "# patient-1" in content
    for section in memory.ALL_SECTIONS:
        assert f"## {section}" in content


def test_ensure_memory_file_is_idempotent(tmp_path, monkeypatch):
    """Calling twice does not overwrite existing content."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    path = memory.ensure_memory_file("patient-1")
    path.write_text(path.read_text() + "\nTEST MARKER\n")
    memory.ensure_memory_file("patient-1")
    assert "TEST MARKER" in path.read_text()
```

Run: `uv run pytest tests/test_memory.py -v`
Expected: 2 new tests FAIL with `AttributeError: module 'backend.memory' has no attribute 'ensure_memory_file'`.

- [ ] **Step 1.7: Implement `ensure_memory_file()`**

Append to `backend/memory.py`:

```python
def ensure_memory_file(user_id: str) -> Path:
    """Create the memory file with an empty section skeleton if missing.

    Idempotent: existing files are not touched.
    """
    path = memory_path(user_id)
    if path.exists():
        return path

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"# {user_id}", ""]
    for section in ALL_SECTIONS:
        lines.append(f"## {section}")
        lines.append("")
    path.write_text("\n".join(lines))
    return path
```

- [ ] **Step 1.8: Run tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: 4 tests pass.

- [ ] **Step 1.9: Write the failing test for `read_section()`**

Append to `tests/test_memory.py`:

```python
def test_read_section_returns_section_body(tmp_path, monkeypatch):
    """read_section returns only that section's content, not the header."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    path = memory.ensure_memory_file("patient-1")
    path.write_text(
        "# patient-1\n\n"
        "## Baselines\n"
        "- hrv: mean=52.3 stddev=8.1\n\n"
        "## Events\n"
        "- 2026-04-10: HRV drop\n\n"
        "## Protocols\n\n"
        "## Context\n"
    )
    baselines = memory.read_section("patient-1", memory.SECTION_BASELINES)
    assert "hrv: mean=52.3 stddev=8.1" in baselines
    assert "HRV drop" not in baselines  # Events section must not leak


def test_read_section_returns_empty_for_missing_section(tmp_path, monkeypatch):
    """Unknown sections raise ValueError (typo protection)."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")
    with pytest.raises(ValueError, match="Unknown section"):
        memory.read_section("patient-1", "NotARealSection")
```

Run: `uv run pytest tests/test_memory.py -v`
Expected: 2 new tests FAIL.

- [ ] **Step 1.10: Implement `read_section()`**

Append to `backend/memory.py`:

```python
def read_section(user_id: str, section: str) -> str:
    """Return the body of a section (everything between ## <section> and the next ##)."""
    if section not in ALL_SECTIONS:
        raise ValueError(f"Unknown section: {section}. Valid: {ALL_SECTIONS}")

    path = ensure_memory_file(user_id)
    content = path.read_text()

    marker = f"## {section}"
    start = content.find(marker)
    if start == -1:
        return ""

    body_start = start + len(marker)
    # Find the next ## header (next section) or end of file
    next_header = content.find("\n## ", body_start)
    body_end = next_header if next_header != -1 else len(content)

    return content[body_start:body_end].strip()
```

- [ ] **Step 1.11: Run tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: 6 tests pass.

- [ ] **Step 1.12: Write the failing test for `append_entry()`**

Append to `tests/test_memory.py`:

```python
def test_append_entry_adds_line_under_section(tmp_path, monkeypatch):
    """append_entry adds a new bullet line under the named section."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")

    memory.append_entry("patient-1", memory.SECTION_EVENTS, "HRV drop to 38ms")

    events = memory.read_section("patient-1", memory.SECTION_EVENTS)
    assert "HRV drop to 38ms" in events
    assert events.count("HRV drop to 38ms") == 1


def test_append_entry_preserves_other_sections(tmp_path, monkeypatch):
    """Appending to one section must not corrupt others."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")
    memory.append_entry("patient-1", memory.SECTION_BASELINES, "hrv: mean=52")
    memory.append_entry("patient-1", memory.SECTION_EVENTS, "nudge fired")
    memory.append_entry("patient-1", memory.SECTION_BASELINES, "sleep: mean=7.2h")

    baselines = memory.read_section("patient-1", memory.SECTION_BASELINES)
    events = memory.read_section("patient-1", memory.SECTION_EVENTS)

    assert "hrv: mean=52" in baselines
    assert "sleep: mean=7.2h" in baselines
    assert "nudge fired" in events
    assert "nudge fired" not in baselines


def test_append_entry_rejects_unknown_section(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    with pytest.raises(ValueError, match="Unknown section"):
        memory.append_entry("patient-1", "Nope", "entry")
```

Run: `uv run pytest tests/test_memory.py -v`
Expected: 3 new tests FAIL.

- [ ] **Step 1.13: Implement `append_entry()`**

Append to `backend/memory.py`:

```python
def append_entry(user_id: str, section: str, entry: str) -> None:
    """Append a bullet line to a section. Entry is prefixed with '- '.

    Timestamps are the caller's responsibility (include them in `entry` if needed).
    """
    if section not in ALL_SECTIONS:
        raise ValueError(f"Unknown section: {section}. Valid: {ALL_SECTIONS}")

    path = ensure_memory_file(user_id)
    content = path.read_text()

    marker = f"## {section}"
    start = content.find(marker)
    if start == -1:
        raise RuntimeError(
            f"Memory file for {user_id} is missing section {section}. "
            "File may be corrupted — delete and let ensure_memory_file recreate it."
        )

    body_start = start + len(marker)
    next_header = content.find("\n## ", body_start)

    new_line = f"- {entry}\n"

    if next_header == -1:
        # Section is the last one: append at end of file
        new_content = content.rstrip() + "\n" + new_line
    else:
        # Insert just before the next section header
        insert_at = next_header + 1  # after the newline before "## "
        new_content = content[:insert_at] + new_line + content[insert_at:]

    path.write_text(new_content)
```

- [ ] **Step 1.14: Run tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: 9 tests pass.

- [ ] **Step 1.15: Write the failing test for `read_all()`**

Append to `tests/test_memory.py`:

```python
def test_read_all_returns_full_markdown(tmp_path, monkeypatch):
    """read_all returns the entire memory file as a string for LLM injection."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")
    memory.append_entry("patient-1", memory.SECTION_BASELINES, "hrv: mean=52")
    memory.append_entry("patient-1", memory.SECTION_CONTEXT, "training for marathon")

    blob = memory.read_all("patient-1")
    assert "# patient-1" in blob
    assert "## Baselines" in blob
    assert "hrv: mean=52" in blob
    assert "training for marathon" in blob
```

Run: `uv run pytest tests/test_memory.py -v`
Expected: 1 new test FAIL with `AttributeError`.

- [ ] **Step 1.16: Implement `read_all()`**

Append to `backend/memory.py`:

```python
def read_all(user_id: str) -> str:
    """Return the full memory file as a string — suitable for LLM context injection."""
    return ensure_memory_file(user_id).read_text()
```

- [ ] **Step 1.17: Run tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: 10 tests pass.

- [ ] **Step 1.18: Commit**

```bash
git add backend/memory.py tests/test_memory.py data/memory/.gitkeep .gitignore
git commit -m "feat(memory): add persistent markdown memory module

Pure file I/O spine for the proactive coach pivot. Stores four sections
per user (Baselines, Events, Protocols, Context) and exposes append_entry,
read_section, and read_all for the coach, nudge detector, and chat tools
to share.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Memory module — baseline computation

Add the one non-I/O function memory needs: computing and storing rolling baselines from Thryve data. This is called by the morning brief and the notification tick.

**Files:**
- Modify: `backend/memory.py`
- Modify: `tests/test_memory.py`

- [ ] **Step 2.1: Write the failing test for `format_baseline()`**

`format_baseline` is a pure helper that formats a baseline entry — test it in isolation before wiring it to live data.

Append to `tests/test_memory.py`:

```python
def test_format_baseline_produces_stable_string():
    """format_baseline(metric, values) returns a deterministic one-liner."""
    line = memory.format_baseline("hrv", [50, 52, 48, 55, 51, 53, 49], days=7)
    # Mean = 51.1, stddev ~ 2.3
    assert line.startswith("hrv: ")
    assert "mean=51.1" in line
    assert "n=7" in line
    assert "window=7d" in line


def test_format_baseline_rejects_empty_values():
    with pytest.raises(ValueError, match="no values"):
        memory.format_baseline("hrv", [], days=7)
```

Run: `uv run pytest tests/test_memory.py -v`
Expected: 2 new tests FAIL.

- [ ] **Step 2.2: Implement `format_baseline()`**

Append to `backend/memory.py`:

```python
from statistics import mean, stdev


def format_baseline(metric: str, values: list[float], days: int) -> str:
    """Format a baseline one-liner for the Baselines section.

    Example: "hrv: mean=51.1 stddev=2.3 n=7 window=7d"
    """
    if not values:
        raise ValueError(f"Cannot compute baseline for {metric}: no values provided")

    m = round(mean(values), 1)
    sd = round(stdev(values), 1) if len(values) >= 2 else 0.0
    return f"{metric}: mean={m} stddev={sd} n={len(values)} window={days}d"
```

- [ ] **Step 2.3: Run tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: 12 tests pass.

- [ ] **Step 2.4: Write the failing test for `upsert_baseline()`**

`upsert_baseline` replaces any existing baseline entry for the same metric rather than appending a duplicate. Baselines must not grow unbounded.

Append to `tests/test_memory.py`:

```python
def test_upsert_baseline_replaces_existing_entry(tmp_path, monkeypatch):
    """Writing a baseline for the same metric twice replaces the old entry."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")

    memory.upsert_baseline("patient-1", "hrv", [50, 52, 48], days=3)
    memory.upsert_baseline("patient-1", "hrv", [60, 62, 58], days=3)

    baselines = memory.read_section("patient-1", memory.SECTION_BASELINES)
    # Old values gone, new values present
    assert "mean=60" in baselines
    assert "mean=50" not in baselines
    # Only one hrv line exists
    assert baselines.count("hrv:") == 1


def test_upsert_baseline_preserves_other_metrics(tmp_path, monkeypatch):
    """Upserting hrv does not touch resting_hr."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")
    memory.upsert_baseline("patient-1", "hrv", [50, 52, 48], days=3)
    memory.upsert_baseline("patient-1", "resting_hr", [62, 64, 63], days=3)
    memory.upsert_baseline("patient-1", "hrv", [70, 72, 68], days=3)

    baselines = memory.read_section("patient-1", memory.SECTION_BASELINES)
    assert "hrv:" in baselines
    assert "resting_hr:" in baselines
    assert "mean=70" in baselines  # new hrv
    assert "mean=63" in baselines  # untouched resting_hr
```

Run: `uv run pytest tests/test_memory.py -v`
Expected: 2 new tests FAIL.

- [ ] **Step 2.5: Implement `upsert_baseline()`**

Append to `backend/memory.py`:

```python
def upsert_baseline(
    user_id: str,
    metric: str,
    values: list[float],
    days: int,
) -> None:
    """Compute a baseline line for `metric` and replace any existing entry for it.

    Baselines are keyed by metric name (everything before the first ':'). A new
    call to upsert_baseline for the same metric overwrites the old line in place.
    """
    new_line = format_baseline(metric, values, days)

    path = ensure_memory_file(user_id)
    content = path.read_text()

    marker = f"## {SECTION_BASELINES}"
    start = content.find(marker)
    if start == -1:
        raise RuntimeError(
            f"Memory file for {user_id} is missing section {SECTION_BASELINES}."
        )

    body_start = start + len(marker)
    next_header = content.find("\n## ", body_start)
    body_end = next_header if next_header != -1 else len(content)

    body = content[body_start:body_end]
    lines = body.split("\n")

    prefix = f"- {metric}:"
    kept = [line for line in lines if not line.startswith(prefix)]
    kept.append(f"- {new_line}")

    # Rebuild body keeping blank-line padding around the section.
    new_body = "\n" + "\n".join(line for line in kept if line.strip()) + "\n\n"

    path.write_text(content[:body_start] + new_body + content[body_end:])
```

- [ ] **Step 2.6: Run tests to verify they pass**

Run: `uv run pytest tests/test_memory.py -v`
Expected: 14 tests pass.

- [ ] **Step 2.7: Commit**

```bash
git add backend/memory.py tests/test_memory.py
git commit -m "feat(memory): add baseline formatting and upsert

format_baseline computes mean/stddev/n/window as a stable one-liner.
upsert_baseline replaces any existing entry for the same metric so
baselines cannot accumulate duplicates across morning briefs.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Remove berries from brain.py and health_server.py

Cut `backend/berries.py` per spec. Removing it before adding memory tools keeps `brain.py`'s tool count honest at every intermediate commit.

**Files:**
- Delete: `backend/berries.py`
- Delete: `tests/test_berries.py`
- Modify: `backend/brain.py` (remove `award_berries` tool and `_tool_award_berries`)
- Modify: `backend/health_server.py` (remove berries import)

- [ ] **Step 3.1: Verify no code outside the targets references `berries`**

Run: use the Grep tool with pattern `berries` over `backend/` and `tests/` to list every match.
Expected: matches only in `backend/berries.py`, `backend/brain.py`, `backend/health_server.py`, `tests/test_berries.py`. If any other file matches, STOP and report — do not delete blindly.

- [ ] **Step 3.2: Delete `backend/berries.py` and its test**

```bash
rm backend/berries.py tests/test_berries.py
```

- [ ] **Step 3.3: Remove `award_berries` from `brain.py`**

Modify `backend/brain.py`:

1. Remove the import line:
   ```python
   from backend.berries import award, total
   ```
2. In the `TOOLS` list (lines ~271–292), delete the entire `award_berries` function entry.
3. In `TOOL_EMOTIONS` (lines ~333–342), delete the `"award_berries": "happy",` line.
4. In `execute_tool()`, delete the branch:
   ```python
   elif name == "award_berries":
       result = _tool_award_berries(args["action"])
       emotion = "happy"
   ```
5. Delete the `_tool_award_berries()` function definition (lines ~677–689).
6. In the system prompt, change `"8 outils"` → `"9 outils"` (line ~98). We'll end at 9 after adding the two memory tools in Task 4.
7. Update the module docstring at the top of the file from `"8-tool function calling"` to `"9-tool function calling"`.

- [ ] **Step 3.4: Remove berries import and usage from `health_server.py`**

Modify `backend/health_server.py`:

1. Delete the import line:
   ```python
   from backend.berries import award, init_berries, total
   ```
2. Remove any call sites for `init_berries`, `award`, or `total`. Use Grep inside the file first to locate them; for each hit, delete the call and the surrounding endpoint/handler if its only purpose was berries.

- [ ] **Step 3.5: Run the full test suite to confirm nothing broke**

Run: `uv run pytest -v`
Expected: all remaining tests pass. Any failure should be either (a) a test that referenced berries directly (delete it) or (b) a genuine regression — investigate.

- [ ] **Step 3.6: Lint check**

Run: `uv run ruff check backend/`
Expected: clean. Fix any unused-import warnings from the deletions.

- [ ] **Step 3.7: Commit**

```bash
git add -A
git commit -m "refactor(brain): cut berries rewards loop for proactive coach pivot

Removes backend/berries.py, tests/test_berries.py, the award_berries tool
from brain.py, and the berries wiring in health_server.py. The rewards
loop is orthogonal to the coaching thesis and costs demo time without
adding to the memory-driven narrative.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Add `read_memory` and `append_memory` tools to brain.py

This lets the chat surface (Surface 2) reference the same memory the morning brief writes, so the agent can say *"why did you nudge me yesterday?"* and actually answer from memory.

**Files:**
- Modify: `backend/brain.py`

- [ ] **Step 4.1: Add the `read_memory` tool definition**

In `backend/brain.py`, inside the `TOOLS` list (after `book_consultation`, before the closing `]`), append:

```python
{
    "type": "function",
    "function": {
        "name": "read_memory",
        "description": (
            "Read a section of the user's persistent memory. "
            "Sections: 'Baselines' (rolling per-metric stats), 'Events' "
            "(past notifications and briefs), 'Protocols' (proposed protocols "
            "and user acceptance), 'Context' (user-stated goals and context). "
            "Use when the user asks about their history, why you nudged them, "
            "or what you've suggested before."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": ["Baselines", "Events", "Protocols", "Context"],
                    "description": "Which memory section to read",
                },
            },
            "required": ["section"],
        },
    },
},
{
    "type": "function",
    "function": {
        "name": "append_memory",
        "description": (
            "Store new user context discovered during conversation. "
            "Use when the user shares a goal, a life event, or a subjective "
            "feeling you should remember for future briefs (e.g. 'I'm starting "
            "a new job next week', 'I always feel wired after meetings'). "
            "Only use the 'Context' section for conversational learning."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "entry": {
                    "type": "string",
                    "description": "The context to remember, one short sentence",
                },
            },
            "required": ["entry"],
        },
    },
},
```

- [ ] **Step 4.2: Add the new tools to `TOOL_EMOTIONS`**

In `TOOL_EMOTIONS`, add:

```python
"read_memory": "thinking",
"append_memory": "curious",
```

- [ ] **Step 4.3: Add the import for memory at the top of `brain.py`**

After the existing backend imports, add:

```python
from backend import memory
```

- [ ] **Step 4.4: Add `_tool_read_memory` and `_tool_append_memory`**

In `backend/brain.py`, after `_tool_book_consultation`, append:

```python
def _tool_read_memory(patient: PatientContext, section: str) -> dict:
    """Read a section of the user's persistent memory file."""
    try:
        body = memory.read_section(patient.token, section)
    except ValueError as e:
        return {"error": str(e)}
    return {
        "section": section,
        "content": body if body else "(empty)",
    }


def _tool_append_memory(patient: PatientContext, entry: str) -> dict:
    """Append a user-context entry to persistent memory.

    Prefixes the entry with today's date for later chronological ordering.
    """
    from datetime import date

    dated = f"{date.today().isoformat()}: {entry}"
    try:
        memory.append_entry(patient.token, memory.SECTION_CONTEXT, dated)
    except ValueError as e:
        return {"error": str(e)}
    return {"stored": dated}
```

Note: we use `patient.token` as the `user_id` for the memory file because it uniquely identifies the user end-to-end. The demo seed file uses `patient-1` as its name — adjust the seed step in Task 8 accordingly.

- [ ] **Step 4.5: Dispatch the new tools from `execute_tool()`**

In `execute_tool()` in `backend/brain.py`, add two new branches before the `else` clause:

```python
elif name == "read_memory":
    result = _tool_read_memory(patient, args["section"])

elif name == "append_memory":
    result = _tool_append_memory(patient, args["entry"])
```

- [ ] **Step 4.6: Update the system prompt to mention memory**

In `SYSTEM_TEMPLATE`, replace the `OUTILS:` block with:

```
OUTILS:
- Tu as 9 outils pour consulter les donnees de sante, calculer le burnout, \
agir (consultation), et lire/ecrire la memoire persistante de l'utilisateur. \
Utilise-les quand la question le necessite.
- MEMOIRE: tu disposes d'une memoire persistante (read_memory, append_memory). \
Quand l'utilisateur demande "pourquoi tu m'as alerte hier ?" ou "qu'est-ce que \
tu avais propose la derniere fois ?", lis la section Events ou Protocols. \
Quand l'utilisateur partage un objectif ou un contexte de vie important, \
sauvegarde-le avec append_memory pour les prochains matins.
- Pour une question generale, les donnees deja fournies ci-dessous suffisent.
```

- [ ] **Step 4.7: Drop the weekly checkup block from `build_system_message`**

The weekly vocal checkup ritual is cut. Remove its plumbing so no caller can accidentally trigger it.

In `backend/brain.py`:

1. Delete the `WEEKLY_CHECKUP_BLOCK` constant (lines ~116–130) and `NORMAL_BLOCK` (line ~132).
2. Remove `{checkup_block}` from `SYSTEM_TEMPLATE`.
3. Change `build_system_message` signature from `(..., weekly_checkup: bool = False)` to `(...)` — drop the parameter.
4. In the `.format()` call, drop `checkup_block=checkup_block`.

- [ ] **Step 4.8: Update callers of `build_system_message`**

Run: use Grep for `build_system_message` across `backend/` and `tests/`.
Expected: one or more matches in `backend/health_server.py`, possibly `backend/voice_ws.py`.

For each call site that passes `weekly_checkup=...`, remove that kwarg. Do NOT leave dead `if` branches for weekly checkup mode — delete them outright.

- [ ] **Step 4.9: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests pass. Import errors mean a reference to the removed weekly checkup or berries was missed — grep for it and fix.

- [ ] **Step 4.10: Lint**

Run: `uv run ruff check backend/`
Expected: clean.

- [ ] **Step 4.11: Commit**

```bash
git add -A
git commit -m "feat(brain): add read_memory and append_memory tools

Brings the tool count to 9 (was 8, minus berries, plus the two memory
tools). The chat surface can now reference past events and protocols
the morning brief wrote, and store new user context discovered mid-
conversation. Also drops the weekly vocal checkup block and parameter
from build_system_message since that surface is cut.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 5: `coach.py` — morning brief orchestrator

Builds the morning brief: read biometrics + memory → LLM → payload with diagnosis, memory callback, protocol, one question. Writes the brief back to memory as an Event and the proposed protocol as a Protocol entry.

**Files:**
- Create: `backend/coach.py`
- Create: `tests/test_coach.py`

- [ ] **Step 5.1: Write the failing test for `BriefPayload` dataclass**

Create `tests/test_coach.py`:

```python
"""Tests for the morning brief orchestrator."""

from unittest.mock import AsyncMock, patch

import pytest

from backend import coach, memory
from backend.brain import PatientContext


def test_brief_payload_has_expected_fields():
    """BriefPayload carries diagnosis, memory_callback, protocol, question, raw_text."""
    p = coach.BriefPayload(
        diagnosis="HRV dropped 14%",
        memory_callback="Same as 3 weeks ago",
        protocol="Skip HIIT, zone-2 walk",
        question="How did you sleep?",
        raw_text="full spoken text",
    )
    d = p.to_dict()
    assert d["diagnosis"] == "HRV dropped 14%"
    assert d["memory_callback"] == "Same as 3 weeks ago"
    assert d["protocol"] == "Skip HIIT, zone-2 walk"
    assert d["question"] == "How did you sleep?"
    assert d["raw_text"] == "full spoken text"
```

Run: `uv run pytest tests/test_coach.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'backend.coach'`.

- [ ] **Step 5.2: Create `backend/coach.py` with the `BriefPayload` dataclass**

```python
"""Morning brief orchestrator for V.I.T.A.L.

Reads recent biometrics from Thryve and the user's persistent memory,
asks the LLM to compose a structured brief (diagnosis + memory callback +
adaptive protocol + one question), and writes the brief back to memory.

This is the Surface 1 entry point — called by the daily cron or the
"Start my day" button in the web UI.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date

from mistralai.client import Mistral

from backend import memory
from backend.brain import PatientContext, SessionData, prefetch_session
from backend.config import LLM_MODEL

log = logging.getLogger(__name__)


@dataclass
class BriefPayload:
    """Structured morning brief returned to the frontend.

    Fields are displayed as separate cards in the UI; `raw_text` is what
    Voxtral TTS speaks.
    """

    diagnosis: str
    memory_callback: str
    protocol: str
    question: str
    raw_text: str

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 5.3: Run tests to verify they pass**

Run: `uv run pytest tests/test_coach.py -v`
Expected: 1 test passes.

- [ ] **Step 5.4: Write the failing test for `_build_brief_prompt()`**

`_build_brief_prompt` is the pure-function core of the brief: given a session + memory blob, return the messages list sent to the LLM. Testing it in isolation means we don't need a live LLM in the test.

Append to `tests/test_coach.py`:

```python
def test_build_brief_prompt_includes_memory_and_biometrics(tmp_path, monkeypatch):
    """The prompt must contain the user's memory blob and recent biometric summary."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.append_entry(
        "test-token",
        memory.SECTION_EVENTS,
        "2026-03-21: HRV drop to 38ms, magnesium + zone-2 walk worked in 4d",
    )
    memory.upsert_baseline("test-token", "hrv", [48, 50, 52, 49, 51, 47, 50], days=7)

    patient = PatientContext(token="test-token", name="Sophie", age=34)
    session = SessionData()
    # Minimal vitals shape matching Thryve output used in brain.py
    session.vitals = {
        "hrv": [{"date": "2026-04-10", "value": 38}],
        "sleep_quality": [{"date": "2026-04-10", "value": 58}],
    }

    messages = coach._build_brief_prompt(patient, session)

    # Two messages: system + user trigger
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    system_content = messages[0]["content"]
    # Memory blob is injected verbatim
    assert "HRV drop to 38ms" in system_content
    assert "hrv: mean=49.6" in system_content or "hrv: mean=49.5" in system_content
    # Biometric snapshot is injected
    assert "38" in system_content  # latest HRV
```

Run: `uv run pytest tests/test_coach.py -v`
Expected: 1 new test FAIL.

- [ ] **Step 5.5: Implement `_build_brief_prompt()`**

Append to `backend/coach.py`:

```python
_BRIEF_SYSTEM_TEMPLATE = """\
Tu es V.I.T.A.L, un coach de vie proactif base sur les donnees sante de l'utilisateur.
Tu produis le BRIEF DU MATIN : un diagnostic court, un rappel de la memoire personnelle \
de l'utilisateur, un protocole adaptatif pour aujourd'hui, et UNE question pour cloturer.

PROFIL :
- Nom : {name}
- Age : {age}

MEMOIRE PERSISTANTE (lis tout, cite ce qui est pertinent) :
{memory_blob}

BIOMETRIQUES (dernier releve) :
{biometrics}

FORMAT DE SORTIE (JSON strict, pas de markdown) :
{{
  "diagnosis": "une phrase, 1-2 chiffres cles",
  "memory_callback": "une phrase qui reference un evenement ou un protocole passe \
de la section Events ou Protocols. Si la memoire ne contient rien de pertinent, \
ecris 'Premier brief — je commence a apprendre ton rythme.'",
  "protocol": "UNE action concrete pour aujourd'hui, adaptee a l'etat actuel",
  "question": "UNE question fermee pour capter l'intention de l'utilisateur",
  "raw_text": "le brief entier a lire a voix haute (3-4 phrases), sans markdown"
}}

REGLES STRICTES :
- JAMAIS de diagnostic medical. Si le signal est grave, recommande un professionnel.
- Le callback memoire doit citer un element REEL de la memoire si elle en contient un.
- raw_text doit etre conversationnel, pas une liste a puces.
- Reponds uniquement le JSON, rien d'autre.
"""


def _format_biometrics(session: SessionData) -> str:
    """Summarize cached vitals as a compact string for the prompt."""
    if not session.vitals:
        return "(pas de donnees biometriques disponibles)"

    lines: list[str] = []
    for metric, values in session.vitals.items():
        nums = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
        if not nums:
            continue
        lines.append(f"- {metric}: dernier={nums[-1]}, moy7j={round(sum(nums)/len(nums), 1)}")
    return "\n".join(lines) if lines else "(pas de donnees biometriques disponibles)"


def _build_brief_prompt(patient: PatientContext, session: SessionData) -> list[dict]:
    """Build the system + user message pair sent to the LLM for the morning brief."""
    memory_blob = memory.read_all(patient.token)
    biometrics = _format_biometrics(session)

    system_content = _BRIEF_SYSTEM_TEMPLATE.format(
        name=patient.name,
        age=patient.age or "?",
        memory_blob=memory_blob,
        biometrics=biometrics,
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "Genere le brief du matin."},
    ]
```

- [ ] **Step 5.6: Run tests to verify they pass**

Run: `uv run pytest tests/test_coach.py -v`
Expected: 2 tests pass.

- [ ] **Step 5.7: Write the failing test for `generate_morning_brief()` with a mocked LLM**

Append to `tests/test_coach.py`:

```python
@pytest.mark.asyncio
async def test_generate_morning_brief_writes_to_memory(tmp_path, monkeypatch):
    """The brief is parsed into a BriefPayload and written to Events + Protocols."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.upsert_baseline("test-token", "hrv", [48, 50, 52, 49, 51, 47, 50], days=7)

    patient = PatientContext(token="test-token", name="Sophie", age=34)

    # Mock the LLM response
    fake_llm_json = json.dumps({
        "diagnosis": "HRV a 38ms, 14% sous ta moyenne 7 jours.",
        "memory_callback": "Meme pattern que le 21 mars, le protocole magnesium + marche zone 2 avait marche en 4 jours.",
        "protocol": "Zero HIIT aujourd'hui. Marche 40min a allure souple + magnesium ce soir.",
        "question": "Tu peux tenir ce protocole aujourd'hui ?",
        "raw_text": "Bonjour Sophie, ton HRV est a 38 ms ce matin, 14 % sous ta moyenne. Meme pattern qu'il y a trois semaines — le magnesium et la marche zone 2 avaient marche en 4 jours. Zero HIIT aujourd'hui, marche 40 minutes souple et magnesium ce soir. Tu peux tenir ce protocole ?",
    })

    class _FakeChoice:
        class message:  # noqa: N801
            content = fake_llm_json
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]

    mock_client = AsyncMock(spec=Mistral)
    mock_client.chat.complete.return_value = _FakeResponse()

    # Patch prefetch_session to seed vitals without hitting Thryve
    async def _fake_prefetch(p, s):
        s.vitals = {"hrv": [{"date": "2026-04-11", "value": 38}]}

    with patch("backend.coach.prefetch_session", new=_fake_prefetch):
        payload = await coach.generate_morning_brief(mock_client, patient)

    assert isinstance(payload, coach.BriefPayload)
    assert payload.diagnosis == "HRV a 38ms, 14% sous ta moyenne 7 jours."
    assert "21 mars" in payload.memory_callback

    # Memory was updated
    events = memory.read_section("test-token", memory.SECTION_EVENTS)
    protocols = memory.read_section("test-token", memory.SECTION_PROTOCOLS)
    assert "HRV a 38ms" in events
    assert "zone 2" in protocols.lower() or "HIIT" in protocols
```

Run: `uv run pytest tests/test_coach.py -v`
Expected: 1 new test FAIL.

- [ ] **Step 5.8: Implement `generate_morning_brief()`**

Append to `backend/coach.py`:

```python
async def generate_morning_brief(
    client: Mistral,
    patient: PatientContext,
) -> BriefPayload:
    """Produce the morning brief and write it back to memory.

    Steps:
    1. Prefetch vitals + burnout into a fresh SessionData
    2. Build the structured brief prompt (includes memory + biometrics)
    3. Call the LLM, expecting a JSON object
    4. Parse into BriefPayload
    5. Append the brief as an Event and the protocol as a Protocol entry
    6. Return the payload
    """
    memory.ensure_memory_file(patient.token)

    session = SessionData()
    try:
        await prefetch_session(patient, session)
    except Exception:
        log.exception("prefetch_session failed during morning brief")
        # Continue: memory + whatever we have is still enough for a partial brief

    messages = _build_brief_prompt(patient, session)

    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
    except Exception:
        log.exception("LLM call failed during morning brief")
        return BriefPayload(
            diagnosis="Je n'arrive pas a lire tes donnees ce matin.",
            memory_callback="",
            protocol="Prends 5 minutes pour te poser et respirer.",
            question="Comment te sens-tu ce matin ?",
            raw_text=(
                "Bonjour, je n'arrive pas a me connecter a tes donnees ce matin. "
                "Prends 5 minutes pour te poser et respirer. Comment te sens-tu ?"
            ),
        )

    raw_content = response.choices[0].message.content
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        log.error("Brief JSON parse failed, raw=%s", raw_content)
        return BriefPayload(
            diagnosis="Brief genere mais illisible.",
            memory_callback="",
            protocol="Relance ton brief dans un instant.",
            question="",
            raw_text=raw_content[:400],
        )

    payload = BriefPayload(
        diagnosis=parsed.get("diagnosis", ""),
        memory_callback=parsed.get("memory_callback", ""),
        protocol=parsed.get("protocol", ""),
        question=parsed.get("question", ""),
        raw_text=parsed.get("raw_text", ""),
    )

    today = date.today().isoformat()
    memory.append_entry(
        patient.token,
        memory.SECTION_EVENTS,
        f"{today}: morning_brief — {payload.diagnosis}",
    )
    if payload.protocol:
        memory.append_entry(
            patient.token,
            memory.SECTION_PROTOCOLS,
            f"{today}: proposed — {payload.protocol} — status: pending",
        )

    return payload
```

- [ ] **Step 5.9: Install pytest-asyncio if not already in dev deps**

Run: `uv run python -c "import pytest_asyncio"`
Expected: either imports silently or raises `ModuleNotFoundError`.

If it raises, add pytest-asyncio to the dev dependencies:

```bash
uv add --dev pytest-asyncio
```

Then ensure `pyproject.toml` has `asyncio_mode = "auto"` or similar under `[tool.pytest.ini_options]`. If not present, append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 5.10: Run tests to verify they pass**

Run: `uv run pytest tests/test_coach.py -v`
Expected: 3 tests pass.

- [ ] **Step 5.11: Write the failing test for `record_user_reply()`**

Append to `tests/test_coach.py`:

```python
@pytest.mark.asyncio
async def test_record_user_reply_appends_context_and_updates_protocol(tmp_path, monkeypatch):
    """User reply to the brief is stored as Context and updates the pending protocol."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.append_entry(
        "test-token",
        memory.SECTION_PROTOCOLS,
        "2026-04-11: proposed — Zone 2 walk — status: pending",
    )

    patient = PatientContext(token="test-token", name="Sophie", age=34)
    await coach.record_user_reply(patient, "ok je vais le faire")

    context = memory.read_section("test-token", memory.SECTION_CONTEXT)
    assert "ok je vais le faire" in context
    # Protocol status was updated based on affirmative reply
    protocols = memory.read_section("test-token", memory.SECTION_PROTOCOLS)
    assert "status: accepted" in protocols
```

Run: `uv run pytest tests/test_coach.py -v`
Expected: 1 new test FAIL.

- [ ] **Step 5.12: Implement `record_user_reply()`**

Append to `backend/coach.py`:

```python
_AFFIRMATIVE_MARKERS = ["ok", "oui", "yes", "d'accord", "carrement", "ça marche"]
_NEGATIVE_MARKERS = ["non", "no", "pas aujourd'hui", "trop", "impossible"]


def _classify_reply(reply: str) -> str:
    """Rough classification of the user's reply to the brief.

    Returns 'accepted', 'rejected', or 'unclear'. The LLM could do this more
    richly but for Surface 1 the boolean outcome is all we write back.
    """
    r = reply.lower()
    if any(m in r for m in _AFFIRMATIVE_MARKERS):
        return "accepted"
    if any(m in r for m in _NEGATIVE_MARKERS):
        return "rejected"
    return "unclear"


async def record_user_reply(patient: PatientContext, reply: str) -> None:
    """Append the user's morning-brief reply to Context and update the pending protocol."""
    today = date.today().isoformat()

    memory.append_entry(
        patient.token,
        memory.SECTION_CONTEXT,
        f"{today}: reply — {reply.strip()}",
    )

    # Update the most recent pending protocol in-place
    outcome = _classify_reply(reply)
    if outcome == "unclear":
        return

    path = memory.ensure_memory_file(patient.token)
    content = path.read_text()

    marker = f"## {memory.SECTION_PROTOCOLS}"
    start = content.find(marker)
    if start == -1:
        return
    body_start = start + len(marker)
    next_header = content.find("\n## ", body_start)
    body_end = next_header if next_header != -1 else len(content)

    body = content[body_start:body_end]
    # Replace the last "status: pending" with "status: <outcome>"
    replaced_once = body.rsplit("status: pending", 1)
    if len(replaced_once) == 2:
        new_body = f"status: {outcome}".join(replaced_once)
        path.write_text(content[:body_start] + new_body + content[body_end:])
```

- [ ] **Step 5.13: Run tests to verify they pass**

Run: `uv run pytest tests/test_coach.py -v`
Expected: 4 tests pass.

- [ ] **Step 5.14: Commit**

```bash
git add backend/coach.py tests/test_coach.py pyproject.toml uv.lock
git commit -m "feat(coach): add morning brief orchestrator

coach.generate_morning_brief reads vitals + memory, asks the LLM for a
JSON-structured brief (diagnosis, memory_callback, protocol, question,
raw_text), writes the brief to Events and the protocol to Protocols,
and returns the payload. coach.record_user_reply stores the user's
response to Context and flips the pending protocol to accepted/rejected.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Morning brief endpoints on `health_server.py`

Expose the coach to the frontend: one endpoint to generate the brief (with SSE streaming) and one to record the user's reply.

**Files:**
- Modify: `backend/health_server.py`

- [ ] **Step 6.1: Read the existing checkup SSE endpoint as a reference**

Use the Read tool on `backend/health_server.py` and locate the current `/api/checkup/respond` handler — the new brief endpoint reuses the same SSE event shape (`event: text\ndata: <json>\n\n`).

- [ ] **Step 6.2: Add `POST /api/coach/brief` returning SSE**

At the bottom of the endpoint section in `backend/health_server.py`, add:

```python
class BriefRequest(BaseModel):
    patient_id: str


@app.post("/api/coach/brief")
async def post_coach_brief(req: BriefRequest) -> StreamingResponse:
    """Generate the morning brief and stream it via SSE.

    Streams three events:
    - event: brief  — full BriefPayload as JSON (UI renders the card)
    - event: audio  — base64 audio chunks from Voxtral TTS of raw_text
    - event: done   — terminator
    """
    patient = _PATIENTS_BY_ID.get(req.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient["token"] or patient["id"],
        name=patient["name"],
        age=patient["age"],
    )

    client = Mistral(api_key=MISTRAL_API_KEY)

    async def _stream():
        from backend import coach as _coach  # local import avoids circulars

        payload = await _coach.generate_morning_brief(client, patient_ctx)

        yield f"event: brief\ndata: {json.dumps(payload.to_dict(), ensure_ascii=False)}\n\n"

        # Stream TTS of the spoken text
        async for chunk in stream_voice_events(
            text=payload.raw_text,
            voice=DEMO_ASSISTANT_VOICE,
        ):
            yield chunk

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
```

**Note:** `stream_voice_events` is the existing helper in `backend/voxtral.py`. If its signature differs (e.g. it yields audio+text events together, or takes different kwargs), adapt the call. Do NOT invent a new signature — use what `voxtral.py` actually exposes. Read it first if unsure.

- [ ] **Step 6.3: Add `POST /api/coach/reply`**

Below the brief endpoint, add:

```python
class ReplyRequest(BaseModel):
    patient_id: str
    text: str


@app.post("/api/coach/reply")
async def post_coach_reply(req: ReplyRequest) -> dict:
    """Record the user's spoken/typed reply to the morning brief."""
    patient = _PATIENTS_BY_ID.get(req.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient["token"] or patient["id"],
        name=patient["name"],
        age=patient["age"],
    )

    from backend import coach as _coach

    await _coach.record_user_reply(patient_ctx, req.text)
    return {"ok": True, "stored": req.text}
```

- [ ] **Step 6.4: Smoke-test the endpoints locally**

Run: `uv run vital-server &` to start the server in the background.

Then run:

```bash
curl -N -X POST http://localhost:8000/api/coach/brief \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient-1"}'
```

Expected: SSE stream begins, first event is `event: brief\ndata: {...}`. If the patient memory file is empty the brief still returns (memory_callback is the fallback string).

Kill the background server when done: `kill %1` or find the PID and kill it.

If the endpoint errors because no Mistral API key or no Thryve token is set in `.env`, that's a demo-data gap, not a code bug — Task 8 seeds the demo data.

- [ ] **Step 6.5: Commit**

```bash
git add backend/health_server.py
git commit -m "feat(server): add /api/coach/brief and /api/coach/reply

Surface 1 wiring: the morning brief endpoint streams the structured
BriefPayload followed by Voxtral TTS audio via SSE. The reply endpoint
records the user's response to memory and flips the pending protocol
status. Both endpoints reuse the existing patient registry.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 6b: Dashboard insights — `generate_dashboard()` + `/api/dashboard/{patient_id}`

The stats dashboard is the landing view of Surface 2. It shows each watched metric with its current value, its delta vs the user's personal baseline, and an LLM-generated insight phrase grounded in memory. One backend call, one LLM call, N insights returned in a single JSON round trip. Tap-to-chat is pure frontend.

**Files:**
- Modify: `backend/coach.py` (add `generate_dashboard`, `DashboardPayload`, `DashboardStat`)
- Modify: `tests/test_coach.py`
- Modify: `backend/health_server.py` (add `GET /api/dashboard/{patient_id}`)

- [ ] **Step 6b.1: Write the failing test for `DashboardStat` and `DashboardPayload`**

Append to `tests/test_coach.py`:

```python
def test_dashboard_stat_has_expected_fields():
    s = coach.DashboardStat(
        metric="hrv",
        value=38.0,
        unit="ms",
        delta_pct=-14.0,
        insight="14% sous ta moyenne 14j — meme pattern que le 21 mars.",
    )
    d = s.to_dict()
    assert d["metric"] == "hrv"
    assert d["value"] == 38.0
    assert d["unit"] == "ms"
    assert d["delta_pct"] == -14.0
    assert "14%" in d["insight"]


def test_dashboard_payload_serializes_stats():
    payload = coach.DashboardPayload(
        stats=[
            coach.DashboardStat(
                metric="hrv", value=38.0, unit="ms",
                delta_pct=-14.0, insight="below baseline",
            ),
        ],
        generated_at="2026-04-11T09:15:00Z",
    )
    d = payload.to_dict()
    assert isinstance(d["stats"], list)
    assert d["stats"][0]["metric"] == "hrv"
    assert d["generated_at"] == "2026-04-11T09:15:00Z"
```

Run: `uv run pytest tests/test_coach.py -v`
Expected: 2 new tests FAIL with `AttributeError: module 'backend.coach' has no attribute 'DashboardStat'`.

- [ ] **Step 6b.2: Add `DashboardStat` and `DashboardPayload` to `backend/coach.py`**

Append to `backend/coach.py` (after `BriefPayload`):

```python
@dataclass
class DashboardStat:
    """A single stat card on the dashboard: value + delta + LLM insight."""

    metric: str
    value: float
    unit: str
    delta_pct: float  # percentage change vs baseline mean, e.g. -14.0 for 14% below
    insight: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DashboardPayload:
    """Response for GET /api/dashboard/{patient_id}."""

    stats: list[DashboardStat]
    generated_at: str

    def to_dict(self) -> dict:
        return {
            "stats": [s.to_dict() for s in self.stats],
            "generated_at": self.generated_at,
        }
```

- [ ] **Step 6b.3: Run tests to verify they pass**

Run: `uv run pytest tests/test_coach.py -v`
Expected: 6 tests pass (4 from Task 5 + 2 new).

- [ ] **Step 6b.4: Write the failing test for `_compute_delta_pct()`**

Append to `tests/test_coach.py`:

```python
def test_compute_delta_pct_returns_signed_percentage(tmp_path, monkeypatch):
    """delta_pct is (current - baseline_mean) / baseline_mean * 100."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.upsert_baseline("test-token", "hrv", [50, 50, 50, 50, 50, 50, 50], days=7)

    # Current 43 vs baseline 50 → -14%
    delta = coach._compute_delta_pct("test-token", "hrv", current=43)
    assert delta == pytest.approx(-14.0, abs=0.1)


def test_compute_delta_pct_returns_zero_when_no_baseline(tmp_path, monkeypatch):
    """When no baseline exists, delta is reported as 0.0 (UI shows no arrow)."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    assert coach._compute_delta_pct("test-token", "hrv", current=43) == 0.0
```

Run: `uv run pytest tests/test_coach.py -v`
Expected: 2 new tests FAIL.

- [ ] **Step 6b.5: Implement `_compute_delta_pct()`**

Append to `backend/coach.py`:

```python
# Watched metrics for the dashboard, with their display units.
# Kept small on purpose: each stat costs prompt tokens in the insight call.
DASHBOARD_METRICS: list[tuple[str, str]] = [
    ("hrv", "ms"),
    ("resting_hr", "bpm"),
    ("sleep_quality", "/100"),
]


def _compute_delta_pct(user_id: str, metric: str, current: float) -> float:
    """Return the signed percentage change of `current` vs the stored baseline mean.

    Returns 0.0 if no baseline exists for the metric (dashboard will render
    the stat without a delta arrow).
    """
    from backend.nudge import _load_baseline  # reuse parser

    baseline = _load_baseline(user_id, metric)
    if baseline is None or baseline["mean"] == 0:
        return 0.0
    return round(((current - baseline["mean"]) / baseline["mean"]) * 100, 1)
```

**Note:** importing `_load_baseline` from `backend.nudge` inside the function avoids a top-of-module circular: `nudge` already imports from `coach` indirectly once we wire `/dev/fire-notification`, so defer the import to call time.

- [ ] **Step 6b.6: Run tests to verify they pass**

Run: `uv run pytest tests/test_coach.py -v`
Expected: 8 tests pass.

- [ ] **Step 6b.7: Write the failing test for `generate_dashboard()`**

Append to `tests/test_coach.py`:

```python
@pytest.mark.asyncio
async def test_generate_dashboard_returns_insights_per_stat(tmp_path, monkeypatch):
    """generate_dashboard returns one DashboardStat per watched metric with an insight."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.upsert_baseline("test-token", "hrv", [50] * 7, days=7)
    memory.upsert_baseline("test-token", "resting_hr", [62] * 7, days=7)
    memory.upsert_baseline("test-token", "sleep_quality", [75] * 7, days=7)

    patient = PatientContext(token="test-token", name="Sophie", age=34)

    fake_insights = json.dumps({
        "hrv": "14% sous ta moyenne — meme pattern qu'en mars",
        "resting_hr": "dans ta zone habituelle",
        "sleep_quality": "nuit courte, explique la HRV basse",
    })

    class _FakeChoice:
        class message:  # noqa: N801
            content = fake_insights
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]

    mock_client = AsyncMock(spec=Mistral)
    mock_client.chat.complete.return_value = _FakeResponse()

    async def _fake_prefetch(p, s):
        s.vitals = {
            "hrv": [{"date": "2026-04-11", "value": 43}],
            "resting_hr": [{"date": "2026-04-11", "value": 63}],
            "sleep_quality": [{"date": "2026-04-11", "value": 58}],
        }

    with patch("backend.coach.prefetch_session", new=_fake_prefetch):
        payload = await coach.generate_dashboard(mock_client, patient)

    assert isinstance(payload, coach.DashboardPayload)
    assert len(payload.stats) == 3

    by_metric = {s.metric: s for s in payload.stats}
    assert by_metric["hrv"].value == 43
    assert by_metric["hrv"].delta_pct == pytest.approx(-14.0, abs=0.1)
    assert "mars" in by_metric["hrv"].insight
    assert by_metric["sleep_quality"].insight  # not empty
```

Run: `uv run pytest tests/test_coach.py -v`
Expected: 1 new test FAIL.

- [ ] **Step 6b.8: Implement `generate_dashboard()`**

Append to `backend/coach.py`:

```python
_DASHBOARD_SYSTEM_TEMPLATE = """\
Tu es V.I.T.A.L. Tu composes des PHRASES D'INSIGHT pour chaque statistique affichee \
sur le dashboard de l'utilisateur. Chaque phrase doit etre COURTE (1 phrase, max ~20 mots), \
ancree dans la memoire personnelle de l'utilisateur, et utiliser sa baseline personnelle \
au lieu de normes generales.

MEMOIRE :
{memory_blob}

STATS ACTUELLES :
{stats_block}

FORMAT DE SORTIE (JSON strict) :
Un objet avec une cle par metrique listee ci-dessus, chaque valeur etant la phrase d'insight. \
Exemple :
{{"hrv": "14% sous ta moyenne 14 jours, meme pattern que le 21 mars",
  "resting_hr": "dans ta zone habituelle",
  "sleep_quality": "nuit courte, probablement liee a la HRV basse"}}

REGLES :
- Pas de diagnostic medical.
- Cite la memoire quand elle contient un evenement lie a la metrique.
- Phrases courtes, conversationnelles, pas de markdown.
- Reponds uniquement le JSON.
"""


def _build_dashboard_prompt(
    patient: PatientContext,
    stats_snapshot: list[tuple[str, float, float]],
) -> list[dict]:
    """Build the LLM prompt that returns one insight per watched metric.

    stats_snapshot is a list of (metric, current_value, delta_pct) tuples.
    """
    memory_blob = memory.read_all(patient.token)
    stats_block = "\n".join(
        f"- {metric}: {value} (delta vs baseline: {delta:+.1f}%)"
        for metric, value, delta in stats_snapshot
    )
    system_content = _DASHBOARD_SYSTEM_TEMPLATE.format(
        memory_blob=memory_blob,
        stats_block=stats_block,
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "Genere les insights du dashboard."},
    ]


async def generate_dashboard(
    client: Mistral,
    patient: PatientContext,
) -> DashboardPayload:
    """Build the dashboard payload for Surface 2's landing view.

    One Thryve fetch + one LLM call → N insights in a single JSON round trip.
    """
    from datetime import datetime, timezone

    memory.ensure_memory_file(patient.token)

    session = SessionData()
    try:
        await prefetch_session(patient, session)
    except Exception:
        log.exception("prefetch_session failed during dashboard generation")

    # Collect latest value per watched metric
    stats_snapshot: list[tuple[str, float, float]] = []
    latest_values: dict[str, float] = {}
    for metric, _unit in DASHBOARD_METRICS:
        values = (session.vitals or {}).get(metric, [])
        nums = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
        if not nums:
            continue
        current = float(nums[-1])
        delta = _compute_delta_pct(patient.token, metric, current)
        latest_values[metric] = current
        stats_snapshot.append((metric, current, delta))

    if not stats_snapshot:
        return DashboardPayload(
            stats=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    messages = _build_dashboard_prompt(patient, stats_snapshot)

    insights: dict[str, str] = {}
    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
        insights = json.loads(response.choices[0].message.content)
    except Exception:
        log.exception("Dashboard insight LLM call failed")
        # Fall back to empty insights — UI still renders the numbers

    stats: list[DashboardStat] = []
    for metric, unit in DASHBOARD_METRICS:
        if metric not in latest_values:
            continue
        current = latest_values[metric]
        delta = _compute_delta_pct(patient.token, metric, current)
        stats.append(
            DashboardStat(
                metric=metric,
                value=current,
                unit=unit,
                delta_pct=delta,
                insight=insights.get(metric, ""),
            )
        )

    return DashboardPayload(
        stats=stats,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
```

- [ ] **Step 6b.9: Run tests to verify they pass**

Run: `uv run pytest tests/test_coach.py -v`
Expected: 9 tests pass.

- [ ] **Step 6b.10: Add `GET /api/dashboard/{patient_id}` to `health_server.py`**

Append to `backend/health_server.py`:

```python
@app.get("/api/dashboard/{patient_id}")
async def get_dashboard(patient_id: str) -> dict:
    """Return the dashboard payload: stats + LLM-generated insights.

    Called by the frontend on view load and refresh. One backend call,
    one LLM call, all insights in a single JSON round trip.
    """
    patient = _PATIENTS_BY_ID.get(patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient["token"] or patient["id"],
        name=patient["name"],
        age=patient["age"],
    )

    client = Mistral(api_key=MISTRAL_API_KEY)

    from backend import coach as _coach

    payload = await _coach.generate_dashboard(client, patient_ctx)
    return payload.to_dict()
```

- [ ] **Step 6b.11: Smoke test the dashboard endpoint**

Run: `uv run vital-server &` in the background.

```bash
curl -s http://localhost:8000/api/dashboard/patient-1 | python -m json.tool
```

Expected: a JSON object with `stats` (array of 3 entries — hrv, resting_hr, sleep_quality) and `generated_at`. Each stat has `metric`, `value`, `unit`, `delta_pct`, and `insight`. If the seeded memory file is present (Task 9), the `hrv` insight should reference the March 21 event.

Kill the background server.

- [ ] **Step 6b.12: Lint**

Run: `uv run ruff check backend/`
Expected: clean.

- [ ] **Step 6b.13: Commit**

```bash
git add backend/coach.py tests/test_coach.py backend/health_server.py
git commit -m "feat(coach): add dashboard insights endpoint

GET /api/dashboard/{patient_id} returns current Thryve stats plus an
LLM-generated insight phrase per stat, grounded in the user's personal
baseline and memory. One Thryve fetch + one LLM call produces all
insights in a single JSON round trip. Frontend uses this for the
Surface 2 landing view; tap-to-chat is pure frontend and needs no
backend change.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Rewire `nudge.py` to read baselines from memory

Drop the hardcoded thresholds (HRV_DROP_PCT, SLEEP_MIN_QUALITY, RESTING_HR_MAX). Compare current biometrics against the user's personal baseline stored in memory. When a deviation fires, use the LLM to compose a memory-grounded nudge and append the event.

**Files:**
- Modify: `backend/nudge.py`
- Modify: `tests/test_nudge.py`

- [ ] **Step 7.1: Read the existing `test_nudge.py` to understand its shape**

Use the Read tool on `tests/test_nudge.py`. Note which mocks and fixtures it uses — the rewrite should match them where possible so the test harness stays stable.

- [ ] **Step 7.2: Write the failing test for `_deviation_check()`**

Replace the contents of `tests/test_nudge.py` with:

```python
"""Tests for the memory-driven nudge detector."""

from unittest.mock import AsyncMock, patch

import pytest

from backend import memory, nudge
from backend.brain import PatientContext


def test_deviation_check_fires_when_value_below_threshold(tmp_path, monkeypatch):
    """A z-score beyond -2 triggers a deviation."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    # Baseline: mean=50, stddev=3 → z for 38 is (38-50)/3 = -4
    memory.upsert_baseline("test-token", "hrv", [50, 50, 50, 53, 47, 50, 50], days=7)

    deviation = nudge._deviation_check("test-token", "hrv", current=38)
    assert deviation is not None
    assert deviation["metric"] == "hrv"
    assert deviation["z_score"] < -2
    assert deviation["direction"] == "below"


def test_deviation_check_returns_none_when_within_tolerance(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.upsert_baseline("test-token", "hrv", [48, 50, 52, 49, 51, 47, 50], days=7)

    assert nudge._deviation_check("test-token", "hrv", current=49) is None


def test_deviation_check_returns_none_when_no_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    # No baseline stored for hrv
    assert nudge._deviation_check("test-token", "hrv", current=38) is None
```

Run: `uv run pytest tests/test_nudge.py -v`
Expected: 3 tests FAIL (the functions don't exist yet).

- [ ] **Step 7.3: Rewrite `backend/nudge.py` with `_deviation_check()`**

Replace `backend/nudge.py` contents with:

```python
"""Memory-driven biometric nudge detector.

Reads the user's personal baseline from backend.memory, compares the latest
biometric values to it via z-score, and fires a personalized notification
when a deviation crosses the threshold. Every fired event is appended to
memory so the morning brief and chat can reference it.

Triggered on a short interval (by a future scheduler) or manually via the
POST /dev/fire-notification endpoint during the demo.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from mistralai.client import Mistral

from backend import memory
from backend.brain import PatientContext
from backend.config import LLM_MODEL
from backend.thryve import ThryveClient

log = logging.getLogger(__name__)

# Z-score thresholds — a reading beyond ±Z_THRESHOLD stddev from baseline fires.
Z_THRESHOLD = 2.0

# Metrics watched by the nudge loop.
WATCHED_METRICS = ["hrv", "resting_hr", "sleep_quality"]


@dataclass
class NudgeMessage:
    """Payload pushed to the frontend via SSE for an active notification."""

    metric: str
    value: float
    z_score: float
    headline: str
    body: str

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "value": self.value,
            "z_score": round(self.z_score, 2),
            "headline": self.headline,
            "body": self.body,
        }


def _parse_baseline_line(line: str) -> Optional[dict]:
    """Parse a baseline line like 'hrv: mean=51.1 stddev=2.3 n=7 window=7d'."""
    match = re.match(
        r"-?\s*(\w+):\s*mean=([\d.]+)\s+stddev=([\d.]+)\s+n=(\d+)\s+window=(\d+)d",
        line.strip(),
    )
    if not match:
        return None
    return {
        "metric": match.group(1),
        "mean": float(match.group(2)),
        "stddev": float(match.group(3)),
        "n": int(match.group(4)),
        "window": int(match.group(5)),
    }


def _load_baseline(user_id: str, metric: str) -> Optional[dict]:
    """Return the parsed baseline dict for a metric, or None if absent."""
    body = memory.read_section(user_id, memory.SECTION_BASELINES)
    for line in body.splitlines():
        parsed = _parse_baseline_line(line)
        if parsed and parsed["metric"] == metric:
            return parsed
    return None


def _deviation_check(user_id: str, metric: str, current: float) -> Optional[dict]:
    """Check whether `current` deviates from the stored baseline for `metric`.

    Returns a dict with metric/z_score/direction/baseline when a deviation fires,
    None otherwise.
    """
    baseline = _load_baseline(user_id, metric)
    if baseline is None or baseline["stddev"] == 0:
        return None

    z = (current - baseline["mean"]) / baseline["stddev"]
    if abs(z) < Z_THRESHOLD:
        return None

    return {
        "metric": metric,
        "current": current,
        "baseline_mean": baseline["mean"],
        "baseline_stddev": baseline["stddev"],
        "z_score": z,
        "direction": "below" if z < 0 else "above",
    }
```

- [ ] **Step 7.4: Run tests to verify they pass**

Run: `uv run pytest tests/test_nudge.py -v`
Expected: 3 tests pass.

- [ ] **Step 7.5: Write the failing test for `_compose_nudge_via_llm()`**

Append to `tests/test_nudge.py`:

```python
def test_compose_nudge_references_past_events(tmp_path, monkeypatch):
    """The composed nudge message should reference past memory events."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.append_entry(
        "test-token",
        memory.SECTION_EVENTS,
        "2026-03-21: HRV drop to 38ms — recovered in 4d with zone-2 walk",
    )

    deviation = {
        "metric": "hrv",
        "current": 38.0,
        "baseline_mean": 51.0,
        "baseline_stddev": 3.0,
        "z_score": -4.33,
        "direction": "below",
    }

    class _FakeChoice:
        class message:  # noqa: N801
            content = json.dumps({
                "headline": "Ton HRV decroche encore",
                "body": "Troisieme fois ce mois-ci apres une courte nuit — meme pattern que le 21 mars.",
            })
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]

    mock_client = AsyncMock(spec=Mistral)
    mock_client.chat.complete.return_value = _FakeResponse()

    message = nudge._compose_nudge_via_llm(mock_client, "test-token", deviation)
    assert isinstance(message, nudge.NudgeMessage)
    assert message.headline == "Ton HRV decroche encore"
    assert "21 mars" in message.body
```

Run: `uv run pytest tests/test_nudge.py -v`
Expected: 1 new test FAIL.

- [ ] **Step 7.6: Implement `_compose_nudge_via_llm()`**

Append to `backend/nudge.py`:

```python
_NUDGE_SYSTEM_TEMPLATE = """\
Tu es V.I.T.A.L, coach de vie proactif. Un signal biometrique vient de devier de la \
baseline personnelle de l'utilisateur. Tu composes une notification COURTE qui reference \
sa MEMOIRE PERSONNELLE (passe, patterns, protocoles tentes).

MEMOIRE :
{memory_blob}

DEVIATION DETECTEE :
- metrique : {metric}
- valeur actuelle : {current}
- baseline : moyenne={baseline_mean}, stddev={baseline_stddev}
- z-score : {z_score:.2f} ({direction})

FORMAT DE SORTIE (JSON strict) :
{{
  "headline": "5-8 mots max, titre de la notification",
  "body": "1 phrase courte qui cite un evenement passe ou un protocole si la memoire en contient. \
Si la memoire n'a rien, dis 'Premier signal de ce type depuis que j'observe ton rythme.'"
}}

REGLES :
- Pas de diagnostic medical.
- Si memoire contient un evenement REEL lie a cette metrique, cite-le avec sa date.
- Reponds uniquement le JSON.
"""


def _compose_nudge_via_llm(
    client: Mistral,
    user_id: str,
    deviation: dict,
) -> NudgeMessage:
    """Ask the LLM to compose a memory-grounded nudge for a deviation."""
    memory_blob = memory.read_all(user_id)

    system_content = _NUDGE_SYSTEM_TEMPLATE.format(
        memory_blob=memory_blob,
        metric=deviation["metric"],
        current=deviation["current"],
        baseline_mean=deviation["baseline_mean"],
        baseline_stddev=deviation["baseline_stddev"],
        z_score=deviation["z_score"],
        direction=deviation["direction"],
    )

    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": "Compose la notification."},
            ],
            response_format={"type": "json_object"},
        )
    except Exception:
        log.exception("Nudge LLM call failed")
        return NudgeMessage(
            metric=deviation["metric"],
            value=deviation["current"],
            z_score=deviation["z_score"],
            headline="Signal atypique detecte",
            body=f"{deviation['metric']} a {deviation['current']} — ouvre l'app pour plus de contexte.",
        )

    try:
        parsed = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        parsed = {"headline": "Signal atypique", "body": "Ouvre l'app pour plus de contexte."}

    return NudgeMessage(
        metric=deviation["metric"],
        value=deviation["current"],
        z_score=deviation["z_score"],
        headline=parsed.get("headline", "Signal atypique"),
        body=parsed.get("body", ""),
    )
```

- [ ] **Step 7.7: Run tests to verify they pass**

Run: `uv run pytest tests/test_nudge.py -v`
Expected: 4 tests pass.

- [ ] **Step 7.8: Add the top-level `evaluate()` and `fire()` entry points**

Append to `backend/nudge.py`:

```python
async def evaluate(
    client: Mistral,
    patient: PatientContext,
) -> list[NudgeMessage]:
    """Scan watched metrics for the patient and return any fired notifications.

    Called on every tick. Pulls recent vitals from Thryve, compares each metric
    to its stored baseline, and composes a message per deviation. Appends
    fired events to memory so the morning brief and chat can reference them.
    """
    memory.ensure_memory_file(patient.token)

    thryve = ThryveClient()
    try:
        vitals = await thryve.get_vitals(patient.token, days=1)
    except Exception:
        log.exception("Thryve fetch failed during nudge evaluate")
        return []

    messages: list[NudgeMessage] = []
    from datetime import date

    today = date.today().isoformat()

    for metric in WATCHED_METRICS:
        values = vitals.get(metric, [])
        nums = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
        if not nums:
            continue
        current = nums[-1]

        deviation = _deviation_check(patient.token, metric, current)
        if deviation is None:
            continue

        message = _compose_nudge_via_llm(client, patient.token, deviation)
        memory.append_entry(
            patient.token,
            memory.SECTION_EVENTS,
            (
                f"{today}: nudge {metric}={current} "
                f"z={deviation['z_score']:.2f} — {message.headline}"
            ),
        )
        messages.append(message)

    return messages


async def fire_manual(
    client: Mistral,
    patient: PatientContext,
    metric: str,
    current: float,
) -> Optional[NudgeMessage]:
    """Manually fire a notification for a given metric/value — used by /dev/fire-notification.

    Computes the deviation against the stored baseline and composes a message
    even if the deviation is within tolerance (demo override).
    """
    memory.ensure_memory_file(patient.token)

    deviation = _deviation_check(patient.token, metric, current)
    if deviation is None:
        # Force a synthetic deviation so the demo always produces a message
        baseline = _load_baseline(patient.token, metric)
        if baseline is None:
            return None
        deviation = {
            "metric": metric,
            "current": current,
            "baseline_mean": baseline["mean"],
            "baseline_stddev": baseline["stddev"],
            "z_score": (current - baseline["mean"]) / (baseline["stddev"] or 1),
            "direction": "below" if current < baseline["mean"] else "above",
        }

    message = _compose_nudge_via_llm(client, patient.token, deviation)

    from datetime import date

    today = date.today().isoformat()
    memory.append_entry(
        patient.token,
        memory.SECTION_EVENTS,
        f"{today}: nudge (manual) {metric}={current} — {message.headline}",
    )
    return message
```

Also remove the old CLI `main()` at the bottom of `nudge.py` — it's no longer the entry point. Replace it with a no-op guard so the module can still be imported safely:

```python
if __name__ == "__main__":
    print("nudge.py is now library-only — use the /dev/fire-notification endpoint.")
```

- [ ] **Step 7.9: Check for stale references to the old nudge CLI**

Run: use Grep for `vital-nudge` and `nudge.main` across the repo.
Expected: possibly matches in `pyproject.toml` (script entry point) and in `CLAUDE.md` / docs.

For each match in `pyproject.toml`'s `[project.scripts]` section, remove the `vital-nudge` entry — it no longer has a meaningful main.

- [ ] **Step 7.10: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests pass.

- [ ] **Step 7.11: Lint**

Run: `uv run ruff check backend/`
Expected: clean.

- [ ] **Step 7.12: Commit**

```bash
git add backend/nudge.py tests/test_nudge.py pyproject.toml
git commit -m "feat(nudge): rewire to memory-driven baselines and LLM composition

Drops the hardcoded HRV/sleep/resting_hr thresholds. Now reads each
metric's personal baseline from memory.SECTION_BASELINES, fires when
|z-score| >= 2, and uses the LLM to compose a notification that
references past Events and Protocols from the user's memory. Fired
events are appended to memory so the morning brief and chat can
reference them. Also adds fire_manual() for the demo /dev endpoint.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 8: `POST /dev/fire-notification` endpoint and notification SSE channel

The demo fallback: if Thryve test data doesn't move during the stage slot, the presenter hits this hidden endpoint and a live notification pops on screen. Also adds a shared SSE broadcast channel so the notification reaches the frontend without tying it to a specific chat session.

**Files:**
- Modify: `backend/health_server.py`

- [ ] **Step 8.1: Add a simple in-memory notification broadcast channel**

Near the top of `backend/health_server.py` (after the existing `PATIENTS` registry, before any endpoints), add:

```python
# ---------------------------------------------------------------------------
# Notification broadcast — in-process pub/sub for Surface 3
# ---------------------------------------------------------------------------

_notification_subscribers: set[asyncio.Queue] = set()


async def _broadcast_notification(payload: dict) -> None:
    """Push a notification payload to every subscribed SSE stream."""
    dead: list[asyncio.Queue] = []
    for queue in _notification_subscribers:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(queue)
    for q in dead:
        _notification_subscribers.discard(q)
```

- [ ] **Step 8.2: Add `GET /api/notifications/stream` SSE endpoint**

Append:

```python
@app.get("/api/notifications/stream")
async def notifications_stream() -> StreamingResponse:
    """Long-lived SSE stream — frontend subscribes once and receives every nudge."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=32)
    _notification_subscribers.add(queue)

    async def _reader():
        try:
            # Initial heartbeat so the client knows it's connected
            yield "event: ready\ndata: {}\n\n"
            while True:
                payload = await queue.get()
                yield f"event: notification\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            _notification_subscribers.discard(queue)

    return StreamingResponse(_reader(), media_type="text/event-stream")
```

- [ ] **Step 8.3: Add `POST /dev/fire-notification`**

Append:

```python
class FireNotificationRequest(BaseModel):
    patient_id: str
    metric: str
    value: float


@app.post("/dev/fire-notification")
async def dev_fire_notification(req: FireNotificationRequest) -> dict:
    """DEV ONLY — manually trigger a notification for the demo.

    Not documented in the public README. Used during the stage slot
    if Thryve test data doesn't move organically.
    """
    patient = _PATIENTS_BY_ID.get(req.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Unknown patient")

    patient_ctx = PatientContext(
        token=patient["token"] or patient["id"],
        name=patient["name"],
        age=patient["age"],
    )

    client = Mistral(api_key=MISTRAL_API_KEY)

    from backend import nudge as _nudge

    message = await _nudge.fire_manual(client, patient_ctx, req.metric, req.value)
    if message is None:
        raise HTTPException(
            status_code=400,
            detail=f"No baseline stored for metric '{req.metric}' — cannot fire",
        )

    await _broadcast_notification(message.to_dict())
    return {"fired": True, "message": message.to_dict()}
```

- [ ] **Step 8.4: Smoke test the dev endpoint**

Run: `uv run vital-server &` in the background.

In a second terminal (or sequentially after killing the server):

```bash
# Subscribe to notifications stream in background
curl -N http://localhost:8000/api/notifications/stream &

# Fire a nudge
curl -X POST http://localhost:8000/dev/fire-notification \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient-1","metric":"hrv","value":38}'
```

Expected: the subscribed stream receives an `event: notification` with the message JSON. If the baseline isn't seeded yet (Task 9 handles that), the fire call returns 400 — that's fine, Task 9 seeds the demo baseline.

Kill the background server.

- [ ] **Step 8.5: Commit**

```bash
git add backend/health_server.py
git commit -m "feat(server): add notification broadcast and dev fire endpoint

Surface 3 wiring: an in-process pub/sub pushes nudge messages to every
subscribed SSE client (/api/notifications/stream). POST /dev/fire-notification
is the hidden demo hook that triggers a manual notification for a given
metric/value — not documented publicly.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 9: Seed the demo memory file

Author the memory file for the chosen Thryve profile with the exact content the stage demo needs: realistic baselines (matched to the real profile's data from Task 0 Step 0.7), the "three weeks ago" event the morning brief will callback, and a past protocol that worked.

**Critical:** the filename is the Thryve `endUserId` hex string, NOT `patient-1`. The default is `2bfaa7e6f9455ceafa0a59fd5b80496c` (Active Gym Guy / Whoop). If a different profile was chosen in Task 0, use that hex instead. Memory is keyed by `patient.token`, which equals the `endUserId`.

**Critical #2:** the `hrv` and `resting_hr` baselines below are placeholders. Before committing, replace them with values computed from the real profile data you observed in Task 0 Step 0.7. If the real HRV mean is 60 but you ship a baseline mean of 51, the LLM's delta math will contradict what the dashboard shows on screen, and the demo loses credibility. Adjust the narrative event values too (the "38ms drop" should be ~1.5σ below the real mean so it reads as a genuine deviation).

**Files:**
- Create: `data/memory/<thryve_end_user_id>.md`
- Modify: `.gitignore` (verify the un-ignore line matches the chosen hex)

- [ ] **Step 9.1: Update the gitignore un-ignore to match the chosen profile**

In `.gitignore`, find the line added in Step 1.1:

```gitignore
!data/memory/patient-1.md
```

Replace with the real profile hex (default shown):

```gitignore
!data/memory/2bfaa7e6f9455ceafa0a59fd5b80496c.md
```

- [ ] **Step 9.2: Write the seed file**

Create `data/memory/2bfaa7e6f9455ceafa0a59fd5b80496c.md` (or whatever hex was chosen) with the following template. **Adjust the baseline means/stddevs to match the real profile data observed in Task 0 Step 0.7** — the template below uses placeholders that fit a typical Whoop athlete profile but MUST be tuned to reality before the demo.

```markdown
# Active Gym Guy (Whoop) — Sophie Martin persona

## Baselines
- hrv: mean=51.1 stddev=2.8 n=14 window=14d
- resting_hr: mean=62.4 stddev=3.2 n=14 window=14d
- sleep_quality: mean=74.2 stddev=6.1 n=14 window=14d

## Events
- 2026-03-21: HRV drop to 38ms after 2 short-sleep nights — z=-4.6
- 2026-03-22: protocol proposed — magnesium + zone-2 walk instead of HIIT
- 2026-03-25: HRV back to 49ms — recovery in 4 days
- 2026-04-03: sleep_quality drop to 58/100 after a busy work week
- 2026-04-05: sleep_quality back to 72/100

## Protocols
- 2026-03-22: proposed — magnesium + zone-2 walk instead of HIIT — status: accepted — outcome: HRV recovered in 4d
- 2026-04-03: proposed — 20min evening walk + screens off 21h — status: accepted — outcome: sleep quality recovered in 2d

## Context
- 2026-03-15: user mentioned "training for a trail race in June"
- 2026-03-28: user stated "I want to avoid burnout like last autumn"
- 2026-04-02: user mentioned "stressful quarter at work, client deadline April 20"
```

- [ ] **Step 9.3: Verify the seed file is tracked by git**

Run: `git status data/memory/2bfaa7e6f9455ceafa0a59fd5b80496c.md` (or whichever hex was chosen).
Expected: file shows up as `untracked` and not gitignored.

If it shows as ignored, verify the `!data/memory/<hex>.md` line in `.gitignore` matches the hex exactly.

- [ ] **Step 9.4: Smoke test with real seeded data**

Run: `uv run vital-server &` in the background.

Then:

```bash
curl -N -X POST http://localhost:8000/api/coach/brief \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient-1"}'
```

Expected: the `event: brief` payload contains a `memory_callback` that references the March 21 or March 25 HRV recovery event. If the callback is empty or generic, the prompt in `coach.py` may need sharpening — iterate.

```bash
curl -X POST http://localhost:8000/dev/fire-notification \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient-1","metric":"hrv","value":38}'
```

Expected: 200 OK, the message body references March 21.

Kill the background server.

- [ ] **Step 9.5: Commit**

```bash
git add data/memory/2bfaa7e6f9455ceafa0a59fd5b80496c.md .gitignore
git commit -m "feat(memory): seed demo memory file for Active Gym Guy profile

Hand-authored baselines (tuned to the real Whoop profile data),
events, protocols, and context for the stage demo. The March 21 HRV
drop + magnesium protocol is the 'three weeks ago' callback the
morning brief references. Without this file, the memory-driven
callbacks fall back to generic first-brief text.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Task 10: Doc sync (CLAUDE.md, ARCHITECTURE.md, CONTEXT.md, backend.md)

Per `.claude/rules/docs.md`, any backend change must be reflected in four docs. Do this once at the end rather than per-task to avoid churn.

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `.vibe/CONTEXT.md`
- Modify: `.claude/rules/backend.md`

- [ ] **Step 10.1: Update `CLAUDE.md`**

Apply these changes:

1. Replace `8-tool function calling` with `9-tool function calling` everywhere.
2. In the tool table, remove the `award_berries` row. Add two new rows:
   | `read_memory(section)` | Read Baselines / Events / Protocols / Context from persistent memory |
   | `append_memory(entry)` | Append user-stated context during conversation |
3. In the project layout block, add:
   ```
   ├── memory.py                 # Persistent markdown memory (baselines, events, protocols, context)
   ├── coach.py                  # Morning brief orchestrator (Surface 1)
   ```
   Remove `berries.py` and `seed_data.py` if listed (seed_data.py stays; only berries is cut).
4. Replace the description of the weekly vocal checkup ritual (point 4) with:
   > 4. Runs a **daily morning brief** with memory-driven diagnosis + adaptive protocol. See `backend/coach.py`.
5. Replace point 5 (biometric nudges) with:
   > 5. Sends **memory-driven notifications** when biometrics deviate beyond ±2σ from the user's personal baseline stored in memory (`backend/nudge.py`).
6. Remove point 6 (berries).
7. In the architecture diagram, replace `health_store.py → PostgreSQL` if stale; add a row mentioning `memory.py → data/memory/*.md`.
8. In the Commit scopes table, remove the `berries` row and add:
   | `memory` | memory.py, memory sections |
   | `coach` | coach.py, morning brief |
9. Remove the `uv run vital-nudge` command from the Commands block.
10. In the LLM Tool Use section, change `exposes 8 tools` to `exposes 9 tools`.

- [ ] **Step 10.2: Update `docs/ARCHITECTURE.md`**

1. Update the tool list from 8 → 9 tools (replace berries entry with read_memory + append_memory).
2. Add the new endpoints to the endpoint list:
   - `POST /api/coach/brief` — morning brief SSE stream
   - `POST /api/coach/reply` — record user's reply to the brief
   - `GET /api/dashboard/{patient_id}` — stats dashboard with LLM insights (Surface 2 landing)
   - `GET /api/notifications/stream` — long-lived SSE for active notifications
   - `POST /dev/fire-notification` — dev-only manual notification trigger
3. Remove any berries-related endpoints.
4. Update the system diagram or module list to include `memory.py` and `coach.py`.

- [ ] **Step 10.3: Update `.vibe/CONTEXT.md`**

1. Update the tool count from 8 → 9.
2. In the architecture summary, mention the three surfaces (morning brief, chat with data, memory-driven notifications) and the shared memory spine.
3. Remove any mention of the weekly vocal checkup and berries.

- [ ] **Step 10.4: Update `.claude/rules/backend.md`**

In the module table, remove `berries.py` and add:

| memory.py | Persistent markdown memory (Baselines, Events, Protocols, Context) |
| coach.py | Morning brief orchestrator: reads memory + vitals, composes a brief via LLM |

Update the Modules table in `nudge.py`'s row from "Daily biometric nudge detector" to "Memory-driven notification detector (z-score vs baselines)".

- [ ] **Step 10.5: Grep for any remaining stale references**

Run: use Grep with pattern `berries|weekly.checkup|vital-nudge|8.tool|8 outils` over `*.md`.
Expected: no matches after the edits above. If matches remain in `wiki/` or `docs/plan-*.md`, leave them per `.claude/rules/docs.md` (those directories are excluded from the doc sync rule).

- [ ] **Step 10.6: Run the full test suite one more time**

Run: `uv run pytest -v`
Expected: every test passes.

- [ ] **Step 10.7: Lint**

Run: `uv run ruff check backend/`
Expected: clean.

- [ ] **Step 10.8: Commit**

```bash
git add CLAUDE.md docs/ARCHITECTURE.md .vibe/CONTEXT.md .claude/rules/backend.md
git commit -m "docs: sync CLAUDE, ARCHITECTURE, CONTEXT, backend rules for coach pivot

Tool count 8 → 9 (drop award_berries, add read_memory + append_memory).
New modules memory.py and coach.py listed. Weekly vocal checkup
references replaced with daily morning brief. Three new endpoints
and the dev fire-notification endpoint added to the architecture doc.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Done — acceptance checklist

Before declaring the backend ready for the frontend team and the stage rehearsal, verify:

- [ ] `.env` contains real Thryve credentials from the organizer and `THRYVE_BASE_URL=https://api-qa.thryve.de/v5`
- [ ] `uv run vital-server` starts without raising `Missing Thryve env vars`
- [ ] `uv run pytest -v` — all tests pass (memory, coach, nudge, existing health_server tests)
- [ ] `uv run ruff check backend/` — clean
- [ ] A direct `ThryveClient().get_vitals(<demo_hex>, days=14)` call returns non-empty HRV data for the chosen profile
- [ ] `POST /api/coach/brief` returns a brief whose `memory_callback` references a real event from the seeded memory file
- [ ] `GET /api/dashboard/patient-1` returns 3 stats (hrv, resting_hr, sleep_quality) with non-empty insights, and the hrv insight references the March 21 event
- [ ] The dashboard HRV value and the brief's diagnosis numbers are consistent with the seeded baseline (no contradictions on screen)
- [ ] `POST /dev/fire-notification` with `patient-1` + `hrv` + `38` returns a message that mentions the March 21 event
- [ ] `GET /api/notifications/stream` receives the notification from the previous step via SSE
- [ ] `grep -r "berries\|weekly.checkup" backend/` returns zero matches
- [ ] `grep -r "8.tool\|8 outils" backend/ CLAUDE.md docs/ARCHITECTURE.md .vibe/CONTEXT.md .claude/rules/backend.md` returns zero matches
