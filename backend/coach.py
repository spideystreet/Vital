"""Morning brief orchestrator for V.I.T.A.L.

Reads recent biometrics from Thryve and the user's persistent memory,
asks the LLM to compose a structured brief (diagnosis + memory callback +
adaptive protocol + one question), and writes the brief back to memory.

This is the Surface 1 entry point — called by the daily cron or the
"Start my day" button in the web UI.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, date

from mistralai.client import Mistral

from backend import memory
from backend.brain import PatientContext, SessionData, prefetch_session
from backend.config import LLM_MODEL

log = logging.getLogger(__name__)


@dataclass
class BriefPayload:
    """Structured morning brief returned to the frontend.

    Fields are displayed as separate cards in the UI; `raw_text` is what
    Voxtral TTS speaks.
    """

    diagnosis: str
    memory_callback: str
    protocol: str
    question: str
    raw_text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DashboardStat:
    """A single stat card on the dashboard: value + delta + LLM insight."""

    metric: str
    value: float
    unit: str
    delta_pct: float
    insight: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChallengeProgress:
    """Live snapshot of the user's active personalized challenge."""

    title: str
    metric: str
    target: int
    current: float
    unit: str
    progress_pct: float
    reason: str
    date: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DashboardPayload:
    """Response for GET /api/dashboard/{patient_id}."""

    stats: list[DashboardStat]
    generated_at: str
    challenge: ChallengeProgress | None = None

    def to_dict(self) -> dict:
        return {
            "stats": [s.to_dict() for s in self.stats],
            "generated_at": self.generated_at,
            "challenge": self.challenge.to_dict() if self.challenge else None,
        }


# Friendly unit labels for challenge metrics.
_CHALLENGE_UNITS: dict[str, str] = {
    "steps": "pas",
}


def _build_challenge_progress(
    patient: PatientContext,
    session: SessionData,
) -> ChallengeProgress | None:
    """Read the active challenge from memory and compute live progress.

    Returns None if the user has no active challenge or the challenge's
    metric is missing from the current session's vitals snapshot.
    """
    active = memory.read_active_challenge(patient.token)
    if active is None:
        return None

    metric = active["metric"]
    values = (session.vitals or {}).get(metric, [])
    nums = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
    current = float(nums[-1]) if nums else 0.0

    target = int(active["target"])
    progress_pct = (
        round(min(100.0, 100.0 * current / target), 1) if target > 0 else 0.0
    )

    return ChallengeProgress(
        title=active["title"],
        metric=metric,
        target=target,
        current=current,
        unit=_CHALLENGE_UNITS.get(metric, metric),
        progress_pct=progress_pct,
        reason=active["reason"],
        date=active["date"],
    )


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_BRIEF_SYSTEM_TEMPLATE = """\
Tu es V.I.T.A.L, un coach de vie proactif base sur les donnees sante de l'utilisateur.
Tu produis le BRIEF DU MATIN : un diagnostic court, un rappel de la memoire personnelle \
de l'utilisateur, un protocole adaptatif pour aujourd'hui, et UNE question pour cloturer.

PROFIL :
- Nom : {name}
- Age : {age}

MEMOIRE PERSISTANTE (lis tout, cite ce qui est pertinent) :
{memory_blob}

BIOMETRIQUES (dernier releve) :
{biometrics}

FORMAT DE SORTIE (JSON strict, pas de markdown) :
{{
  "diagnosis": "une phrase, 1-2 chiffres cles",
  "memory_callback": "une phrase qui reference un evenement ou un protocole passe \
de la section Events ou Protocols. Si la memoire ne contient rien de pertinent, \
ecris 'Premier brief — je commence a apprendre ton rythme.'",
  "protocol": "UNE action concrete pour aujourd'hui, adaptee a l'etat actuel",
  "question": "UNE question fermee pour capter l'intention de l'utilisateur",
  "raw_text": "le brief entier a lire a voix haute (3-4 phrases), sans markdown"
}}

REGLES STRICTES :
- JAMAIS de diagnostic medical. Si le signal est grave, recommande un professionnel.
- Le callback memoire doit citer un element REEL de la memoire si elle en contient un.
- raw_text doit etre conversationnel, pas une liste a puces.
- Reponds uniquement le JSON, rien d'autre.
"""


def _format_biometrics(session: SessionData) -> str:
    """Summarize cached vitals as a compact string for the prompt."""
    if not session.vitals:
        return "(pas de donnees biometriques disponibles)"

    lines: list[str] = []
    for metric, values in session.vitals.items():
        nums = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
        if not nums:
            continue
        lines.append(f"- {metric}: dernier={nums[-1]}, moy7j={round(sum(nums)/len(nums), 1)}")
    return "\n".join(lines) if lines else "(pas de donnees biometriques disponibles)"


def _build_brief_prompt(patient: PatientContext, session: SessionData) -> list[dict]:
    """Build the system + user message pair sent to the LLM for the morning brief."""
    memory_blob = memory.read_all(patient.token)
    biometrics = _format_biometrics(session)

    system_content = _BRIEF_SYSTEM_TEMPLATE.format(
        name=patient.name,
        age=patient.age or "?",
        memory_blob=memory_blob,
        biometrics=biometrics,
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "Genere le brief du matin."},
    ]


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def generate_morning_brief(
    client: Mistral,
    patient: PatientContext,
) -> BriefPayload:
    """Produce the morning brief and write it back to memory."""
    memory.ensure_memory_file(patient.token)

    session = SessionData()
    try:
        await prefetch_session(patient, session)
    except Exception:
        log.exception("prefetch_session failed during morning brief")

    messages = _build_brief_prompt(patient, session)

    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
    except Exception:
        log.exception("LLM call failed during morning brief")
        return BriefPayload(
            diagnosis="Je n'arrive pas a lire tes donnees ce matin.",
            memory_callback="",
            protocol="Prends 5 minutes pour te poser et respirer.",
            question="Comment te sens-tu ce matin ?",
            raw_text=(
                "Bonjour, je n'arrive pas a me connecter a tes donnees ce matin. "
                "Prends 5 minutes pour te poser et respirer. Comment te sens-tu ?"
            ),
        )

    raw_content = response.choices[0].message.content
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        log.error("Brief JSON parse failed, raw=%s", raw_content)
        return BriefPayload(
            diagnosis="Brief genere mais illisible.",
            memory_callback="",
            protocol="Relance ton brief dans un instant.",
            question="",
            raw_text=raw_content[:400],
        )

    payload = BriefPayload(
        diagnosis=parsed.get("diagnosis", ""),
        memory_callback=parsed.get("memory_callback", ""),
        protocol=parsed.get("protocol", ""),
        question=parsed.get("question", ""),
        raw_text=parsed.get("raw_text", ""),
    )

    today = date.today().isoformat()
    memory.append_entry(
        patient.token,
        memory.SECTION_EVENTS,
        f"{today}: morning_brief — {payload.diagnosis}",
    )
    if payload.protocol:
        memory.append_entry(
            patient.token,
            memory.SECTION_PROTOCOLS,
            f"{today}: proposed — {payload.protocol} — status: pending",
        )

    return payload


# ---------------------------------------------------------------------------
# User reply handler
# ---------------------------------------------------------------------------

_AFFIRMATIVE_MARKERS = ["ok", "oui", "yes", "d'accord", "carrement", "ça marche"]
_NEGATIVE_MARKERS = ["non", "no", "pas aujourd'hui", "trop", "impossible"]


def _classify_reply(reply: str) -> str:
    """Rough classification of the user's reply to the brief."""
    r = reply.lower()
    if any(m in r for m in _AFFIRMATIVE_MARKERS):
        return "accepted"
    if any(m in r for m in _NEGATIVE_MARKERS):
        return "rejected"
    return "unclear"


async def record_user_reply(patient: PatientContext, reply: str) -> None:
    """Append the user's morning-brief reply to Context and update the pending protocol."""
    today = date.today().isoformat()

    memory.append_entry(
        patient.token,
        memory.SECTION_CONTEXT,
        f"{today}: reply — {reply.strip()}",
    )

    outcome = _classify_reply(reply)
    if outcome == "unclear":
        return

    path = memory.ensure_memory_file(patient.token)
    content = path.read_text()

    marker = f"## {memory.SECTION_PROTOCOLS}"
    start = content.find(marker)
    if start == -1:
        return
    body_start = start + len(marker)
    next_header = content.find("\n## ", body_start)
    body_end = next_header if next_header != -1 else len(content)

    body = content[body_start:body_end]
    replaced_once = body.rsplit("status: pending", 1)
    if len(replaced_once) == 2:
        new_body = f"status: {outcome}".join(replaced_once)
        path.write_text(content[:body_start] + new_body + content[body_end:])


# ---------------------------------------------------------------------------
# Dashboard insights (Surface 2)
# ---------------------------------------------------------------------------

# Watched metrics for the dashboard, with their display units.
DASHBOARD_METRICS: list[tuple[str, str]] = [
    ("hrv", "ms"),
    ("resting_hr", "bpm"),
    ("sleep_quality", "/100"),
]


def _parse_baseline_mean(user_id: str, metric: str) -> float | None:
    """Parse the Baselines section and return the mean for `metric`, or None."""
    import re

    baselines = memory.read_section(user_id, memory.SECTION_BASELINES)
    if not baselines:
        return None
    pattern = re.compile(rf"{re.escape(metric)}:\s*mean=([0-9.]+)")
    match = pattern.search(baselines)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _compute_delta_pct(user_id: str, metric: str, current: float) -> float:
    """Return the signed percentage change of `current` vs the stored baseline mean.

    Returns 0.0 if no baseline exists for the metric.
    """
    mean = _parse_baseline_mean(user_id, metric)
    if mean is None or mean == 0:
        return 0.0
    return round(((current - mean) / mean) * 100, 1)


_DASHBOARD_SYSTEM_TEMPLATE = """\
Tu es V.I.T.A.L. Tu composes des PHRASES D'INSIGHT pour chaque statistique affichee \
sur le dashboard de l'utilisateur. Chaque phrase doit etre COURTE (1 phrase, max ~20 mots), \
ancree dans la memoire personnelle de l'utilisateur, et utiliser sa baseline personnelle \
au lieu de normes generales.

MEMOIRE :
{memory_blob}

STATS ACTUELLES :
{stats_block}

FORMAT DE SORTIE (JSON strict) :
Un objet avec une cle par metrique listee ci-dessus, chaque valeur etant la phrase d'insight. \
Exemple :
{{"hrv": "14% sous ta moyenne 14 jours, meme pattern que le 21 mars",
  "resting_hr": "dans ta zone habituelle",
  "sleep_quality": "nuit courte, probablement liee a la HRV basse"}}

REGLES :
- Pas de diagnostic medical.
- Cite la memoire quand elle contient un evenement lie a la metrique.
- Phrases courtes, conversationnelles, pas de markdown.
- Reponds uniquement le JSON.
"""


def _build_dashboard_prompt(
    patient: PatientContext,
    stats_snapshot: list[tuple[str, float, float]],
) -> list[dict]:
    """Build the LLM prompt that returns one insight per watched metric."""
    memory_blob = memory.read_all(patient.token)
    stats_block = "\n".join(
        f"- {metric}: {value} (delta vs baseline: {delta:+.1f}%)"
        for metric, value, delta in stats_snapshot
    )
    system_content = _DASHBOARD_SYSTEM_TEMPLATE.format(
        memory_blob=memory_blob,
        stats_block=stats_block,
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "Genere les insights du dashboard."},
    ]


async def generate_dashboard(
    client: Mistral,
    patient: PatientContext,
) -> DashboardPayload:
    """Build the dashboard payload for Surface 2's landing view."""
    from datetime import datetime

    memory.ensure_memory_file(patient.token)

    session = SessionData()
    try:
        await prefetch_session(patient, session)
    except Exception:
        log.exception("prefetch_session failed during dashboard generation")

    stats_snapshot: list[tuple[str, float, float]] = []
    latest_values: dict[str, float] = {}
    for metric, _unit in DASHBOARD_METRICS:
        values = (session.vitals or {}).get(metric, [])
        nums = [v["value"] for v in values if isinstance(v.get("value"), (int, float))]
        if not nums:
            continue
        current = float(nums[-1])
        delta = _compute_delta_pct(patient.token, metric, current)
        latest_values[metric] = current
        stats_snapshot.append((metric, current, delta))

    if not stats_snapshot:
        return DashboardPayload(
            stats=[],
            generated_at=datetime.now(UTC).isoformat(),
        )

    messages = _build_dashboard_prompt(patient, stats_snapshot)

    insights: dict[str, str] = {}
    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
        )
        insights = json.loads(response.choices[0].message.content)
    except Exception:
        log.exception("Dashboard insight LLM call failed")

    stats: list[DashboardStat] = []
    for metric, unit in DASHBOARD_METRICS:
        if metric not in latest_values:
            continue
        current = latest_values[metric]
        delta = _compute_delta_pct(patient.token, metric, current)
        stats.append(
            DashboardStat(
                metric=metric,
                value=current,
                unit=unit,
                delta_pct=delta,
                insight=insights.get(metric, ""),
            )
        )

    challenge = _build_challenge_progress(patient, session)

    return DashboardPayload(
        stats=stats,
        generated_at=datetime.now(UTC).isoformat(),
        challenge=challenge,
    )
