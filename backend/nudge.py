"""Daily nudge detector: scans biometrics and decides whether to alert the user.

Run periodically (e.g. via cron). Triggers a notification only when stress
signals warrant attention — never on a schedule. The reward (Alan Play berries)
is granted only if the user accepts the nudge, so engagement tracks need, not
compliance.
"""

from dataclasses import dataclass

from backend.burnout import compute_burnout
from backend.thryve import ThryveClient

# Thresholds — keep aligned with brain.py system prompt
HRV_DROP_PCT = -15.0
SLEEP_MIN_QUALITY = 60.0
RESTING_HR_MAX = 80.0


@dataclass
class NudgeDecision:
    should_nudge: bool
    reasons: list[str]
    headline: str

    def to_dict(self) -> dict:
        return {
            "should_nudge": self.should_nudge,
            "reasons": self.reasons,
            "headline": self.headline,
        }


async def evaluate(patient_token: str) -> NudgeDecision:
    """Decide whether to send a daily nudge based on recent Thryve data."""
    client = ThryveClient()
    metrics = await client.get_burnout_metrics(patient_token, days=7)
    reasons: list[str] = []

    # --- HRV drop check ---
    hrv = metrics.get("hrv")
    if hrv and hrv["baseline_7d"] and hrv["latest"] is not None:
        baseline = hrv["baseline_7d"]
        if baseline > 0:
            change_pct = ((hrv["latest"] - baseline) / baseline) * 100
            if change_pct <= HRV_DROP_PCT:
                reasons.append(f"HRV en baisse ({change_pct:.0f}%)")

    # --- Sleep quality check ---
    sleep = metrics.get("sleep_quality")
    if sleep and sleep["latest"] is not None:
        if sleep["latest"] < SLEEP_MIN_QUALITY:
            reasons.append(f"Qualité de sommeil faible ({sleep['latest']:.0f}/100)")

    # --- Resting HR check ---
    rhr = metrics.get("resting_hr")
    if rhr and rhr["latest"] is not None:
        if rhr["latest"] > RESTING_HR_MAX:
            reasons.append(f"FC repos élevée ({rhr['latest']:.0f} bpm)")

    if not reasons:
        return NudgeDecision(
            should_nudge=False,
            reasons=[],
            headline="Tout est dans le vert, pas besoin de check aujourd'hui.",
        )

    # Compute burnout score for context
    burnout = compute_burnout(metrics)

    headline = f"V.I.T.A.L a remarqué un truc (score {burnout.score}), 30 secondes ?"
    return NudgeDecision(should_nudge=True, reasons=reasons, headline=headline)


def main() -> None:
    """CLI entry: print the nudge decision as JSON for cron / shortcut hooks."""
    import asyncio
    import json
    import os

    token = os.environ.get("THRYVE_PATIENT_TOKEN", "")
    if not token:
        print('{"error": "THRYVE_PATIENT_TOKEN not set"}')
        return

    decision = asyncio.run(evaluate(token))
    print(json.dumps(decision.to_dict(), ensure_ascii=False))


if __name__ == "__main__":
    main()
