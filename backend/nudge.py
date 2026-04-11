"""Memory-driven biometric nudge detector.

Reads the user's personal baseline from backend.memory, compares the latest
biometric values to it via z-score, and fires a personalized notification
when a deviation crosses the threshold. Every fired event is appended to
memory so the morning brief and chat can reference it.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import date

from mistralai.client import Mistral

from backend import memory
from backend.brain import PatientContext
from backend.config import LLM_MODEL
from backend.thryve import ThryveClient

log = logging.getLogger(__name__)

Z_THRESHOLD = 2.0
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


def _parse_baseline_line(line: str) -> dict | None:
    """Parse 'hrv: mean=51.1 stddev=2.3 n=7 window=7d'."""
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


def _load_baseline(user_id: str, metric: str) -> dict | None:
    """Return the parsed baseline dict for a metric, or None."""
    body = memory.read_section(user_id, memory.SECTION_BASELINES)
    for line in body.splitlines():
        parsed = _parse_baseline_line(line)
        if parsed and parsed["metric"] == metric:
            return parsed
    return None


def _deviation_check(user_id: str, metric: str, current: float) -> dict | None:
    """Z-score check against the stored baseline."""
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
            body=(
                f"{deviation['metric']} a {deviation['current']} — "
                "ouvre l'app pour plus de contexte."
            ),
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


async def evaluate(
    client: Mistral,
    patient: PatientContext,
) -> list[NudgeMessage]:
    """Scan watched metrics for the patient and return any fired notifications."""
    memory.ensure_memory_file(patient.token)

    thryve = ThryveClient()
    try:
        vitals = await thryve.get_vitals(patient.token, days=1)
    except Exception:
        log.exception("Thryve fetch failed during nudge evaluate")
        return []

    messages: list[NudgeMessage] = []
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
) -> NudgeMessage | None:
    """Manually fire a notification for demo — used by /dev/fire-notification."""
    memory.ensure_memory_file(patient.token)

    deviation = _deviation_check(patient.token, metric, current)
    if deviation is None:
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

    today = date.today().isoformat()
    memory.append_entry(
        patient.token,
        memory.SECTION_EVENTS,
        f"{today}: nudge (manual) {metric}={current} — {message.headline}",
    )
    return message


if __name__ == "__main__":
    print("nudge.py is now library-only — use the /dev/fire-notification endpoint.")
