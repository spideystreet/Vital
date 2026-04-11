"""Tests for the memory-driven nudge detector."""

import json
from unittest.mock import MagicMock

import pytest

from backend import memory, nudge
from backend.brain import PatientContext  # noqa: F401 — PatientContext may be used by future tests


def test_deviation_check_fires_when_value_below_threshold(tmp_path, monkeypatch):
    """A z-score beyond -2 triggers a deviation."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
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
    assert nudge._deviation_check("test-token", "hrv", current=38) is None


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

    mock_client = MagicMock()
    mock_client.chat.complete.return_value = _FakeResponse()

    message = nudge._compose_nudge_via_llm(mock_client, "test-token", deviation)
    assert isinstance(message, nudge.NudgeMessage)
    assert message.headline == "Ton HRV decroche encore"
    assert "21 mars" in message.body
