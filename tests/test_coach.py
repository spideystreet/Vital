"""Tests for the morning brief orchestrator."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mistralai.client import Mistral

from backend import coach, memory
from backend.brain import PatientContext, SessionData


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
    session.vitals = {
        "hrv": [{"date": "2026-04-10", "value": 38}],
        "sleep_quality": [{"date": "2026-04-10", "value": 58}],
    }

    messages = coach._build_brief_prompt(patient, session)

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    system_content = messages[0]["content"]
    assert "HRV drop to 38ms" in system_content
    assert "hrv: mean=49.6" in system_content or "hrv: mean=49.5" in system_content
    assert "38" in system_content


@pytest.mark.asyncio
async def test_generate_morning_brief_writes_to_memory(tmp_path, monkeypatch):
    """The brief is parsed into a BriefPayload and written to Events + Protocols."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.upsert_baseline("test-token", "hrv", [48, 50, 52, 49, 51, 47, 50], days=7)

    patient = PatientContext(token="test-token", name="Sophie", age=34)

    fake_llm_json = json.dumps({
        "diagnosis": "HRV a 38ms, 14% sous ta moyenne 7 jours.",
        "memory_callback": "Meme pattern que le 21 mars, le protocole magnesium + marche zone 2 avait marche en 4 jours.",
        "protocol": "Zero HIIT aujourd'hui. Marche 40min a allure souple + magnesium ce soir.",
        "question": "Tu peux tenir ce protocole aujourd'hui ?",
        "raw_text": "Bonjour Sophie, ton HRV est a 38 ms ce matin.",
    })

    class _FakeChoice:
        class message:  # noqa: N801
            content = fake_llm_json
        finish_reason = "stop"

    class _FakeResponse:
        choices = [_FakeChoice()]

    mock_client = MagicMock()
    mock_client.chat.complete.return_value = _FakeResponse()

    async def _fake_prefetch(p, s):
        s.vitals = {"hrv": [{"date": "2026-04-11", "value": 38}]}

    with patch("backend.coach.prefetch_session", new=_fake_prefetch):
        payload = await coach.generate_morning_brief(mock_client, patient)

    assert isinstance(payload, coach.BriefPayload)
    assert payload.diagnosis == "HRV a 38ms, 14% sous ta moyenne 7 jours."
    assert "21 mars" in payload.memory_callback

    events = memory.read_section("test-token", memory.SECTION_EVENTS)
    protocols = memory.read_section("test-token", memory.SECTION_PROTOCOLS)
    assert "HRV a 38ms" in events
    assert "zone 2" in protocols.lower() or "HIIT" in protocols


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
    protocols = memory.read_section("test-token", memory.SECTION_PROTOCOLS)
    assert "status: accepted" in protocols


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


def test_compute_delta_pct_returns_signed_percentage(tmp_path, monkeypatch):
    """delta_pct is (current - baseline_mean) / baseline_mean * 100."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    memory.upsert_baseline("test-token", "hrv", [50, 50, 50, 50, 50, 50, 50], days=7)

    delta = coach._compute_delta_pct("test-token", "hrv", current=43)
    assert delta == pytest.approx(-14.0, abs=0.1)


def test_compute_delta_pct_returns_zero_when_no_baseline(tmp_path, monkeypatch):
    """When no baseline exists, delta is 0.0."""
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    memory.ensure_memory_file("test-token")
    assert coach._compute_delta_pct("test-token", "hrv", current=43) == 0.0


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

    mock_client = MagicMock()
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
    assert by_metric["sleep_quality"].insight
