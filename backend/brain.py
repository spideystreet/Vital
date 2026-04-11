"""LLM reasoning with Thryve health context and 9-tool function calling."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from statistics import mean

from mistralai.client import Mistral

from backend import memory
from backend.burnout import BurnoutResult, compute_burnout
from backend.config import LLM_MODEL
from backend.thryve import METRIC_CODES, ThryveClient

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patient & session data holders
# ---------------------------------------------------------------------------


@dataclass
class PatientContext:
    """Identifies the patient for the current conversation."""

    token: str  # Thryve auth token
    name: str
    age: int | None = None


@dataclass
class SessionData:
    """Cached health data fetched once per session to avoid redundant API calls."""

    vitals: dict | None = None
    blood_panel: dict | None = None
    burnout: BurnoutResult | None = None
    user_info: dict | None = None


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_TEMPLATE = """\
Tu es V.I.T.A.L, un coach bien-etre vocal specialise dans la prevention du stress \
et du burnout. Tu analyses les donnees de sante de l'utilisateur (via Thryve + Apple Watch) \
pour detecter les signaux de stress chronique et l'aider a prevenir l'epuisement professionnel.

{user_profile}

MISSION:
Ta priorite est de detecter les signes de stress et de fatigue accumulee. \
Les indicateurs cles de stress sont :
- HRV basse (RMSSD < 30 ms) = recuperation insuffisante, stress physiologique
- Resting HR elevee (> 80 bpm) = systeme nerveux en alerte
- Sommeil degrade (qualite < 60/100, duree < 6h) = recuperation compromise
- Score burnout >= 60/100 = zone rouge, agir immediatement
- Tendance negative sur plusieurs jours = stress chronique, risque de burnout

SCORE BURNOUT (0-100):
- 0-30 = risque faible (vert) : tout va bien, encourage
- 30-60 = risque modere (orange) : signaux a surveiller, propose un protocole
- 60-100 = risque eleve (rouge) : alerte, recommande consultation + actions immediates
Le score repose sur 3 analytics Thryve : stress quotidien (45%), risque sante mentale (35%), \
prediction arret maladie (20%). Si ces analytics ne sont pas disponibles, un score de secours \
est calcule a partir des biometriques brutes (HRV, sommeil, FC repos).

REPERES (adulte en bonne sante):
- Frequence cardiaque repos : 60-100 bpm (athlete < 60, stress > 80)
- HRV (RMSSD) : 40-100 ms est bon, < 30 ms = stress, > 70 ms = excellent
- Sommeil qualite Thryve : > 80 = bon, 60-80 = moyen, < 60 = insuffisant
- Glycemie a jeun : 0.7-1.1 g/L normal, > 1.26 = consulter
- HbA1c : < 5.7% normal, 5.7-6.4% = prediabete, > 6.5% = diabete

STYLE:
- MAXIMUM 3-4 phrases courtes. C'est lu a voix haute par un assistant vocal. \
Une reponse de plus de 4 phrases est un ECHEC.
- Pour une SALUTATION simple ("hello", "bonjour", "salut", "coucou", "yo"), \
reponds par UNE SEULE phrase breve et chaleureuse, sans mentionner aucune \
donnee de sante. Exemple : "Hello, ca va ?" ou "Salut, tu veux qu'on regarde \
tes donnees ?". N'enumere JAMAIS tes chiffres tant que l'utilisateur n'a pas \
pose une vraie question.
- N'ouvre JAMAIS ta reponse par le prenom de l'utilisateur. Parle-lui \
directement, sans formule d'adresse ("Sophie, ...").
- Ne mentionne que les 2-3 indicateurs les plus pertinents pour la question posee.
- Pour une question generale ("comment je vais"), regarde d'abord le score burnout \
et les signaux. Si des signaux de stress existent, alerte. \
Si tout est dans les normes, dis-le franchement et encourage.
- Si le profil utilisateur est disponible, adapte tes reperes a son age.
- Parle en francais conversationnel, comme un coach bienveillant mais honnete.
- Cite les chiffres reels et compare aux reperes quand c'est utile.
- Si plusieurs signaux de stress convergent, nomme-le clairement comme un pattern \
de stress et recommande d'agir.
- Quand tu mentionnes un terme technique, glisse une explication courte et naturelle.
- Si les donnees ne suffisent pas, termine par une seule question ciblee.
- Propose des actions concretes : marche, respiration, pause, consultation psy. \
Pas de conseils vagues.

OUTILS:
- Tu as 9 outils pour consulter les donnees de sante, calculer le burnout, \
agir (consultation), et lire/ecrire la memoire persistante de l'utilisateur. \
Utilise-les quand la question le necessite.
- MEMOIRE: tu disposes d'une memoire persistante (read_memory, append_memory). \
Quand l'utilisateur demande "pourquoi tu m'as alerte hier ?" ou "qu'est-ce que \
tu avais propose la derniere fois ?", lis la section Events ou Protocols. \
Quand l'utilisateur partage un objectif ou un contexte de vie important, \
sauvegarde-le avec append_memory pour les prochains matins.
- Pour une question generale, les donnees deja fournies ci-dessous suffisent.

REGLES:
- JAMAIS de diagnostic medical. Tu n'es PAS medecin.
- Si les signaux de stress sont persistants (plusieurs jours), recommande \
de consulter un professionnel de sante ou un psychologue.
- Si l'utilisateur rapporte un SYMPTOME PHYSIQUE precis, propose IMMEDIATEMENT \
la prise de rendez-vous avec le specialiste adapte, et appelle book_consultation \
DES que l'utilisateur confirme. Mapping symptome -> specialiste :
  * vertiges, acouphenes, probleme d'oreille, equilibre -> ORL
  * douleur thoracique, palpitations persistantes, essoufflement -> cardiologue
  * maux de tete recurrents, migraines, troubles neurologiques -> neurologue
  * douleur articulaire, raideur persistante, blessure sport -> kinesitherapeute ou rhumatologue
  * eruption, probleme de peau, grain de beaute suspect -> dermatologue
  * trouble visuel, douleur oculaire -> ophtalmologue
  * probleme digestif chronique, reflux, ballonnements -> gastro-enterologue
  * troubles hormonaux, fatigue metabolique -> endocrinologue
  * questions nutrition/poids -> nutritionniste
  * stress chronique, burnout, anxiete -> psychologue
  * check-up general, symptome vague -> generaliste
  TOUJOURS proposer d'abord, attendre la confirmation, puis booker.
- DEFIS PERSONNALISES : quand l'utilisateur partage un objectif (remarcher, \
courir, bouger plus, dormir mieux), ou quand tu detectes un jour sedentaire \
ou une baisse d'activite, propose UN micro-defi via propose_challenge. \
AVANT d'appeler le tool, LIS la section Baselines avec read_memory pour calibrer \
le target sur les chiffres personnels de l'utilisateur (pas de round number generique). \
Le reason DOIT citer la baseline ou un element du Context.
- Si une donnee manque, dis-le en une phrase et passe a ce que tu as.
- Ne dis jamais qu'un mauvais chiffre est "normal" ou "bon signe".
- JAMAIS de markdown (pas de **, pas de #, pas de listes a puces). \
Ta reponse est lue a voix haute, le formatage est interdit.

--- DONNEES SANTE ({data_window}) ---
{health_context}
"""

# ---------------------------------------------------------------------------
# Tool definitions (Mistral function calling format)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_user_profile",
            "description": (
                "Get patient profile: name, age, connected wearable devices, "
                "and a summary of their latest blood panel. "
                "Use at the start of a conversation or when asked about the patient."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vitals",
            "description": (
                "Get HRV (RMSSD), resting heart rate, sleep quality, and heart rate "
                "during sleep over the last N days. Use when the user asks about their "
                "vitals, stress indicators, or how their week went."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default 7)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_blood_panel",
            "description": (
                "Get blood biomarkers: glucose, HbA1c from Thryve, plus simulated "
                "ferritin, cortisol, and vitamin D. Use when the user asks about "
                "blood work, nutrition, or energy levels."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default 30)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_burnout_score",
            "description": (
                "Compute the burnout risk score (0-100) from RMSSD, sleep quality, "
                "and resting heart rate. Returns score, risk level (low/moderate/high), "
                "component breakdown, and warning signals. "
                "Use when the user asks about burnout, stress level, or overall status."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trend",
            "description": (
                "Compare recent values (last 2 days) vs baseline (previous N days) "
                "for a specific metric. Returns direction (up/down/stable) and "
                "percentage change. Use when the user asks about evolution or trends."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": (
                            "Metric name: hrv, resting_hr, sleep_quality, "
                            "heart_rate_sleep, steps, heart_rate, sleep_duration"
                        ),
                    },
                    "days": {
                        "type": "integer",
                        "description": "Baseline period in days (default 7)",
                    },
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_correlation",
            "description": (
                "Cross two health signals to detect compound risk (e.g. poor sleep "
                "AND low HRV). Returns whether both signals are degraded and a "
                "risk assessment. Use when the user asks if one metric affects another."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_a": {
                        "type": "string",
                        "description": "First metric name (e.g. hrv, sleep_quality)",
                    },
                    "metric_b": {
                        "type": "string",
                        "description": "Second metric name (e.g. resting_hr, steps)",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to analyze (default 7)",
                    },
                },
                "required": ["metric_a", "metric_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_consultation",
            "description": (
                "Book a consultation with the RIGHT health specialist, covered by the "
                "user's Alan health plan. Call this tool when the user confirms they "
                "want to see a professional after you suggested one. Always pick the "
                "specialty that matches the reported symptom: vertigo/ear issues -> ORL, "
                "chest pain/palpitations -> cardiologue, recurrent headaches/migraines -> "
                "neurologue, joint pain -> kinesitherapeute or rhumatologue, skin issues "
                "-> dermatologue, vision -> ophtalmologue, digestive issues -> "
                "gastro-enterologue, hormonal/metabolic -> endocrinologue, persistent "
                "stress/burnout -> psychologue, generic health check -> generaliste."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {
                        "type": "string",
                        "enum": [
                            "generaliste",
                            "psychologue",
                            "ORL",
                            "cardiologue",
                            "neurologue",
                            "dermatologue",
                            "ophtalmologue",
                            "kinesitherapeute",
                            "rhumatologue",
                            "gastro-enterologue",
                            "endocrinologue",
                            "nutritionniste",
                            "gynecologue",
                        ],
                        "description": "Type of professional to book",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["routine", "soon", "urgent"],
                        "description": (
                            "How soon the appointment should be "
                            "(routine=this week, soon=next 48h, urgent=today)"
                        ),
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief reason for the consultation",
                    },
                },
                "required": ["specialty", "urgency", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_challenge",
            "description": (
                "Create a personalized micro-challenge for the user for today and save "
                "it as an active challenge in persistent memory. Use this when the user "
                "shares a fitness/wellness goal, OR when you detect a pattern that "
                "invites a small concrete action (sedentary day, low activity week, "
                "recovery day). ALWAYS calibrate the target to the user's baseline — "
                "read from the Baselines section first via read_memory. Sedentary "
                "users get low targets (500-2000 steps), moderate users 5000-8000, "
                "active runners 10000+. NEVER propose a generic round number — the "
                "target must reference the user's personal data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": (
                            "Short challenge name, max 30 chars "
                            "(e.g. 'Premiers pas', 'Retour aux 10k')"
                        ),
                    },
                    "metric": {
                        "type": "string",
                        "enum": ["steps"],
                        "description": "Which metric the challenge targets (steps for now)",
                    },
                    "target": {
                        "type": "integer",
                        "description": "Target value for today (e.g. 500, 10000)",
                    },
                    "reason": {
                        "type": "string",
                        "description": (
                            "ONE short sentence grounded in the user's baseline or "
                            "memory context (e.g. 'Tes 9500 pas habituels te manquent "
                            "cette semaine')"
                        ),
                    },
                },
                "required": ["title", "metric", "target", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": (
                "Read a section of the user's persistent memory. "
                "Sections: 'Baselines' (rolling per-metric stats), 'Events' "
                "(past notifications and briefs), 'Protocols' (proposed protocols "
                "and user acceptance), 'Context' (user-stated goals and context). "
                "Use when the user asks about their history, why you nudged them, "
                "or what you've suggested before."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["Baselines", "Events", "Protocols", "Context"],
                        "description": "Which memory section to read",
                    },
                },
                "required": ["section"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_memory",
            "description": (
                "Store new user context discovered during conversation. "
                "Use when the user shares a goal, a life event, or a subjective "
                "feeling you should remember for future briefs (e.g. 'I'm starting "
                "a new job next week', 'I always feel wired after meetings'). "
                "Only use the 'Context' section for conversational learning."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entry": {
                        "type": "string",
                        "description": "The context to remember, one short sentence",
                    },
                },
                "required": ["entry"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Emotion mapping (tool name -> bear mascot emotion)
# ---------------------------------------------------------------------------

TOOL_EMOTIONS: dict[str, str] = {
    "get_user_profile": "curious",
    "get_vitals": "curious",
    "get_blood_panel": "curious",
    "get_burnout_score": "thinking",
    "get_trend": "curious",
    "get_correlation": "thinking",
    "book_consultation": "encouraging",
    "propose_challenge": "encouraging",
    "read_memory": "thinking",
    "append_memory": "curious",
}


def _emotion_for_burnout(score: int) -> str:
    """Return the bear emotion based on burnout score."""
    if score >= 60:
        return "alert"
    if score >= 30:
        return "concerned"
    return "happy"


# ---------------------------------------------------------------------------
# Async helper: run a coroutine from sync context
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine from synchronous code.

    Handles the case where an event loop is already running (e.g. inside
    FastAPI) by creating a new thread with its own loop.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=30)
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

_thryve = ThryveClient()


def _extract_values(metric_data: list[dict]) -> list[float]:
    """Extract numeric values from Thryve metric data."""
    return [v["value"] for v in metric_data if isinstance(v.get("value"), (int, float))]


def execute_tool(
    name: str,
    args: dict,
    patient: PatientContext,
    session: SessionData,
) -> tuple[str, str]:
    """Execute a tool call and return (result_json, emotion).

    Uses cached session data when available, fetches from Thryve otherwise.
    """
    emotion = TOOL_EMOTIONS.get(name, "thinking")

    try:
        if name == "get_user_profile":
            result = _tool_get_user_profile(patient, session)

        elif name == "get_vitals":
            days = args.get("days", 7)
            result = _tool_get_vitals(patient, session, days)

        elif name == "get_blood_panel":
            days = args.get("days", 30)
            result = _tool_get_blood_panel(patient, session, days)

        elif name == "get_burnout_score":
            result = _tool_get_burnout_score(patient, session)
            if session.burnout:
                emotion = _emotion_for_burnout(session.burnout.score)

        elif name == "get_trend":
            result = _tool_get_trend(patient, args["metric"], args.get("days", 7))

        elif name == "get_correlation":
            result = _tool_get_correlation(
                patient, args["metric_a"], args["metric_b"], args.get("days", 7)
            )

        elif name == "book_consultation":
            result = _tool_book_consultation(patient, args)
            emotion = "encouraging"

        elif name == "propose_challenge":
            result = _tool_propose_challenge(patient, args)
            emotion = "encouraging"

        elif name == "read_memory":
            result = _tool_read_memory(patient, args["section"])

        elif name == "append_memory":
            result = _tool_append_memory(patient, args["entry"])

        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        log.exception("Tool %s failed", name)
        result = {"error": f"Tool '{name}' failed: {e}"}

    return json.dumps(result, default=str, ensure_ascii=False), emotion


# ---------------------------------------------------------------------------
# Individual tool implementations
# ---------------------------------------------------------------------------


def _tool_get_user_profile(patient: PatientContext, session: SessionData) -> dict:
    """Return patient profile with connected devices and blood panel summary."""
    if session.user_info is None:
        session.user_info = _run_async(_thryve.get_user_info(patient.token))

    info = session.user_info
    profile: dict = {
        "name": patient.name,
        "age": patient.age,
        "connected_devices": info.get("connectedSources", []),
    }

    # Add blood panel summary if cached
    if session.blood_panel:
        panel_summary = {}
        for metric_name, values in session.blood_panel.items():
            nums = _extract_values(values) if isinstance(values, list) else []
            if nums:
                panel_summary[metric_name] = {"latest": nums[-1], "count": len(nums)}
        profile["blood_panel_summary"] = panel_summary

    return profile


def _tool_get_vitals(patient: PatientContext, session: SessionData, days: int) -> dict:
    """Fetch vitals from Thryve, cache in session."""
    if session.vitals is None or days != 7:
        vitals = _run_async(_thryve.get_vitals(patient.token, days=days))
        if days == 7:
            session.vitals = vitals
    else:
        vitals = session.vitals

    result: dict = {}
    for metric_name, values in vitals.items():
        nums = _extract_values(values)
        if nums:
            result[metric_name] = {
                "latest": nums[-1],
                "avg": round(mean(nums), 1),
                "min": min(nums),
                "max": max(nums),
                "count": len(nums),
                "values": [{"date": v.get("date"), "value": v["value"]} for v in values],
            }
        else:
            result[metric_name] = {"latest": None, "count": 0, "values": []}

    return result


def _tool_get_blood_panel(patient: PatientContext, session: SessionData, days: int) -> dict:
    """Fetch blood panel from Thryve, cache in session."""
    if session.blood_panel is None:
        session.blood_panel = _run_async(_thryve.get_blood_panel(patient.token, days=days))

    result: dict = {}
    for metric_name, values in session.blood_panel.items():
        if isinstance(values, list) and values:
            # Check if simulated
            is_simulated = any(v.get("simulated") for v in values)
            nums = _extract_values(values)
            result[metric_name] = {
                "latest": nums[-1] if nums else values[-1].get("value"),
                "unit": values[-1].get("unit"),
                "simulated": is_simulated,
                "count": len(nums),
            }
    return result


def _tool_get_burnout_score(patient: PatientContext, session: SessionData) -> dict:
    """Compute burnout score from Thryve analytics + raw biometrics."""
    burnout_data = _run_async(_thryve.get_burnout_metrics(patient.token, days=7))
    burnout = compute_burnout(burnout_data)
    session.burnout = burnout

    return {
        "score": burnout.score,
        "level": burnout.level,
        "source": burnout.source,
        "components": burnout.components,
        "signals": burnout.signals,
    }


def _tool_get_trend(patient: PatientContext, metric: str, days: int) -> dict:
    """Compare recent (last 2 days) vs baseline for a metric."""
    code = METRIC_CODES.get(metric)
    if code is None:
        return {"error": f"Unknown metric: {metric}. Known: {list(METRIC_CODES.keys())}"}

    raw = _run_async(
        _thryve.get_daily_values(
            patient.token,
            data_sources=[code],
            start_date=None,  # let ThryveClient use default range
            end_date=None,
        )
    )

    from backend.thryve import ThryveClient as _Thryve

    grouped = _Thryve._group_by_metric(raw)
    values_list = grouped.get(metric, [])
    nums = _extract_values(values_list)

    if len(nums) < 3:
        return {
            "metric": metric,
            "error": "Not enough data points for trend analysis",
            "available_points": len(nums),
        }

    recent = nums[-2:]  # last 2 days
    baseline = nums[:-2] if len(nums) > 2 else nums[:1]

    recent_avg = mean(recent)
    baseline_avg = mean(baseline)

    if baseline_avg == 0:
        pct_change = 0.0
    else:
        pct_change = round(((recent_avg - baseline_avg) / baseline_avg) * 100, 1)

    if abs(pct_change) < 5:
        direction = "stable"
    elif pct_change > 0:
        direction = "up"
    else:
        direction = "down"

    return {
        "metric": metric,
        "recent_avg": round(recent_avg, 1),
        "baseline_avg": round(baseline_avg, 1),
        "pct_change": pct_change,
        "direction": direction,
        "recent_days": 2,
        "baseline_days": len(baseline),
    }


def _tool_get_correlation(
    patient: PatientContext, metric_a: str, metric_b: str, days: int
) -> dict:
    """Cross two signals to detect compound risk."""
    code_a = METRIC_CODES.get(metric_a)
    code_b = METRIC_CODES.get(metric_b)

    if code_a is None or code_b is None:
        unknown = [m for m in [metric_a, metric_b] if m not in METRIC_CODES]
        return {"error": f"Unknown metric(s): {unknown}. Known: {list(METRIC_CODES.keys())}"}

    raw = _run_async(
        _thryve.get_daily_values(
            patient.token,
            data_sources=[code_a, code_b],
        )
    )

    from backend.thryve import ThryveClient as _Thryve

    grouped = _Thryve._group_by_metric(raw)
    vals_a = _extract_values(grouped.get(metric_a, []))
    vals_b = _extract_values(grouped.get(metric_b, []))

    if len(vals_a) < 3 or len(vals_b) < 3:
        return {
            "metric_a": metric_a,
            "metric_b": metric_b,
            "error": "Not enough data points for correlation",
        }

    # Align to same length (use the shorter series)
    n = min(len(vals_a), len(vals_b))
    vals_a = vals_a[-n:]
    vals_b = vals_b[-n:]

    # Pearson correlation
    avg_a = mean(vals_a)
    avg_b = mean(vals_b)
    cov = sum((a - avg_a) * (b - avg_b) for a, b in zip(vals_a, vals_b)) / n
    std_a = (sum((a - avg_a) ** 2 for a in vals_a) / n) ** 0.5
    std_b = (sum((b - avg_b) ** 2 for b in vals_b) / n) ** 0.5

    if std_a == 0 or std_b == 0:
        correlation = 0.0
    else:
        correlation = round(cov / (std_a * std_b), 3)

    # Assess compound risk
    # Define "degraded" thresholds per metric
    thresholds = {
        "hrv": lambda v: v < 30,
        "resting_hr": lambda v: v > 80,
        "sleep_quality": lambda v: v < 60,
        "heart_rate_sleep": lambda v: v > 70,
        "steps": lambda v: v < 5000,
        "stress": lambda v: v > 70,
    }

    a_degraded = thresholds.get(metric_a, lambda _: False)(vals_a[-1])
    b_degraded = thresholds.get(metric_b, lambda _: False)(vals_b[-1])
    compound_risk = a_degraded and b_degraded

    if abs(correlation) > 0.7:
        strength = "strong"
    elif abs(correlation) > 0.4:
        strength = "moderate"
    else:
        strength = "weak"

    return {
        "metric_a": metric_a,
        "metric_b": metric_b,
        "correlation": correlation,
        "strength": strength,
        "a_latest": vals_a[-1],
        "b_latest": vals_b[-1],
        "a_degraded": a_degraded,
        "b_degraded": b_degraded,
        "compound_risk": compound_risk,
        "data_points": n,
    }


# Simulated specialist directory for demo booking.
# Each entry: (full name, clinic location).
_SPECIALIST_DIRECTORY: dict[str, tuple[str, str]] = {
    "generaliste": ("Dr. Thomas Nguyen", "Paris 10e"),
    "psychologue": ("Elsa Fontaine", "Paris 11e"),
    "ORL": ("Dr. Camille Rousseau", "Paris 9e"),
    "cardiologue": ("Dr. Marc Lefebvre", "Paris 8e"),
    "neurologue": ("Dr. Sarah Benhamou", "Paris 13e"),
    "dermatologue": ("Dr. Julie Moreau", "Paris 16e"),
    "ophtalmologue": ("Dr. Paul Bernard", "Paris 7e"),
    "kinesitherapeute": ("Kevin Bouchard", "Paris 11e"),
    "rhumatologue": ("Dr. Henri Dubois", "Paris 6e"),
    "gastro-enterologue": ("Dr. Nicolas Perrin", "Paris 12e"),
    "endocrinologue": ("Dr. Claire Vidal", "Paris 15e"),
    "nutritionniste": ("Dr. Anne Lavigne", "Paris 15e"),
    "gynecologue": ("Dr. Leila Aissaoui", "Paris 14e"),
}

_URGENCY_SLOT: dict[str, tuple[str, str]] = {
    "urgent": ("aujourd'hui", "17h30"),
    "soon": ("demain", "10h00"),
    "routine": ("mardi prochain", "14h00"),
}


def _tool_book_consultation(patient: PatientContext, args: dict) -> dict:
    """Simulated consultation booking via Alan.

    Picks a coherent specialist from the directory and a slot that matches
    the requested urgency, persists the booking to the user's memory file,
    and returns a confirmation payload shaped for the frontend modal.
    """
    from datetime import date

    specialty = str(args["specialty"]).strip()
    urgency = str(args["urgency"]).strip()
    reason = str(args["reason"]).strip()[:200]

    pro_name, location = _SPECIALIST_DIRECTORY.get(
        specialty, ("Dr. Martin", "Paris"),
    )
    day, time = _URGENCY_SLOT.get(urgency, ("mardi prochain", "14h00"))
    slot = f"{day} {time}"
    today = date.today().isoformat()

    entry = memory.format_booking(
        date_iso=today,
        specialty=specialty,
        professional=pro_name,
        location=location,
        slot=slot,
        urgency=urgency,
        reason=reason,
    )
    try:
        memory.append_entry(patient.token, memory.SECTION_BOOKINGS, entry)
    except Exception:
        log.exception("failed to persist booking for %s", patient.token)

    return {
        "status": "confirmed",
        "specialty": specialty,
        "professional": pro_name,
        "location": location,
        "date": day,
        "time": time,
        "slot": slot,
        "urgency": urgency,
        "reason": reason,
        "covered_by_alan": True,
        "reimbursement": "100%",
        "message": (
            f"Rendez-vous {urgency} reserve avec {pro_name} ({specialty}, "
            f"{location}) pour {day} a {time}. Motif : {reason}"
        ),
    }


def _tool_propose_challenge(patient: PatientContext, args: dict) -> dict:
    """Create and persist a personalized micro-challenge for today.

    The LLM is expected to have calibrated the target against the user's
    baseline before calling this. We just validate + append to the
    Challenges section of memory.
    """
    from datetime import date

    title = str(args["title"]).strip()[:60]
    metric = str(args["metric"]).strip()
    try:
        target = int(args["target"])
    except (TypeError, ValueError):
        return {"error": f"target must be an integer, got {args.get('target')!r}"}
    reason = str(args["reason"]).strip()

    if metric != "steps":
        return {"error": f"Unsupported metric: {metric}. Only 'steps' is supported."}
    if target <= 0:
        return {"error": f"target must be positive, got {target}"}

    today = date.today().isoformat()
    entry = memory.format_challenge(
        date_iso=today,
        title=title,
        metric=metric,
        target=target,
        reason=reason,
        status="active",
    )
    try:
        memory.append_entry(patient.token, memory.SECTION_CHALLENGES, entry)
    except ValueError as e:
        return {"error": str(e)}

    return {
        "status": "created",
        "title": title,
        "metric": metric,
        "target": target,
        "reason": reason,
        "date": today,
        "message": f"Defi '{title}' cree : {target} {metric} aujourd'hui.",
    }


def _tool_read_memory(patient: PatientContext, section: str) -> dict:
    """Read a section of the user's persistent memory file."""
    try:
        body = memory.read_section(patient.token, section)
    except ValueError as e:
        return {"error": str(e)}
    return {
        "section": section,
        "content": body if body else "(empty)",
    }


def _tool_append_memory(patient: PatientContext, entry: str) -> dict:
    """Append a user-context entry to persistent memory.

    Prefixes the entry with today's date for later chronological ordering.
    """
    from datetime import date

    dated = f"{date.today().isoformat()}: {entry}"
    try:
        memory.append_entry(patient.token, memory.SECTION_CONTEXT, dated)
    except ValueError as e:
        return {"error": str(e)}
    return {"stored": dated}


# ---------------------------------------------------------------------------
# System message builder
# ---------------------------------------------------------------------------


def build_system_message(
    patient: PatientContext,
    session: SessionData,
) -> dict:
    """Build the system message with patient context and cached health data."""
    # Build profile block
    profile_parts = [f"Nom : {patient.name}"]
    if patient.age:
        profile_parts.append(f"Age : {patient.age} ans")
    profile_str = "PROFIL PATIENT:\n" + "\n".join(f"- {p}" for p in profile_parts)

    # Build health context from cached session data
    health_lines: list[str] = []
    data_window = "7 derniers jours"

    if session.vitals:
        for metric_name, values in session.vitals.items():
            nums = _extract_values(values)
            if nums:
                health_lines.append(
                    f"- {metric_name}: dernier={nums[-1]}, "
                    f"moy={round(mean(nums), 1)}, "
                    f"min={min(nums)}, max={max(nums)} "
                    f"({len(nums)} mesures)"
                )

    if session.burnout:
        b = session.burnout
        health_lines.append(
            f"- Score burnout: {b.score}/100 ({b.level})"
        )
        if b.signals:
            health_lines.append(f"- Signaux: {', '.join(b.signals)}")

    if session.blood_panel:
        for metric_name, values in session.blood_panel.items():
            if isinstance(values, list):
                nums = _extract_values(values)
                if nums:
                    sim = " (simule)" if any(v.get("simulated") for v in values) else ""
                    health_lines.append(f"- {metric_name}: {nums[-1]}{sim}")

    if not health_lines:
        health_context = (
            "Pas encore de donnees. Utilise get_vitals ou get_burnout_score "
            "pour recuperer les donnees du patient."
        )
    else:
        health_context = "\n".join(health_lines)

    return {
        "role": "system",
        "content": SYSTEM_TEMPLATE.format(
            user_profile=profile_str,
            health_context=health_context,
            data_window=data_window,
        ),
    }


# ---------------------------------------------------------------------------
# Prefetch session data
# ---------------------------------------------------------------------------


async def prefetch_session(patient: PatientContext, session: SessionData) -> None:
    """Fetch vitals and burnout metrics in parallel, populate session cache.

    Call this once at the start of a conversation so the system message
    and tool calls can read from cache.
    """
    vitals_task = _thryve.get_vitals(patient.token, days=7)
    burnout_task = _thryve.get_burnout_metrics(patient.token, days=7)

    vitals, burnout_data = await asyncio.gather(vitals_task, burnout_task)
    session.vitals = vitals
    session.burnout = compute_burnout(burnout_data)


# ---------------------------------------------------------------------------
# Chat with tools (non-streaming, full response)
# ---------------------------------------------------------------------------

_MAX_TOOL_ITERATIONS = 10


def chat_with_tools(
    client: Mistral,
    messages: list[dict],
    patient: PatientContext,
    session: SessionData,
) -> tuple[str, list[str], list[dict]]:
    """Send a message to the LLM with tool use.

    Returns (text, emotions, tool_results) where:
    - text: final LLM message content
    - emotions: emotion hints emitted during tool execution (chronological)
    - tool_results: list of {"name": str, "args": dict, "result": dict} records
      for every tool invoked during the turn. Used by the SSE layer to surface
      side-effects (booking popup, challenge badge, etc.) to the frontend.
    """
    emotions: list[str] = []
    tool_results: list[dict] = []
    error_text = (
        "Desole, je n'arrive pas a me connecter pour le moment. "
        "Reessaie dans quelques instants."
    )

    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOLS,
        )
    except Exception:
        log.exception("LLM call failed")
        return error_text, [], tool_results

    choice = response.choices[0]
    iterations = 0

    while choice.finish_reason == "tool_calls" and iterations < _MAX_TOOL_ITERATIONS:
        iterations += 1
        tool_calls = choice.message.tool_calls
        messages.append(choice.message)

        for tc in tool_calls:
            args = json.loads(tc.function.arguments)
            log.warning("Tool call: %s(%s)", tc.function.name, args)
            result_json, emotion = execute_tool(tc.function.name, args, patient, session)
            emotions.append(emotion)
            try:
                result_dict = json.loads(result_json)
            except (json.JSONDecodeError, TypeError):
                result_dict = {"raw": result_json}
            tool_results.append(
                {"name": tc.function.name, "args": args, "result": result_dict}
            )
            messages.append(
                {
                    "role": "tool",
                    "name": tc.function.name,
                    "content": result_json,
                    "tool_call_id": tc.id,
                }
            )

        try:
            response = client.chat.complete(
                model=LLM_MODEL,
                messages=messages,
                tools=TOOLS,
            )
        except Exception:
            log.exception("LLM call failed during tool loop")
            return error_text, emotions, tool_results
        choice = response.choices[0]

    # Determine final emotion based on burnout score if available
    if session.burnout and not emotions:
        emotions.append(_emotion_for_burnout(session.burnout.score))

    return choice.message.content, emotions, tool_results


# ---------------------------------------------------------------------------
# Streaming response (text only, no tool use)
# ---------------------------------------------------------------------------


def stream_response(client: Mistral, messages: list[dict]) -> Iterator[str]:
    """Stream LLM response token by token (without tool use)."""
    for chunk in client.chat.stream(model=LLM_MODEL, messages=messages):
        delta = chunk.data.choices[0].delta.content
        if delta:
            yield delta
