"""Seed the health database with realistic mock data.

Simulates 7 days of Apple Watch data for a healthy, active 25-year-old.
Plants a subtle issue in recent nights for LLM detection testing.

Usage: uv run python scripts/seed_health_data.py [--url http://localhost:8420]
"""

import argparse
import random
from datetime import UTC, datetime, timedelta

import httpx


def generate_metrics(days: int = 7) -> list[dict]:
    """Generate realistic health data for a healthy 25-year-old.

    Hidden issue: SpO2 dips during sleep in the last 3 nights (92-94%)
    and deep sleep declining — subtle sleep apnea pattern.
    """
    now = datetime.now(UTC)
    metrics = []
    hours = days * 24

    for h in range(hours, 0, -1):
        t = now - timedelta(hours=h)
        ts = t.isoformat()
        hour_of_day = t.hour
        days_ago = h / 24

        # --- Heart rate ---
        if 0 <= hour_of_day < 6:
            hr = random.gauss(54, 3)
        elif 6 <= hour_of_day < 8:
            hr = random.gauss(65, 5)
        elif 8 <= hour_of_day < 12:
            hr = random.gauss(72, 6)
        elif 12 <= hour_of_day < 14:
            hr = random.gauss(78, 5)
        elif 17 <= hour_of_day < 19:
            hr = random.gauss(135, 20)
        else:
            hr = random.gauss(68, 6)
        metrics.append(
            {
                "metric": "heart_rate",
                "value": round(max(42, hr), 1),
                "recorded_at": ts,
            }
        )

        # --- SpO2 ---
        # THE PLANTED ISSUE: nocturnal dips in the last 3 nights
        if 0 <= hour_of_day < 6 and days_ago <= 3:
            spo2 = random.gauss(93.0, 0.8)
        else:
            spo2 = random.gauss(98.2, 0.5)
        metrics.append(
            {
                "metric": "spo2",
                "value": round(max(88, min(100, spo2)), 1),
                "recorded_at": ts,
            }
        )

        # --- HRV ---
        if 0 <= hour_of_day < 6:
            hrv = random.gauss(65, 10)
        elif 17 <= hour_of_day < 19:
            hrv = random.gauss(35, 8)
        else:
            hrv = random.gauss(52, 10)
        metrics.append(
            {
                "metric": "hrv",
                "value": round(max(15, hrv), 1),
                "recorded_at": ts,
            }
        )

        # --- Respiratory rate ---
        if 0 <= hour_of_day < 6:
            rr = random.gauss(14, 1.5)
        else:
            rr = random.gauss(16, 2)
        metrics.append(
            {
                "metric": "respiratory_rate",
                "value": round(max(8, rr), 1),
                "recorded_at": ts,
            }
        )

        # --- Wrist temperature (deviation from baseline in C) ---
        temp_dev = random.gauss(0.0, 0.15)
        metrics.append(
            {
                "metric": "wrist_temperature",
                "value": round(temp_dev, 2),
                "recorded_at": ts,
            }
        )

    # --- Steps (hourly accumulation, per day) ---
    for day in range(days, 0, -1):
        total_steps = 0
        for hour in range(24):
            t = now - timedelta(days=day) + timedelta(hours=hour)
            ts = t.isoformat()
            if 0 <= hour < 7:
                steps = random.randint(0, 10)
            elif 7 <= hour < 9:
                steps = random.randint(800, 1500)
            elif 12 <= hour < 13:
                steps = random.randint(500, 1200)
            elif 17 <= hour < 19:
                steps = random.randint(2000, 4000)
            else:
                steps = random.randint(100, 500)
            total_steps += steps
            metrics.append(
                {
                    "metric": "steps",
                    "value": total_steps,
                    "recorded_at": ts,
                }
            )

    # --- Daily metrics (one per day, including today) ---
    for day in range(days, -1, -1):
        t_morning = (now - timedelta(days=day)).replace(hour=7, minute=30)
        if t_morning > now:
            continue
        ts_morning = t_morning.isoformat()
        days_ago = day

        # Resting HR
        metrics.append(
            {
                "metric": "resting_hr",
                "value": round(random.gauss(58, 2), 1),
                "recorded_at": ts_morning,
            }
        )

        # Active calories (end of day — skip if today isn't over)
        t_eod = (now - timedelta(days=day)).replace(hour=23)
        if t_eod <= now:
            metrics.append(
                {
                    "metric": "active_calories",
                    "value": round(random.gauss(520, 80)),
                    "recorded_at": t_eod.isoformat(),
                }
            )

            # Distance
            metrics.append(
                {
                    "metric": "distance",
                    "value": round(random.gauss(8.5, 1.5), 1),
                    "recorded_at": t_eod.isoformat(),
                }
            )

        # Sleep total
        sleep_h = round(random.gauss(7.8, 0.5), 1)
        metrics.append(
            {
                "metric": "sleep",
                "value": max(5.0, min(9.5, sleep_h)),
                "recorded_at": ts_morning,
            }
        )

        # Deep sleep — THE PLANTED ISSUE: declining in last 3 days
        if days_ago <= 3:
            deep = round(random.gauss(0.8, 0.15), 1)
        else:
            deep = round(random.gauss(1.6, 0.2), 1)
        metrics.append(
            {
                "metric": "sleep_deep",
                "value": max(0.3, deep),
                "recorded_at": ts_morning,
            }
        )

        # REM sleep
        rem = round(random.gauss(1.8, 0.3), 1)
        metrics.append(
            {
                "metric": "sleep_rem",
                "value": max(0.5, rem),
                "recorded_at": ts_morning,
            }
        )

    return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Seed V.I.T.A.L with mock health data",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8420",
        help="Server base URL",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Days of data to generate",
    )
    args = parser.parse_args()

    metrics = generate_metrics(args.days)
    print(f"Generated {len(metrics)} data points over {args.days} days")

    resp = httpx.post(f"{args.url}/health", json={"metrics": metrics})
    resp.raise_for_status()
    print(f"Server response: {resp.json()}")

    summary = httpx.get(f"{args.url}/health/summary?hours=168").json()
    print("\n--- Health Summary (7 days) ---")
    for metric, stats in summary.items():
        unit = stats.get("unit", "")
        print(
            f"  {metric}: latest={stats['latest']} {unit}"
            f" (avg={stats['avg']}, range={stats['min']}"
            f"-{stats['max']}, n={stats['count']})"
        )


if __name__ == "__main__":
    main()
