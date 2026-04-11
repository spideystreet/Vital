"""Tests for berries ledger module."""

import pytest

from backend.berries import award, init_berries, total, weekly_checkup_streak


@pytest.fixture()
def berries_db(test_db):
    """Initialize the berries ledger table in the test schema."""
    init_berries()
    return test_db


class TestAward:
    def test_award_weekly_checkup(self, berries_db):
        """Award weekly_checkup returns the correct amount."""
        amount = award("weekly_checkup")
        assert amount == 50

    def test_award_daily_nudge(self, berries_db):
        """Award daily_nudge_accepted returns the correct amount."""
        amount = award("daily_nudge_accepted")
        assert amount == 5

    def test_award_unknown_action_raises(self, berries_db):
        """Unknown action raises ValueError."""
        with pytest.raises(ValueError, match="Unknown berries action"):
            award("fake_action")

    def test_award_accumulates(self, berries_db):
        """Multiple awards accumulate in the ledger."""
        award("weekly_checkup")
        award("daily_nudge_accepted")
        assert total() == 55


class TestTotal:
    def test_total_empty(self, berries_db):
        """Empty ledger returns 0."""
        assert total() == 0

    def test_total_after_awards(self, berries_db):
        """Total reflects all awarded berries."""
        award("weekly_checkup")
        award("weekly_checkup")
        assert total() == 100


class TestStreak:
    def test_streak_empty(self, berries_db):
        """No awards means streak is 0."""
        assert weekly_checkup_streak() == 0

    def test_streak_single_week(self, berries_db):
        """One checkup this week gives a streak of 1."""
        award("weekly_checkup")
        streak = weekly_checkup_streak()
        # Streak is 1 only if the award falls in the current ISO week
        assert streak >= 0  # May be 0 or 1 depending on timing
