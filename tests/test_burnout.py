"""Tests for burnout score computation."""

from backend.burnout import BurnoutResult, compute_burnout, level_from_score


def _make_metrics(
    stress=None,
    mental_health_risk=None,
    sick_leave=None,
    hrv_latest=None,
    hrv_baseline=None,
    sleep_quality=None,
    sleep_regularity=None,
    resting_hr=None,
):
    """Build a metrics dict matching ThryveClient.get_burnout_metrics() output."""
    m = {}
    if stress is not None:
        m["stress"] = {"latest": stress, "baseline_7d": stress, "values": [], "count": 1}
    if mental_health_risk is not None:
        m["mental_health_risk"] = {
            "latest": mental_health_risk, "baseline_7d": mental_health_risk,
            "values": [], "count": 1,
        }
    if sick_leave is not None:
        m["sick_leave_prediction"] = {
            "latest": sick_leave, "baseline_7d": sick_leave, "values": [], "count": 1,
        }
    if hrv_latest is not None:
        m["hrv"] = {
            "latest": hrv_latest,
            "baseline_7d": hrv_baseline if hrv_baseline is not None else hrv_latest,
            "values": [], "count": 1,
        }
    if sleep_quality is not None:
        m["sleep_quality"] = {
            "latest": sleep_quality, "baseline_7d": sleep_quality, "values": [], "count": 1,
        }
    if sleep_regularity is not None:
        m["sleep_regularity"] = {
            "latest": sleep_regularity, "baseline_7d": sleep_regularity,
            "values": [], "count": 1,
        }
    if resting_hr is not None:
        m["resting_hr"] = {
            "latest": resting_hr, "baseline_7d": resting_hr, "values": [], "count": 1,
        }
    return m


class TestLevelFromScore:
    def test_low(self):
        assert level_from_score(0) == "low"
        assert level_from_score(15) == "low"
        assert level_from_score(29) == "low"

    def test_moderate(self):
        assert level_from_score(30) == "moderate"
        assert level_from_score(45) == "moderate"
        assert level_from_score(59) == "moderate"

    def test_high(self):
        assert level_from_score(60) == "high"
        assert level_from_score(80) == "high"
        assert level_from_score(100) == "high"


class TestComputeBurnoutThryve:
    """Tests using Thryve analytics (stress, mental_health_risk, sick_leave)."""

    def test_low_stress_low_score(self):
        """Low stress, no risk -> low burnout."""
        result = compute_burnout(_make_metrics(stress=15, mental_health_risk=5, sick_leave=0))
        assert isinstance(result, BurnoutResult)
        assert result.level == "low"
        assert result.score < 30
        assert result.source == "thryve"

    def test_high_stress_high_score(self):
        """High stress, high risk -> high burnout."""
        result = compute_burnout(_make_metrics(stress=85, mental_health_risk=60, sick_leave=4))
        assert result.level == "high"
        assert result.score >= 60
        assert result.source == "thryve"

    def test_moderate_stress(self):
        """Moderate signals -> moderate risk."""
        result = compute_burnout(_make_metrics(stress=50, mental_health_risk=15, sick_leave=1))
        assert result.level == "moderate"
        assert 30 <= result.score < 60

    def test_partial_analytics_stress_only(self):
        """Only stress available — still uses thryve source."""
        result = compute_burnout(_make_metrics(stress=80))
        assert result.source == "thryve"
        assert result.score >= 60

    def test_signals_generated_on_high_stress(self):
        """High stress generates a signal."""
        result = compute_burnout(_make_metrics(stress=75, mental_health_risk=30, sick_leave=3))
        assert any("stress" in s.lower() for s in result.signals)

    def test_signals_mental_health_risk(self):
        """High mental health risk generates a signal."""
        result = compute_burnout(_make_metrics(stress=30, mental_health_risk=40))
        assert any("mental" in s.lower() or "santé" in s.lower() for s in result.signals)

    def test_signals_sick_leave(self):
        """High sick leave prediction generates a signal."""
        result = compute_burnout(_make_metrics(stress=30, sick_leave=4))
        assert any("arrêt" in s.lower() or "maladie" in s.lower() for s in result.signals)

    def test_score_clamped_0_100(self):
        """Score always in [0, 100]."""
        best = compute_burnout(_make_metrics(stress=0, mental_health_risk=0, sick_leave=0))
        assert 0 <= best.score <= 100
        worst = compute_burnout(_make_metrics(stress=100, mental_health_risk=100, sick_leave=10))
        assert 0 <= worst.score <= 100


class TestComputeBurnoutFallback:
    """Tests when Thryve analytics are unavailable — fallback to raw biometrics."""

    def test_fallback_healthy(self):
        """Good raw biometrics -> low risk, fallback source."""
        result = compute_burnout(
            _make_metrics(hrv_latest=50, hrv_baseline=50, sleep_quality=85, resting_hr=58)
        )
        assert result.source == "fallback"
        assert result.level == "low"
        assert result.score < 30

    def test_fallback_stressed(self):
        """Bad raw biometrics -> high risk."""
        result = compute_burnout(
            _make_metrics(hrv_latest=15, hrv_baseline=50, sleep_quality=30, resting_hr=95)
        )
        assert result.source == "fallback"
        assert result.level == "high"
        assert result.score >= 60

    def test_fallback_signals_hrv(self):
        """Low HRV generates a signal."""
        result = compute_burnout(
            _make_metrics(hrv_latest=20, hrv_baseline=50, sleep_quality=80, resting_hr=60)
        )
        assert any("HRV" in s for s in result.signals)

    def test_fallback_signals_sleep(self):
        """Low sleep quality generates a signal."""
        result = compute_burnout(
            _make_metrics(hrv_latest=50, hrv_baseline=50, sleep_quality=40, resting_hr=60)
        )
        assert any("sommeil" in s.lower() for s in result.signals)

    def test_fallback_signals_rhr(self):
        """High resting HR generates a signal."""
        result = compute_burnout(
            _make_metrics(hrv_latest=50, hrv_baseline=50, sleep_quality=80, resting_hr=92)
        )
        assert any("FC" in s or "repos" in s for s in result.signals)

    def test_empty_metrics_zero_score(self):
        """No data at all -> score 0."""
        result = compute_burnout({})
        assert result.score == 0
        assert result.source == "fallback"
