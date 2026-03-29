"""Tests for health_server API."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from vital.health_server import app
from vital.health_store import insert_metrics


@pytest.fixture()
def client(test_db):
    """Return a TestClient with a clean test database."""
    return TestClient(app)


class TestPingEndpoint:
    """Test the ping endpoint."""

    def test_ping(self, client):
        """Ping returns alive status."""
        response = client.get("/health/ping")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


class TestReceiveHealthData:
    """Test the health data reception endpoint."""

    def test_receive_valid_data(self, client):
        """Valid payload inserts metrics and returns count."""
        payload = {
            "metrics": [
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
        }
        response = client.post("/health", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["inserted"] == 2

    def test_receive_empty_metrics_list(self, client):
        """Empty metrics list returns 400."""
        payload = {"metrics": []}
        response = client.post("/health", json=payload)
        assert response.status_code == 400
        assert "No metrics provided" in response.text

    def test_receive_malformed_payload(self, client):
        """Payload without 'metrics' key triggers validation error."""
        payload = {"invalid": "data"}
        response = client.post("/health", json=payload)
        assert response.status_code == 422

    def test_receive_missing_metrics_field(self, client):
        """Missing metrics field triggers validation error."""
        payload = {"other_field": "value"}
        response = client.post("/health", json=payload)
        assert response.status_code == 422


class TestHealthSummaryEndpoint:
    """Test the health summary endpoint."""

    def test_summary_empty_db(self, client):
        """Summary on empty database returns empty dict."""
        response = client.get("/health/summary")
        assert response.status_code == 200
        assert response.json() == {}

    def test_summary_with_data(self, client):
        """Summary returns aggregated stats for inserted data."""
        now = datetime.now(UTC)
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

        response = client.get("/health/summary")
        assert response.status_code == 200
        data = response.json()
        assert "heart_rate" in data
        assert "spo2" in data
        assert data["heart_rate"]["avg"] == 72.0
        assert data["spo2"]["avg"] == 98.0

    def test_summary_with_time_parameter(self, client):
        """Time parameter filters out old records."""
        now = datetime.now(UTC)
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

        response = client.get("/health/summary?hours=24")
        assert response.status_code == 200
        data = response.json()
        assert data["heart_rate"]["avg"] == 72.0
        assert data["heart_rate"]["count"] == 1

    def test_summary_invalid_time_parameter(self, client):
        """Non-integer hours parameter triggers validation error."""
        response = client.get("/health/summary?hours=invalid")
        assert response.status_code == 422
