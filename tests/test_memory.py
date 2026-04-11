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


def test_append_entry_handles_body_containing_section_header(tmp_path, monkeypatch):
    """An entry whose text contains '## Events' must not break future section lookups.

    Regression test: without line-anchored matching, find('## Events') would hit
    inside the Baselines entry and corrupt subsequent reads/writes.
    """
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")
    # An entry that mentions another section heading verbatim
    memory.append_entry(
        "patient-1",
        memory.SECTION_BASELINES,
        "note: user asked about '## Events' naming",
    )
    memory.append_entry("patient-1", memory.SECTION_EVENTS, "HRV drop")

    baselines = memory.read_section("patient-1", memory.SECTION_BASELINES)
    events = memory.read_section("patient-1", memory.SECTION_EVENTS)

    assert "## Events" in baselines  # the note stays in Baselines
    assert "HRV drop" in events
    assert "HRV drop" not in baselines  # no cross-leak


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


def test_upsert_baseline_replaces_existing_entry(tmp_path, monkeypatch):
    """Writing a baseline for the same metric twice replaces the old entry."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("patient-1")

    memory.upsert_baseline("patient-1", "hrv", [50, 52, 48], days=3)
    memory.upsert_baseline("patient-1", "hrv", [60, 62, 58], days=3)

    baselines = memory.read_section("patient-1", memory.SECTION_BASELINES)
    assert "mean=60" in baselines
    assert "mean=50" not in baselines
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
    assert "mean=70" in baselines
    assert "mean=63" in baselines
