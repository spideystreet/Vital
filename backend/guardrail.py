"""Nebius Llama Guard 3 8B guardrail: checks LLM responses before delivery.

Blocks medical diagnosis (Llama Guard category S6 — Specialized Advice)
and replaces unsafe responses with a safe redirect to a health professional.
"""

from dataclasses import dataclass

import httpx

from backend.config import NEBIUS_API_KEY, NEBIUS_BASE_URL

GUARD_MODEL = "meta-llama/Llama-Guard-3-8B"

SAFE_REPLACEMENT = (
    "Je ne suis pas médecin et je ne peux pas poser de diagnostic. "
    "Je te recommande de consulter un professionnel de santé pour cette question."
)

_PROMPT_TEMPLATE = """\
[INST] Task: Check if there is unsafe content in 'Agent' messages \
in conversations according to our safety policy.

<BEGIN CONVERSATION>

User: {user_message}
Agent: {assistant_response}

<END CONVERSATION>

Provide your safety assessment for Agent in the above conversation. [/INST]"""


@dataclass
class GuardrailResult:
    safe: bool
    category: str | None  # e.g. "S6" if blocked
    original_response: str
    safe_response: str  # either original (if safe) or replacement


def _parse_guard_output(output: str) -> tuple[bool, str | None]:
    """Parse Llama Guard output into (is_safe, category)."""
    text = output.strip()
    if text.lower().startswith("safe"):
        return True, None
    # Format: "unsafe\nS6" or "unsafe\n S6"
    lines = text.splitlines()
    category = None
    if len(lines) >= 2:
        category = lines[1].strip()
    return False, category


async def check_response(user_message: str, assistant_response: str) -> GuardrailResult:
    """Check if the LLM response is safe using Llama Guard 3.

    Args:
        user_message: The user's input message.
        assistant_response: The assistant's response to check.

    Returns:
        GuardrailResult indicating whether the response is safe.
    """
    prompt = _PROMPT_TEMPLATE.format(
        user_message=user_message,
        assistant_response=assistant_response,
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{NEBIUS_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NEBIUS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GUARD_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 64,
                "temperature": 0.0,
            },
        )
        resp.raise_for_status()

    data = resp.json()
    guard_output = data["choices"][0]["message"]["content"]
    is_safe, category = _parse_guard_output(guard_output)

    return GuardrailResult(
        safe=is_safe,
        category=category,
        original_response=assistant_response,
        safe_response=assistant_response if is_safe else SAFE_REPLACEMENT,
    )


def check_response_sync(user_message: str, assistant_response: str) -> GuardrailResult:
    """Synchronous version for use in non-async contexts."""
    prompt = _PROMPT_TEMPLATE.format(
        user_message=user_message,
        assistant_response=assistant_response,
    )

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            f"{NEBIUS_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {NEBIUS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GUARD_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 64,
                "temperature": 0.0,
            },
        )
        resp.raise_for_status()

    data = resp.json()
    guard_output = data["choices"][0]["message"]["content"]
    is_safe, category = _parse_guard_output(guard_output)

    return GuardrailResult(
        safe=is_safe,
        category=category,
        original_response=assistant_response,
        safe_response=assistant_response if is_safe else SAFE_REPLACEMENT,
    )
