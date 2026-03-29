"""LLM reasoning with health context injection."""

from collections.abc import Iterator

from mistralai.client import Mistral

from vital.config import LLM_MODEL
from vital.health_store import get_summary

SYSTEM_TEMPLATE = """\
Tu es V.I.T.A.L, un assistant santé vocal. Tu as accès aux données Apple Watch \
de l'utilisateur ci-dessous.

STYLE:
- 3-4 phrases max par réponse. Va droit au but.
- Commence par ce qui compte : les anomalies, les points d'attention.
- Parle en français conversationnel, comme un coach sportif bienveillant.
- Quand tu mentionnes un terme technique (HRV, SpO2, sommeil profond, REM…), \
glisse une explication courte et naturelle dans la phrase. \
Par exemple : "ta variabilité cardiaque (HRV), c'est-à-dire la régularité \
entre chaque battement" ou "ton taux d'oxygène dans le sang (SpO2)". \
Pas de définitions scolaires, juste ce qu'il faut pour comprendre.
- Pas de markdown, pas de listes, pas d'emojis. C'est lu à voix haute.
- Donne des chiffres concrets tirés des données, pas des généralités.
- Si les données ne suffisent pas à trancher, termine par une question \
courte et ciblée pour affiner ton analyse. Une seule question, naturelle, \
pas un interrogatoire.

RÈGLES:
- JAMAIS de diagnostic médical. Tu n'es PAS médecin.
- Si quelque chose est préoccupant, dis-le clairement et recommande un professionnel.
- Si une donnée manque, dis-le en une phrase et passe à autre chose.

--- DONNÉES SANTÉ (dernières {hours}h) ---
{health_context}
"""


def build_system_message(hours: int = 24) -> dict:
    """Build the system message with current health context."""
    summary = get_summary(hours)

    if not summary:
        health_context = (
            "No health data available yet. Ask the user to sync their Apple Watch data."
        )
    else:
        lines = []
        for metric, stats in summary.items():
            unit = stats.get("unit") or ""
            lines.append(
                f"- {metric}: avg={stats['avg']} {unit}, "
                f"min={stats['min']}, max={stats['max']}, "
                f"latest={stats['latest']}"
                f" ({stats['count']} readings)"
            )
        health_context = "\n".join(lines)

    return {
        "role": "system",
        "content": SYSTEM_TEMPLATE.format(hours=hours, health_context=health_context),
    }


def stream_response(client: Mistral, messages: list[dict]) -> Iterator[str]:
    """Stream LLM response token by token."""
    for chunk in client.chat.stream(model=LLM_MODEL, messages=messages):
        delta = chunk.data.choices[0].delta.content
        if delta:
            yield delta
