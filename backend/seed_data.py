"""Generate realistic health data for testing the LLM responses."""

import random
from datetime import UTC, datetime, timedelta

# ----------------------------------------------------------------------
# Demo-mode synthetic vitals
# ----------------------------------------------------------------------
# Tuned to match the seeded memory baselines in
# data/memory/2bfaa7e6f9455ceafa0a59fd5b80496c.md so the dashboard's
# delta_pct math lines up with the morning brief narrative.
# ----------------------------------------------------------------------

# (mean, stddev) pulled directly from the Baselines section.
_DEMO_BASELINES: dict[str, tuple[float, float]] = {
    "hrv": (55.2, 4.8),
    "resting_hr": (58.7, 3.4),
    "sleep_quality": (76.3, 6.2),
    "heart_rate_sleep": (52.0, 4.0),
    "steps": (9500.0, 1800.0),
}

# Last-day values — deliberately offset from baseline so the dashboard
# reads a non-zero delta and the brief has a concrete signal to talk about.
# None of these cross the 2σ nudge threshold on their own (that's what
# /dev/fire-notification is for — the stage driver controls that trigger).
_DEMO_LATEST: dict[str, float] = {
    "hrv": 48.0,          # ~-1.5σ — "14% below your 14-day baseline"
    "resting_hr": 64.0,   # ~+1.6σ — elevated
    "sleep_quality": 68.0,  # ~-1.3σ — moderate drop
    "heart_rate_sleep": 55.0,
    "steps": 7200.0,  # ~-1.3σ — below usual, invites a challenge
}


def _demo_series(metric: str, days: int) -> list[dict]:
    """Build a `days`-long list of day/value dicts centered on the baseline.

    Uses a fixed random seed so every call returns the same series (stage
    repeatability). The final day is forced to the `_DEMO_LATEST` value.
    """
    mean, stddev = _DEMO_BASELINES[metric]
    rng = random.Random(hash(metric) & 0xFFFFFFFF)
    today = datetime.now().date()
    out: list[dict] = []
    for i in range(days):
        day = today - timedelta(days=days - 1 - i)
        if i == days - 1:
            value = _DEMO_LATEST[metric]
        else:
            value = round(rng.gauss(mean, stddev * 0.6), 1)
        out.append({"date": day.isoformat(), "value": value, "unit": None})
    return out


def build_demo_vitals(days: int = 14) -> dict:
    """Return the `get_vitals` shape for DEMO_MODE — one entry per metric."""
    return {metric: _demo_series(metric, days) for metric in _DEMO_BASELINES}


def build_demo_blood_panel() -> dict:
    """Return the `get_blood_panel` shape for DEMO_MODE with plausible labs."""
    return {
        "blood_glucose": [
            {"date": None, "value": 94, "unit": "mg/dL"},
            {"date": None, "value": 98, "unit": "mg/dL"},
            {"date": None, "value": 91, "unit": "mg/dL"},
        ],
        "hba1c": [{"date": None, "value": 5.3, "unit": "%"}],
        "ferritin": [{"value": 85, "unit": "ng/mL", "simulated": True}],
        "cortisol": [{"value": 14.2, "unit": "ug/dL", "simulated": True}],
        "vitamin_d": [{"value": 32, "unit": "ng/mL", "simulated": True}],
    }


def build_demo_burnout_metrics(days: int = 7) -> dict:
    """Return the `get_burnout_metrics` shape for DEMO_MODE."""
    vitals = {metric: _demo_series(metric, days) for metric in _DEMO_BASELINES}
    # Thryve analytic scores — low-moderate stress persona.
    vitals["stress"] = [
        {"date": None, "value": 32, "unit": "/100"},
        {"date": None, "value": 28, "unit": "/100"},
        {"date": None, "value": 41, "unit": "/100"},
    ]
    vitals["mental_health_risk"] = [{"date": None, "value": 15, "unit": "/100"}]
    vitals["sick_leave_prediction"] = [{"date": None, "value": 5, "unit": "/100"}]

    result: dict = {}
    for name, values in vitals.items():
        numeric = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
        baseline = sum(numeric) / len(numeric) if numeric else None
        result[name] = {
            "values": values,
            "baseline_7d": round(baseline, 2) if baseline is not None else None,
            "latest": numeric[-1] if numeric else None,
            "count": len(numeric),
        }
    return result

SCENARIOS = {
    "healthy": {
        "description": "Healthy active person, good sleep, low stress",
        "metrics": {
            "heart_rate": {"avg": 68, "spread": 8, "count": 24},
            "resting_hr": {"avg": 58, "spread": 3, "count": 4},
            "hrv": {"avg": 52, "spread": 8, "count": 6},
            "spo2": {"avg": 98, "spread": 1, "count": 6},
            "respiratory_rate": {"avg": 14, "spread": 1, "count": 4},
            "wrist_temperature": {"avg": 0.1, "spread": 0.2, "count": 2},
            "vo2_max": {"avg": 44, "spread": 0, "count": 1},
            "steps": {"avg": 9500, "spread": 1500, "count": 1},
            "active_calories": {"avg": 420, "spread": 50, "count": 1},
            "resting_energy": {"avg": 1650, "spread": 20, "count": 1},
            "distance": {"avg": 7.2, "spread": 1.0, "count": 1},
            "workout": {"avg": 45, "spread": 10, "count": 1},
            "sleep": {"avg": 7.8, "spread": 0.3, "count": 1},
            "sleep_deep": {"avg": 1.5, "spread": 0.2, "count": 1},
            "sleep_rem": {"avg": 1.8, "spread": 0.2, "count": 1},
            "stand_time": {"avg": 45, "spread": 10, "count": 1},
            "mindful_minutes": {"avg": 10, "spread": 3, "count": 1},
            "walking_hr_avg": {"avg": 95, "spread": 5, "count": 4},
            "audio_exposure": {"avg": 62, "spread": 8, "count": 4},
            "exercise_time": {"avg": 35, "spread": 10, "count": 1},
        },
    },
    "stressed": {
        "description": "Stressed person, poor sleep, high HR, low HRV",
        "metrics": {
            "heart_rate": {"avg": 82, "spread": 12, "count": 24},
            "resting_hr": {"avg": 74, "spread": 4, "count": 4},
            "hrv": {"avg": 22, "spread": 5, "count": 6},
            "spo2": {"avg": 97, "spread": 1, "count": 6},
            "respiratory_rate": {"avg": 18, "spread": 2, "count": 4},
            "wrist_temperature": {"avg": 0.4, "spread": 0.3, "count": 2},
            "vo2_max": {"avg": 38, "spread": 0, "count": 1},
            "steps": {"avg": 3200, "spread": 800, "count": 1},
            "active_calories": {"avg": 180, "spread": 30, "count": 1},
            "resting_energy": {"avg": 1680, "spread": 20, "count": 1},
            "distance": {"avg": 2.4, "spread": 0.5, "count": 1},
            "workout": {"avg": 0, "spread": 0, "count": 0},
            "sleep": {"avg": 5.2, "spread": 0.5, "count": 1},
            "sleep_deep": {"avg": 0.6, "spread": 0.2, "count": 1},
            "sleep_rem": {"avg": 0.8, "spread": 0.2, "count": 1},
            "stand_time": {"avg": 15, "spread": 5, "count": 1},
            "mindful_minutes": {"avg": 0, "spread": 0, "count": 0},
            "walking_hr_avg": {"avg": 110, "spread": 8, "count": 4},
            "audio_exposure": {"avg": 78, "spread": 10, "count": 4},
            "exercise_time": {"avg": 5, "spread": 3, "count": 1},
        },
    },
    "athlete": {
        "description": "Very active athlete, excellent vitals, lots of exercise",
        "metrics": {
            "heart_rate": {"avg": 62, "spread": 15, "count": 24},
            "resting_hr": {"avg": 48, "spread": 2, "count": 4},
            "hrv": {"avg": 72, "spread": 10, "count": 6},
            "spo2": {"avg": 99, "spread": 0.5, "count": 6},
            "respiratory_rate": {"avg": 12, "spread": 1, "count": 4},
            "wrist_temperature": {"avg": 0.0, "spread": 0.1, "count": 2},
            "vo2_max": {"avg": 52, "spread": 0, "count": 1},
            "steps": {"avg": 14000, "spread": 2000, "count": 1},
            "active_calories": {"avg": 750, "spread": 80, "count": 1},
            "resting_energy": {"avg": 1720, "spread": 20, "count": 1},
            "distance": {"avg": 11.5, "spread": 1.5, "count": 1},
            "workout": {"avg": 75, "spread": 15, "count": 2},
            "sleep": {"avg": 8.2, "spread": 0.3, "count": 1},
            "sleep_deep": {"avg": 2.0, "spread": 0.2, "count": 1},
            "sleep_rem": {"avg": 2.1, "spread": 0.2, "count": 1},
            "stand_time": {"avg": 60, "spread": 10, "count": 1},
            "mindful_minutes": {"avg": 15, "spread": 5, "count": 1},
            "walking_hr_avg": {"avg": 85, "spread": 5, "count": 4},
            "audio_exposure": {"avg": 58, "spread": 5, "count": 4},
            "exercise_time": {"avg": 65, "spread": 15, "count": 1},
        },
    },
    "sleep_deprived": {
        "description": "Sleep-deprived, otherwise OK, fatigue building up",
        "metrics": {
            "heart_rate": {"avg": 75, "spread": 10, "count": 24},
            "resting_hr": {"avg": 68, "spread": 4, "count": 4},
            "hrv": {"avg": 30, "spread": 6, "count": 6},
            "spo2": {"avg": 96, "spread": 1, "count": 6},
            "respiratory_rate": {"avg": 16, "spread": 2, "count": 4},
            "wrist_temperature": {"avg": 0.3, "spread": 0.2, "count": 2},
            "vo2_max": {"avg": 41, "spread": 0, "count": 1},
            "steps": {"avg": 6000, "spread": 1000, "count": 1},
            "active_calories": {"avg": 280, "spread": 40, "count": 1},
            "resting_energy": {"avg": 1660, "spread": 20, "count": 1},
            "distance": {"avg": 4.5, "spread": 0.8, "count": 1},
            "workout": {"avg": 20, "spread": 5, "count": 1},
            "sleep": {"avg": 4.1, "spread": 0.4, "count": 1},
            "sleep_deep": {"avg": 0.4, "spread": 0.1, "count": 1},
            "sleep_rem": {"avg": 0.5, "spread": 0.1, "count": 1},
            "stand_time": {"avg": 25, "spread": 8, "count": 1},
            "mindful_minutes": {"avg": 0, "spread": 0, "count": 0},
            "walking_hr_avg": {"avg": 102, "spread": 6, "count": 4},
            "audio_exposure": {"avg": 65, "spread": 8, "count": 4},
            "exercise_time": {"avg": 15, "spread": 5, "count": 1},
        },
    },
}


def generate_metrics(scenario: str) -> list[dict]:
    """Generate a list of health metrics for a given scenario."""
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario!r}. Choose from: {list(SCENARIOS.keys())}")

    config = SCENARIOS[scenario]
    metrics = []
    now = datetime.now(UTC)

    for metric_name, params in config["metrics"].items():
        count = params["count"]
        if count == 0:
            continue
        for i in range(count):
            value = params["avg"] + random.uniform(-params["spread"], params["spread"])
            value = round(max(0, value), 1)
            recorded_at = (now - timedelta(hours=random.uniform(0, 24))).isoformat()
            metrics.append(
                {
                    "metric": metric_name,
                    "value": value,
                    "recorded_at": recorded_at,
                }
            )

    return metrics


def main():
    """Seed the database with a chosen scenario."""
    import sys

    from backend.health_store import init_db, insert_metrics

    scenario = sys.argv[1] if len(sys.argv) > 1 else "healthy"
    print(f"Seeding scenario: {scenario} — {SCENARIOS[scenario]['description']}")

    init_db()
    metrics = generate_metrics(scenario)
    count = insert_metrics(metrics)
    print(f"Inserted {count} data points.")


if __name__ == "__main__":
    main()
