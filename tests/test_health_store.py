"""Tests for health_store module."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from vital.health_store import (
    get_latest,
    get_recent_raw,
    get_summary,
    init_db,
    insert_metrics,
)


class TestInitDB:
    """Test database initialization."""

    def test_init_db_idempotent(self, test_db):
        """Calling init_db multiple times does not raise."""
        init_db()
        init_db()

    def test_init_db_seeds_default_metrics(self, test_db):
        """Default metrics are seeded in metric_catalog."""
        import psycopg

        from vital.config import DATABASE_URL

        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute(f"SET search_path TO {test_db}")
            rows = conn.execute("SELECT name FROM metric_catalog ORDER BY name").fetchall()
        names = [r[0] for r in rows]
        assert "heart_rate" in names
        assert "spo2" in names
        assert "steps" in names
        assert "sleep" in names


class TestInsertMetrics:
    """Test metric insertion."""

    def test_insert_single_metric(self, test_db):
        """Insert a single metric and check the returned count."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "recorded_at": "2026-03-28T08:30:00Z",
        }
        count = insert_metrics([metric])
        assert count == 1

    def test_insert_multiple_metrics(self, test_db):
        """Insert multiple metrics in one batch."""
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "recorded_at": "2026-03-28T08:30:00Z",
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "recorded_at": "2026-03-28T08:35:00Z",
            },
        ]
        count = insert_metrics(metrics)
        assert count == 2

    def test_insert_with_metadata(self, test_db):
        """Metadata dict is stored as JSONB."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "recorded_at": "2026-03-28T08:30:00Z",
            "metadata": {"device": "apple_watch", "source": "healthkit"},
        }
        insert_metrics([metric])

        result = get_latest("heart_rate")
        meta = result[0]["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta)
        assert meta == {"device": "apple_watch", "source": "healthkit"}

    def test_insert_without_optional_fields(self, test_db):
        """Source, value_end, and metadata are optional and default to NULL."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "recorded_at": "2026-03-28T08:30:00Z",
        }
        count = insert_metrics([metric])
        assert count == 1

        result = get_latest("heart_rate")
        assert result[0]["metadata"] is None
        assert result[0]["value_end"] is None
        assert result[0]["source"] is None

    def test_insert_empty_list(self, test_db):
        """Inserting an empty list inserts zero rows."""
        count = insert_metrics([])
        assert count == 0

    def test_insert_duplicate_metrics(self, test_db):
        """Inserting the same metric twice creates two distinct rows."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "recorded_at": "2026-03-28T08:30:00Z",
        }
        insert_metrics([metric])
        insert_metrics([metric])

        result = get_latest("heart_rate", limit=10)
        assert len(result) == 2

    def test_insert_unknown_metric_raises(self, test_db):
        """Inserting an unknown metric name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown metric"):
            insert_metrics(
                [
                    {
                        "metric": "nonexistent_metric",
                        "value": 42.0,
                        "recorded_at": "2026-03-28T08:30:00Z",
                    }
                ]
            )

    def test_insert_missing_required_field_raises(self, test_db):
        """Missing required fields raise KeyError."""
        with pytest.raises(KeyError):
            insert_metrics([{"metric": "heart_rate", "value": 72.0}])

        with pytest.raises(KeyError):
            insert_metrics([{"recorded_at": "2026-03-28T08:30:00Z", "value": 72.0}])

        with pytest.raises(KeyError):
            insert_metrics([{"metric": "heart_rate", "recorded_at": "2026-03-28T08:30:00Z"}])

    def test_insert_with_none_metadata(self, test_db):
        """Explicitly passing metadata=None stores NULL."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "recorded_at": "2026-03-28T08:30:00Z",
            "metadata": None,
        }
        insert_metrics([metric])

        result = get_latest("heart_rate")
        assert result[0]["metadata"] is None

    def test_insert_with_source(self, test_db):
        """Source field is stored correctly."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "recorded_at": "2026-03-28T08:30:00Z",
            "source": "apple_watch_ultra",
        }
        insert_metrics([metric])

        result = get_latest("heart_rate")
        assert result[0]["source"] == "apple_watch_ultra"

    def test_insert_with_value_end(self, test_db):
        """value_end is stored for duration-type metrics."""
        metric = {
            "metric": "sleep",
            "value": 7.5,
            "value_end": 8.0,
            "recorded_at": "2026-03-28T08:30:00Z",
        }
        insert_metrics([metric])

        result = get_latest("sleep")
        assert result[0]["value_end"] == 8.0


class TestGetLatest:
    """Test retrieving latest metrics."""

    def test_get_latest_empty_db(self, test_db):
        """Empty database returns an empty list."""
        result = get_latest("heart_rate")
        assert result == []

    def test_get_latest_single_metric(self, test_db):
        """Single inserted metric is retrievable."""
        insert_metrics(
            [
                {
                    "metric": "heart_rate",
                    "value": 72.0,
                    "recorded_at": "2026-03-28T08:30:00Z",
                }
            ]
        )
        result = get_latest("heart_rate")
        assert len(result) == 1
        assert result[0]["metric"] == "heart_rate"
        assert result[0]["value"] == 72.0

    def test_get_latest_multiple_metrics(self, test_db):
        """Limit parameter restricts results, ordered most-recent first."""
        metrics = [
            {
                "metric": "heart_rate",
                "value": 70.0,
                "recorded_at": "2026-03-28T08:00:00Z",
            },
            {
                "metric": "heart_rate",
                "value": 72.0,
                "recorded_at": "2026-03-28T08:30:00Z",
            },
            {
                "metric": "heart_rate",
                "value": 75.0,
                "recorded_at": "2026-03-28T09:00:00Z",
            },
        ]
        insert_metrics(metrics)

        result = get_latest("heart_rate", limit=2)
        assert len(result) == 2
        assert result[0]["value"] == 75.0
        assert result[1]["value"] == 72.0

    def test_get_latest_different_metric(self, test_db):
        """get_latest filters by metric name."""
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "recorded_at": "2026-03-28T08:30:00Z",
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "recorded_at": "2026-03-28T08:35:00Z",
            },
        ]
        insert_metrics(metrics)

        result = get_latest("spo2")
        assert len(result) == 1
        assert result[0]["metric"] == "spo2"

    def test_get_latest_nonexistent_metric(self, test_db):
        """Querying a metric that was never inserted returns an empty list."""
        insert_metrics(
            [
                {
                    "metric": "heart_rate",
                    "value": 72.0,
                    "recorded_at": "2026-03-28T08:30:00Z",
                }
            ]
        )
        result = get_latest("nonexistent_metric")
        assert result == []


class TestGetSummary:
    """Test summary aggregation."""

    def test_get_summary_empty_db(self, test_db):
        """Empty database returns an empty dict."""
        result = get_summary(hours=24)
        assert result == {}

    def test_get_summary_single_metric(self, test_db):
        """Aggregation computes avg/min/max correctly."""
        now = datetime.now(UTC)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()

        metrics = [
            {
                "metric": "heart_rate",
                "value": 70.0,
                "recorded_at": one_hour_ago,
            },
            {
                "metric": "heart_rate",
                "value": 75.0,
                "recorded_at": now.isoformat(),
            },
        ]
        insert_metrics(metrics)

        result = get_summary(hours=24)
        assert "heart_rate" in result
        assert result["heart_rate"]["avg"] == 72.5
        assert result["heart_rate"]["min"] == 70.0
        assert result["heart_rate"]["max"] == 75.0

    def test_get_summary_multiple_metrics(self, test_db):
        """Summary covers all distinct metric types."""
        now = datetime.now(UTC)
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "recorded_at": now.isoformat(),
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "recorded_at": now.isoformat(),
            },
        ]
        insert_metrics(metrics)

        result = get_summary(hours=24)
        assert "heart_rate" in result
        assert "spo2" in result
        assert result["heart_rate"]["avg"] == 72.0
        assert result["spo2"]["avg"] == 98.0

    def test_get_summary_time_filter(self, test_db):
        """Old records outside the time window are excluded."""
        now = datetime.now(UTC)
        old_date = (now - timedelta(days=2)).isoformat()
        recent_date = now.isoformat()

        metrics = [
            {
                "metric": "heart_rate",
                "value": 60.0,
                "recorded_at": old_date,
            },
            {
                "metric": "heart_rate",
                "value": 72.0,
                "recorded_at": recent_date,
            },
        ]
        insert_metrics(metrics)

        result = get_summary(hours=24)
        assert result["heart_rate"]["avg"] == 72.0
        assert result["heart_rate"]["count"] == 1

    def test_get_summary_zero_hours(self, test_db):
        """A zero-hour window returns no data."""
        now = datetime.now(UTC)
        insert_metrics(
            [
                {
                    "metric": "heart_rate",
                    "value": 72.0,
                    "recorded_at": (now - timedelta(minutes=1)).isoformat(),
                }
            ]
        )
        result = get_summary(hours=0)
        assert result == {}


class TestGetRecentRaw:
    """Test retrieving recent raw data."""

    def test_get_recent_raw_empty_db(self, test_db):
        """Empty database returns an empty list."""
        result = get_recent_raw(hours=24)
        assert result == []

    def test_get_recent_raw_single_entry(self, test_db):
        """Single recent entry is returned."""
        now = datetime.now(UTC)
        insert_metrics(
            [
                {
                    "metric": "heart_rate",
                    "value": 72.0,
                    "recorded_at": now.isoformat(),
                }
            ]
        )

        result = get_recent_raw(hours=24)
        assert len(result) == 1
        assert result[0]["metric"] == "heart_rate"

    def test_get_recent_raw_multiple_entries(self, test_db):
        """Multiple recent entries are all returned."""
        now = datetime.now(UTC)
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "recorded_at": now.isoformat(),
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "recorded_at": now.isoformat(),
            },
        ]
        insert_metrics(metrics)

        result = get_recent_raw(hours=24)
        assert len(result) == 2

    def test_get_recent_raw_time_filter(self, test_db):
        """Old records outside the time window are excluded."""
        now = datetime.now(UTC)
        old_date = (now - timedelta(days=2)).isoformat()
        recent_date = now.isoformat()

        metrics = [
            {
                "metric": "heart_rate",
                "value": 60.0,
                "recorded_at": old_date,
            },
            {
                "metric": "heart_rate",
                "value": 72.0,
                "recorded_at": recent_date,
            },
        ]
        insert_metrics(metrics)

        result = get_recent_raw(hours=24)
        assert len(result) == 1
        assert result[0]["value"] == 72.0

    def test_get_recent_raw_ordered_descending(self, test_db):
        """Results are ordered by recorded_at descending (most recent first)."""
        now = datetime.now(UTC)
        metrics = [
            {
                "metric": "heart_rate",
                "value": 60.0,
                "recorded_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "metric": "heart_rate",
                "value": 80.0,
                "recorded_at": (now - timedelta(hours=1)).isoformat(),
            },
            {
                "metric": "heart_rate",
                "value": 70.0,
                "recorded_at": now.isoformat(),
            },
        ]
        insert_metrics(metrics)

        result = get_recent_raw(hours=24)
        values = [r["value"] for r in result]
        assert values == [70.0, 80.0, 60.0]
