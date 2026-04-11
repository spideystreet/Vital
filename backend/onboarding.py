"""One-time vocal onboarding: asks the question bank in order, writes initial memory file.

Session state is kept in a module-level dict keyed by user_id. This is fine for the
hackathon (single-process demo). For production, back it with Redis or a real session store.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend import memory
from backend.onboarding_questions import QUESTIONS, OnboardingQuestion

log = logging.getLogger(__name__)


class OnboardingError(RuntimeError):
    """Raised on invalid onboarding flow transitions."""


@dataclass
class OnboardingStep:
    """What the frontend needs to render the current question."""

    index: int
    total: int
    question: OnboardingQuestion
    done: bool = False


# user_id -> ordered dict of answered {question_id: raw_value}
_SESSIONS: dict[str, dict[str, Any]] = {}


def start_session(user_id: str) -> OnboardingStep:
    """Begin onboarding for a user. Resets any in-flight session for that user."""
    _SESSIONS[user_id] = {}
    return _current_step(user_id)


def record_answer(user_id: str, question_id: str, value: Any) -> OnboardingStep:
    """Record an answer for the current question and advance to the next one."""
    session = _SESSIONS.get(user_id)
    if session is None:
        raise OnboardingError(f"no active onboarding session for user_id={user_id}")
    current = _current_question(session)
    if current is None:
        raise OnboardingError("onboarding already complete — call finalize()")
    if question_id != current.id:
        raise OnboardingError(
            f"expected answer for {current.id!r}, got {question_id!r}"
        )
    session[question_id] = value
    return _current_step(user_id)


def finalize(user_id: str) -> None:
    """Write the seeded memory file for this user. Raises if any answers are missing."""
    session = _SESSIONS.get(user_id)
    if session is None:
        raise OnboardingError(f"no active onboarding session for user_id={user_id}")
    missing = [q.id for q in QUESTIONS if q.id not in session]
    if missing:
        raise OnboardingError(f"cannot finalize, missing answers: {missing}")

    memory.ensure_memory_file(user_id)
    for q in QUESTIONS:
        entry = f"{q.field}: {session[q.id]}"
        section = (
            memory.SECTION_BASELINES if q.section == "Baselines" else memory.SECTION_CONTEXT
        )
        memory.append_entry(user_id, section, entry)

    del _SESSIONS[user_id]
    log.info("onboarding.finalized user_id=%s", user_id)


def _current_question(session: dict[str, Any]) -> OnboardingQuestion | None:
    for q in QUESTIONS:
        if q.id not in session:
            return q
    return None


def _current_step(user_id: str) -> OnboardingStep:
    session = _SESSIONS[user_id]
    current = _current_question(session)
    if current is None:
        return OnboardingStep(
            index=len(QUESTIONS),
            total=len(QUESTIONS),
            question=QUESTIONS[-1],
            done=True,
        )
    return OnboardingStep(
        index=len(session),
        total=len(QUESTIONS),
        question=current,
        done=False,
    )
