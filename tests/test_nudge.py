"""Tests for nudge evaluation logic."""

import pytest

from backend.nudge import NudgeDecision, evaluate


def _make_metrics(
    hrv_latest=45.0,
    hrv_baseline=50.0,
    sleep_latest=80.0,
    rhr_latest=65.0,
):
    """Build a mock get_burnout_metrics return value."""
    return {
        "hrv": {
            "values": [],
            "baseline_7d": hrv_baseline,
            "latest": hrv_latest,
            "count": 7,
        },
        "sleep_quality": {
            "values": [],
            "baseline_7d": sleep_latest,
            "latest": sleep_latest,
            "count": 7,
        },
        "resting_hr": {
            "values": [],
            "baseline_7d": rhr_latest,
            "latest": rhr_latest,
            "count": 7,
        },
    }


@pytest.fixture()
def mock_thryve(monkeypatch):
    """Patch ThryveClient.get_burnout_metrics to return controlled data."""
    _metrics = {}

    async def _fake_get_burnout_metrics(self, patient_token, days=7):
        return _metrics

    monkeypatch.setattr(
        "backend.thryve.ThryveClient.get_burnout_metrics",
        _fake_get_burnout_metrics,
    )
    return _metrics


@pytest.mark.asyncio
class TestEvaluate:
    async def test_no_nudge_all_green(self, mock_thryve):
        """No nudge when all signals are healthy."""
        mock_thryve.update(_make_metrics(
            hrv_latest=48.0,
            hrv_baseline=50.0,
            sleep_latest=85.0,
            rhr_latest=62.0,
        ))
        decision = await evaluate("test-token")
        assert isinstance(decision, NudgeDecision)
        assert decision.should_nudge is False
        assert decision.reasons == []

    async def test_nudge_hrv_drop(self, mock_thryve):
        """Nudge triggered when HRV drops more than 15%."""
        mock_thryve.update(_make_metrics(
            hrv_latest=30.0,
            hrv_baseline=50.0,  # -40% drop
            sleep_latest=85.0,
            rhr_latest=62.0,
        ))
        decision = await evaluate("test-token")
        assert decision.should_nudge is True
        assert any("HRV" in r for r in decision.reasons)

    async def test_nudge_bad_sleep(self, mock_thryve):
        """Nudge triggered when sleep quality is below threshold."""
        mock_thryve.update(_make_metrics(
            hrv_latest=48.0,
            hrv_baseline=50.0,
            sleep_latest=40.0,  # below 60
            rhr_latest=62.0,
        ))
        decision = await evaluate("test-token")
        assert decision.should_nudge is True
        assert any("sommeil" in r.lower() or "sleep" in r.lower() for r in decision.reasons)

    async def test_nudge_high_resting_hr(self, mock_thryve):
        """Nudge triggered when resting HR exceeds threshold."""
        mock_thryve.update(_make_metrics(
            hrv_latest=48.0,
            hrv_baseline=50.0,
            sleep_latest=85.0,
            rhr_latest=88.0,  # above 80
        ))
        decision = await evaluate("test-token")
        assert decision.should_nudge is True
        assert any("FC" in r for r in decision.reasons)

    async def test_nudge_multiple_bad_signals(self, mock_thryve):
        """Multiple bad signals produce multiple reasons."""
        mock_thryve.update(_make_metrics(
            hrv_latest=25.0,
            hrv_baseline=50.0,
            sleep_latest=35.0,
            rhr_latest=90.0,
        ))
        decision = await evaluate("test-token")
        assert decision.should_nudge is True
        assert len(decision.reasons) == 3

    async def test_to_dict(self, mock_thryve):
        """NudgeDecision.to_dict() returns the expected shape."""
        mock_thryve.update(_make_metrics())
        decision = await evaluate("test-token")
        d = decision.to_dict()
        assert "should_nudge" in d
        assert "reasons" in d
        assert "headline" in d

    async def test_empty_metrics(self, mock_thryve):
        """No crash when metrics are empty (no data from Thryve)."""
        # mock_thryve is already empty dict
        decision = await evaluate("test-token")
        assert decision.should_nudge is False
