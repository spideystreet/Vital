"""Free-speech vocal intake for new patients.

Unlike `onboarding.py` (rigid Q&A flow), this module lets the user speak
freely while an LLM extracts known fields from each utterance and fills a
5-category health form progressively. Used by the demo "new patient" flow:
the frontend opens a page, the user talks, the form fills as they speak.

Sessions are kept in a module-level dict keyed by session_id (hackathon
single-process demo). The final form is written back to the patient's
markdown memory file via `finalize`.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from mistralai.client import Mistral

from backend import memory
from backend.config import LLM_MODEL

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Form schema — 5 categories, 15 fields
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntakeField:
    key: str
    label_fr: str
    type: str  # "integer" | "string" | "enum" | "boolean" | "scale_1_10"
    enum_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntakeCategory:
    key: str
    label_fr: str
    fields: tuple[IntakeField, ...]


INTAKE_SCHEMA: tuple[IntakeCategory, ...] = (
    IntakeCategory(
        "identity",
        "Identité",
        (
            IntakeField("age", "Âge", "integer"),
            IntakeField("sex", "Sexe", "enum", ("male", "female", "other")),
            IntakeField("weight_kg", "Poids (kg)", "integer"),
            IntakeField("height_cm", "Taille (cm)", "integer"),
            IntakeField("job", "Métier", "string"),
        ),
    ),
    IntakeCategory(
        "lifestyle",
        "Mode de vie",
        (
            IntakeField("weekly_endurance_hours", "Heures d'endurance par semaine", "integer"),
            IntakeField("sitting_hours_per_day", "Heures assis par jour", "integer"),
            IntakeField("smoker", "Fumeur", "boolean"),
            IntakeField(
                "alcohol_frequency",
                "Fréquence alcool",
                "enum",
                ("never", "rarely", "weekly", "several_per_week", "daily"),
            ),
        ),
    ),
    IntakeCategory(
        "sleep",
        "Sommeil",
        (
            IntakeField("avg_sleep_hours", "Heures de sommeil par nuit", "integer"),
            IntakeField("sleep_satisfaction", "Satisfaction sommeil (1-10)", "scale_1_10"),
        ),
    ),
    IntakeCategory(
        "mental",
        "Mental",
        (
            IntakeField("dominant_emotion_30d", "Émotion dominante 30 derniers jours", "string"),
            IntakeField(
                "work_mental_impact", "Impact du travail sur le mental (1-10)", "scale_1_10"
            ),
        ),
    ),
    IntakeCategory(
        "medical",
        "Médical",
        (
            IntakeField("family_cvd", "Antécédents cardiovasculaires familiaux", "boolean"),
            IntakeField("current_medications", "Médicaments actuels", "string"),
        ),
    ),
)


_FIELD_BY_KEY: dict[str, IntakeField] = {
    f.key: f for cat in INTAKE_SCHEMA for f in cat.fields
}

# Fields that belong to the Baselines section of the memory file.
# Everything else goes to Context.
_BASELINE_FIELDS: frozenset[str] = frozenset(
    {
        "age",
        "sex",
        "weight_kg",
        "height_cm",
        "job",
        "weekly_endurance_hours",
        "avg_sleep_hours",
    }
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


@dataclass
class IntakeSession:
    session_id: str
    patient_id: str
    values: dict[str, Any] = field(default_factory=dict)
    transcripts: list[str] = field(default_factory=list)


_SESSIONS: dict[str, IntakeSession] = {}


def schema_to_dict() -> list[dict]:
    """Return the static form schema (no values) as JSON-friendly dicts."""
    return [
        {
            "key": cat.key,
            "label_fr": cat.label_fr,
            "fields": [
                {
                    "key": f.key,
                    "label_fr": f.label_fr,
                    "type": f.type,
                    "enum_values": list(f.enum_values),
                }
                for f in cat.fields
            ],
        }
        for cat in INTAKE_SCHEMA
    ]


def form_state(session: IntakeSession) -> dict:
    """Return the full form grouped by category, with current values."""
    return {
        "session_id": session.session_id,
        "patient_id": session.patient_id,
        "categories": [
            {
                "key": cat.key,
                "label_fr": cat.label_fr,
                "fields": [
                    {
                        "key": f.key,
                        "label_fr": f.label_fr,
                        "type": f.type,
                        "enum_values": list(f.enum_values),
                        "value": session.values.get(f.key),
                    }
                    for f in cat.fields
                ],
            }
            for cat in INTAKE_SCHEMA
        ],
        "progress": {
            "filled": len(session.values),
            "total": len(_FIELD_BY_KEY),
        },
    }


def start(patient_id: str) -> IntakeSession:
    """Open a new intake session for a patient. Resets any prior session."""
    session_id = str(uuid.uuid4())
    sess = IntakeSession(session_id=session_id, patient_id=patient_id)
    _SESSIONS[session_id] = sess
    return sess


def get(session_id: str) -> IntakeSession | None:
    return _SESSIONS.get(session_id)


# ---------------------------------------------------------------------------
# LLM extraction
# ---------------------------------------------------------------------------


_EXTRACTION_SYSTEM = """Tu extrais des donnees de sante depuis une phrase libre de l'utilisateur.

Reponds avec un JSON contenant UNIQUEMENT les cles explicitement mentionnees
dans la phrase. N'invente rien, n'ajoute aucune cle qui n'est pas clairement
evoquee.

Champs attendus :
{fields_doc}

REGLES :
- "32 ans" -> age=32
- "1m80" ou "un metre quatre vingt" -> height_cm=180
- "75 kilos" -> weight_kg=75
- Pour un enum, renvoie EXACTEMENT une des valeurs de la liste.
- Pour les scales 1-10, renvoie un entier entre 1 et 10.
- Pour les booleens, renvoie true ou false.
- Si un champ n'est pas evoque, ne l'inclus PAS.
- Reponds uniquement le JSON, rien d'autre.
"""


def _fields_doc() -> str:
    lines: list[str] = []
    for cat in INTAKE_SCHEMA:
        for f in cat.fields:
            line = f"- {f.key} ({f.type})"
            if f.enum_values:
                line += f" in [{', '.join(f.enum_values)}]"
            line += f" : {f.label_fr}"
            lines.append(line)
    return "\n".join(lines)


def _coerce(fld: IntakeField, val: Any) -> Any:
    """Convert a raw LLM value to the field's declared type, or None."""
    try:
        if fld.type == "integer":
            return int(float(val))
        if fld.type == "scale_1_10":
            return max(1, min(10, int(float(val))))
        if fld.type == "boolean":
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            return str(val).strip().lower() in ("true", "yes", "oui", "1")
        if fld.type == "enum":
            v = str(val).strip().lower()
            return v if v in fld.enum_values else None
        if fld.type == "string":
            s = str(val).strip()
            return s if s else None
    except (TypeError, ValueError):
        return None
    return None


def extract_fields(client: Mistral, transcript: str) -> dict[str, Any]:
    """Ask the LLM to extract known fields from a free-speech utterance."""
    if not transcript.strip():
        return {}

    system = _EXTRACTION_SYSTEM.format(fields_doc=_fields_doc())
    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": transcript},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
    except Exception:
        log.exception("vocal intake extraction failed")
        return {}

    if not isinstance(parsed, dict):
        return {}

    cleaned: dict[str, Any] = {}
    for key, raw in parsed.items():
        if key not in _FIELD_BY_KEY or raw is None:
            continue
        coerced = _coerce(_FIELD_BY_KEY[key], raw)
        if coerced is not None:
            cleaned[key] = coerced
    return cleaned


def ingest(session: IntakeSession, client: Mistral, transcript: str) -> dict:
    """Extract fields from a transcript, merge into session, return updated state."""
    transcript = (transcript or "").strip()
    new_fields: dict[str, Any] = {}
    if transcript:
        session.transcripts.append(transcript)
        new_fields = extract_fields(client, transcript)
        session.values.update(new_fields)
    return {
        "transcript": transcript,
        "new_fields": new_fields,
        "form": form_state(session),
    }


# ---------------------------------------------------------------------------
# Finalize
# ---------------------------------------------------------------------------


def finalize(session_id: str) -> dict:
    """Write extracted values to the patient's memory file and close the session."""
    session = _SESSIONS.get(session_id)
    if session is None:
        raise RuntimeError(f"no active intake session: {session_id}")

    memory.ensure_memory_file(session.patient_id)
    for key, val in session.values.items():
        section = (
            memory.SECTION_BASELINES if key in _BASELINE_FIELDS else memory.SECTION_CONTEXT
        )
        memory.append_entry(session.patient_id, section, f"{key}: {val}")

    result = {
        "ok": True,
        "patient_id": session.patient_id,
        "fields_saved": len(session.values),
        "memory_file": f"data/memory/{session.patient_id}.md",
    }
    del _SESSIONS[session_id]
    log.info(
        "vocal_intake.finalized session=%s patient=%s fields=%d",
        session_id,
        session.patient_id,
        result["fields_saved"],
    )
    return result
