"""Tests for backend.onboarding — session flow and memory seeding."""
from __future__ import annotations

import pytest

from backend import memory, onboarding
from backend.onboarding_questions import QUESTIONS


@pytest.fixture
def tmp_memory(monkeypatch, tmp_path):
    monkeypatch.setattr(memory, "MEMORY_DIR", tmp_path)
    return tmp_path


class TestOnboardingSession:
    def test_start_session_returns_first_question(self, tmp_memory):
        step = onboarding.start_session("demo-user")
        assert step.index == 0
        assert step.question.id == QUESTIONS[0].id
        assert step.total == len(QUESTIONS)

    def test_record_answer_advances_to_next_question(self, tmp_memory):
        onboarding.start_session("demo-user")
        step = onboarding.record_answer("demo-user", QUESTIONS[0].id, 32)
        assert step.index == 1
        assert step.question.id == QUESTIONS[1].id

    def test_record_answer_rejects_wrong_question_id(self, tmp_memory):
        onboarding.start_session("demo-user")
        with pytest.raises(onboarding.OnboardingError):
            onboarding.record_answer("demo-user", "not-the-current-question", "foo")

    def test_finalize_writes_memory_file_with_baselines_and_context(self, tmp_memory):
        onboarding.start_session("demo-user")
        for q in QUESTIONS:
            onboarding.record_answer(
                "demo-user",
                q.id,
                _dummy_value_for(q.type),
            )
        onboarding.finalize("demo-user")
        path = memory.MEMORY_DIR / "demo-user.md"
        assert path.exists()
        body = path.read_text()
        assert "## Baselines" in body
        assert "## Context" in body
        assert "age" in body
        assert "smoker" in body

    def test_finalize_before_all_questions_answered_raises(self, tmp_memory):
        onboarding.start_session("demo-user")
        onboarding.record_answer("demo-user", QUESTIONS[0].id, 32)
        with pytest.raises(onboarding.OnboardingError):
            onboarding.finalize("demo-user")


def _dummy_value_for(t):
    return {
        "integer": 5,
        "scale_1_10": 5,
        "string": "test",
        "enum": "male",
        "boolean": False,
    }[t]
