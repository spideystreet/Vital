"""Tests for health_store module."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vital.health_store import (
    get_latest,
    get_recent_raw,
    get_summary,
    init_db,
    insert_metrics,
)


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Patch DB_PATH to a temp SQLite file and initialize the schema."""
    # Create a unique database file for this test
    import uuid
    db_file = tmp_path / f"test_health_{uuid.uuid4().hex}.db"
    
    # Patch the database path and directory
    monkeypatch.setattr("vital.health_store.DB_PATH", db_file)
    monkeypatch.setattr("vital.health_store.DATA_DIR", tmp_path)
    
    # Initialize the database
    init_db()
    
    return db_file


class TestInitDB:
    """Test database initialization."""

    def test_init_db_creates_table(self, tmp_db):
        """Verify init_db creates the health_data table."""
        import sqlite3

        with sqlite3.connect(tmp_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        assert ("health_data",) in tables

    def test_init_db_creates_index(self, tmp_db):
        """Verify init_db creates the metric/date index."""
        import sqlite3

        with sqlite3.connect(tmp_db) as conn:
            indexes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        assert ("idx_health_metric_date",) in indexes


class TestInsertMetrics:
    """Test metric insertion."""

    def test_insert_single_metric(self, tmp_db):
        """Insert a single metric and check the returned count."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "unit": "bpm",
            "recorded_at": "2026-03-28T08:30:00Z",
        }
        count = insert_metrics([metric])
        assert count == 1

    def test_insert_multiple_metrics(self, tmp_db):
        """Insert multiple metrics in one batch."""
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": "2026-03-28T08:30:00Z",
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "unit": "%",
                "recorded_at": "2026-03-28T08:35:00Z",
            },
        ]
        count = insert_metrics(metrics)
        assert count == 2

    def test_insert_with_metadata(self, tmp_db):
        """Metadata dict is JSON-serialized into the metadata column."""
        import sqlite3

        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "unit": "bpm",
            "recorded_at": "2026-03-28T08:30:00Z",
            "metadata": {"device": "apple_watch", "source": "healthkit"},
        }
        insert_metrics([metric])

        with sqlite3.connect(tmp_db) as conn:
            row = conn.execute("SELECT metadata FROM health_data").fetchone()
        assert row[0] is not None
        assert json.loads(row[0]) == {"device": "apple_watch", "source": "healthkit"}

    def test_insert_without_optional_fields(self, tmp_db):
        """Unit and metadata are optional and default to NULL."""
        metric = {
            "metric": "heart_rate",
            "value": 72.0,
            "recorded_at": "2026-03-28T08:30:00Z",
        }
        count = insert_metrics([metric])
        assert count == 1


class TestGetLatest:
    """Test retrieving latest metrics."""

    def test_get_latest_empty_db(self, tmp_db):
        """Empty database returns an empty list."""
        result = get_latest("heart_rate")
        assert result == []

    def test_get_latest_single_metric(self, tmp_db):
        """Single inserted metric is retrievable."""
        insert_metrics([
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": "2026-03-28T08:30:00Z",
            }
        ])
        result = get_latest("heart_rate")
        assert len(result) == 1
        assert result[0]["metric"] == "heart_rate"
        assert result[0]["value"] == 72.0

    def test_get_latest_multiple_metrics(self, tmp_db):
        """Limit parameter restricts results, ordered most-recent first."""
        metrics = [
            {
                "metric": "heart_rate",
                "value": 70.0,
                "unit": "bpm",
                "recorded_at": "2026-03-28T08:00:00Z",
            },
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": "2026-03-28T08:30:00Z",
            },
            {
                "metric": "heart_rate",
                "value": 75.0,
                "unit": "bpm",
                "recorded_at": "2026-03-28T09:00:00Z",
            },
        ]
        insert_metrics(metrics)

        result = get_latest("heart_rate", limit=2)
        assert len(result) == 2
        assert result[0]["value"] == 75.0
        assert result[1]["value"] == 72.0

    def test_get_latest_different_metric(self, tmp_db):
        """get_latest filters by metric name."""
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": "2026-03-28T08:30:00Z",
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "unit": "%",
                "recorded_at": "2026-03-28T08:35:00Z",
            },
        ]
        insert_metrics(metrics)

        result = get_latest("spo2")
        assert len(result) == 1
        assert result[0]["metric"] == "spo2"


class TestGetSummary:
    """Test summary aggregation."""

    def test_get_summary_empty_db(self, tmp_db):
        """Empty database returns an empty dict."""
        result = get_summary(hours=24)
        assert result == {}

    def test_get_summary_single_metric(self, tmp_db):
        """Aggregation computes avg/min/max correctly."""
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()

        metrics = [
            {
                "metric": "heart_rate",
                "value": 70.0,
                "unit": "bpm",
                "recorded_at": one_hour_ago,
            },
            {
                "metric": "heart_rate",
                "value": 75.0,
                "unit": "bpm",
                "recorded_at": now.isoformat(),
            },
        ]
        insert_metrics(metrics)

        result = get_summary(hours=24)
        assert "heart_rate" in result
        assert result["heart_rate"]["avg"] == 72.5
        assert result["heart_rate"]["min"] == 70.0
        assert result["heart_rate"]["max"] == 75.0

    def test_get_summary_multiple_metrics(self, tmp_db):
        """Summary covers all distinct metric types."""
        now = datetime.now(timezone.utc)
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": now.isoformat(),
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "unit": "%",
                "recorded_at": now.isoformat(),
            },
        ]
        insert_metrics(metrics)

        result = get_summary(hours=24)
        assert "heart_rate" in result
        assert "spo2" in result
        assert result["heart_rate"]["avg"] == 72.0
        assert result["spo2"]["avg"] == 98.0

    def test_get_summary_time_filter(self, tmp_db):
        """Old records outside the time window are excluded."""
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(days=2)).isoformat()
        recent_date = now.isoformat()

        metrics = [
            {
                "metric": "heart_rate",
                "value": 60.0,
                "unit": "bpm",
                "recorded_at": old_date,
            },
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": recent_date,
            },
        ]
        insert_metrics(metrics)

        result = get_summary(hours=24)
        assert result["heart_rate"]["avg"] == 72.0
        assert result["heart_rate"]["count"] == 1


class TestGetRecentRaw:
    """Test retrieving recent raw data."""

    def test_get_recent_raw_empty_db(self, tmp_db):
        """Empty database returns an empty list."""
        result = get_recent_raw(hours=24)
        assert result == []

    def test_get_recent_raw_single_entry(self, tmp_db):
        """Single recent entry is returned."""
        now = datetime.now(timezone.utc)
        insert_metrics([
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": now.isoformat(),
            }
        ])

        result = get_recent_raw(hours=24)
        assert len(result) == 1
        assert result[0]["metric"] == "heart_rate"

    def test_get_recent_raw_multiple_entries(self, tmp_db):
        """Multiple recent entries are all returned."""
        now = datetime.now(timezone.utc)
        metrics = [
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": now.isoformat(),
            },
            {
                "metric": "spo2",
                "value": 98.0,
                "unit": "%",
                "recorded_at": now.isoformat(),
            },
        ]
        insert_metrics(metrics)

        result = get_recent_raw(hours=24)
        assert len(result) == 2

    def test_get_recent_raw_time_filter(self, tmp_db):
        """Old records outside the time window are excluded."""
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(days=2)).isoformat()
        recent_date = now.isoformat()

        metrics = [
            {
                "metric": "heart_rate",
                "value": 60.0,
                "unit": "bpm",
                "recorded_at": old_date,
            },
            {
                "metric": "heart_rate",
                "value": 72.0,
                "unit": "bpm",
                "recorded_at": recent_date,
            },
        ]
        insert_metrics(metrics)

        result = get_recent_raw(hours=24)
        assert len(result) == 1
        assert result[0]["value"] == 72.0
