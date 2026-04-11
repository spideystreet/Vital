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
from datetime import date

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
