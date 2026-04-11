"""Burnout score engine — built on Thryve analytics.

Uses Thryve-computed health scores (stress, mental health risk,
sick leave prediction) as primary signals, with raw biometrics
(HRV, sleep quality, resting HR) as supporting context.

Thryve analytics codes used:
    6010 — AverageStress (daily, from HRV + activity)
    2254 — SleepRelatedMentalHealthRisk (%, from sleep stages)
    2257 — SleepRelatedSickLeavePrediction (excess days, from sleep)

When Thryve analytics are unavailable, falls back to raw biometrics
with a simple heuristic (clearly marked as fallback in the result).
"""

from dataclasses import dataclass, field

# Risk thresholds for the final score (0-100)
THRESHOLD_LOW = 30
THRESHOLD_MODERATE = 60


@dataclass
class BurnoutResult:
    score: int  # 0-100
    level: str  # "low", "moderate", "high"
    signals: list[str] = field(default_factory=list)
    source: str = "thryve"  # "thryve" or "fallback"
    components: dict = field(default_factory=dict)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def level_from_score(score: int) -> str:
    """Return 'low', 'moderate', or 'high' from score."""
    if score < THRESHOLD_LOW:
        return "low"
    if score < THRESHOLD_MODERATE:
        return "moderate"
    return "high"


def _get(metrics: dict, key: str, field: str = "latest"):
    """Safely extract a field from a metrics entry (handles None values)."""
    entry = metrics.get(key)
    if isinstance(entry, dict):
        return entry.get(field)
    return None


def compute_burnout(metrics: dict) -> BurnoutResult:
    """Compute burnout score from Thryve metrics dict.

    Args:
        metrics: Dict from ThryveClient.get_burnout_metrics().
                 Keys are metric names, values have "latest" and "baseline_7d".

    Returns:
        BurnoutResult with score, level, signals, and source.
    """
    stress = _get(metrics, "stress")
    mental_health_risk = _get(metrics, "mental_health_risk")
    sick_leave = _get(metrics, "sick_leave_prediction")

    has_analytics = any(v is not None for v in [stress, mental_health_risk, sick_leave])

    if has_analytics:
        return _score_from_thryve(stress, mental_health_risk, sick_leave, metrics)
    return _score_from_fallback(metrics)


def _score_from_thryve(
    stress: float | None,
    mental_health_risk: float | None,
    sick_leave: float | None,
    metrics: dict,
) -> BurnoutResult:
    """Score using Thryve-computed analytics as primary signals."""
    signals: list[str] = []
    components: dict = {}
    weighted_sum = 0.0
    total_weight = 0.0

    # Stress (6010): daily stress from HRV — scale varies by Thryve, normalize to 0-100
    if stress is not None:
        components["stress"] = stress
        # Thryve stress is typically 0-100, higher = more stressed
        weighted_sum += stress * 0.45
        total_weight += 0.45
        if stress > 60:
            signals.append(f"Niveau de stress élevé ({stress:.0f}/100)")

    # Mental health risk (2254): % elevated risk from sleep
    if mental_health_risk is not None:
        components["mental_health_risk"] = mental_health_risk
        # Already a percentage — cap contribution at 100
        risk_norm = _clamp(mental_health_risk / 100.0)
        weighted_sum += risk_norm * 100 * 0.35
        total_weight += 0.35
        if mental_health_risk > 20:
            signals.append(
                f"Risque santé mentale élevé ({mental_health_risk:.0f}%)"
            )

    # Sick leave prediction (2257): excess days vs reference population
    if sick_leave is not None:
        components["sick_leave_prediction"] = sick_leave
        # Normalize: 0 extra days = 0, 5+ extra days = 100
        sick_norm = _clamp(sick_leave / 5.0)
        weighted_sum += sick_norm * 100 * 0.20
        total_weight += 0.20
        if sick_leave > 2:
            signals.append(
                f"Prédiction arrêt maladie +{sick_leave:.1f} jours"
            )

    # Compute score
    if total_weight > 0:
        raw_score = weighted_sum / total_weight
    else:
        raw_score = 0.0

    score = int(_clamp(raw_score, 0.0, 100.0))
    level = level_from_score(score)

    # Add raw biometric context signals (not used in score, just for display)
    _add_biometric_signals(signals, metrics)

    return BurnoutResult(
        score=score,
        level=level,
        signals=signals,
        source="thryve",
        components=components,
    )


def _score_from_fallback(metrics: dict) -> BurnoutResult:
    """Fallback score from raw biometrics when Thryve analytics unavailable.

    Uses HRV, sleep quality, and resting HR with a simple heuristic.
    Clearly marked as fallback — not a validated formula.
    """
    signals: list[str] = []
    components: dict = {}

    hrv_current = _get(metrics, "hrv")
    hrv_baseline = _get(metrics, "hrv", "baseline_7d")
    sleep_quality = _get(metrics, "sleep_quality")
    resting_hr = _get(metrics, "resting_hr")

    weighted_sum = 0.0
    total_weight = 0.0

    if hrv_current is not None and hrv_baseline and hrv_baseline > 0:
        hrv_ratio = _clamp(hrv_current / hrv_baseline)
        components["hrv_ratio"] = round(hrv_ratio, 3)
        weighted_sum += (1.0 - hrv_ratio) * 100 * 0.45
        total_weight += 0.45
        if hrv_ratio < 0.7:
            signals.append(
                f"HRV en baisse ({hrv_current:.0f} ms vs baseline {hrv_baseline:.0f} ms)"
            )

    if sleep_quality is not None:
        sleep_norm = _clamp(sleep_quality / 100.0)
        components["sleep_quality"] = sleep_quality
        weighted_sum += (1.0 - sleep_norm) * 100 * 0.35
        total_weight += 0.35
        if sleep_quality < 60:
            signals.append(f"Qualité de sommeil faible ({sleep_quality:.0f}/100)")

    if resting_hr is not None:
        rhr_norm = _clamp((resting_hr - 50.0) / 50.0)
        components["resting_hr"] = resting_hr
        weighted_sum += rhr_norm * 100 * 0.20
        total_weight += 0.20
        if resting_hr > 80:
            signals.append(f"FC repos élevée ({resting_hr:.0f} bpm)")

    if total_weight > 0:
        raw_score = weighted_sum / total_weight
    else:
        raw_score = 0.0

    score = int(_clamp(raw_score, 0.0, 100.0))
    level = level_from_score(score)

    return BurnoutResult(
        score=score,
        level=level,
        signals=signals,
        source="fallback",
        components=components,
    )


def _add_biometric_signals(signals: list[str], metrics: dict) -> None:
    """Append raw biometric context signals (for display, not scoring)."""
    sleep_q = _get(metrics, "sleep_quality")
    if sleep_q is not None and sleep_q < 60:
        signals.append(f"Qualité de sommeil faible ({sleep_q:.0f}/100)")

    sleep_reg = _get(metrics, "sleep_regularity")
    if sleep_reg is not None and sleep_reg < 60:
        signals.append(f"Régularité de sommeil faible ({sleep_reg:.0f}/100)")

    rhr = _get(metrics, "resting_hr")
    if rhr is not None and rhr > 80:
        signals.append(f"FC repos élevée ({rhr:.0f} bpm)")
