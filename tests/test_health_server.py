"""Tests for health_server API."""

import pytest
from fastapi.testclient import TestClient

from backend.health_server import app


@pytest.fixture()
def client(test_db):
    """Return a TestClient with a clean test database."""
    return TestClient(app)


@pytest.fixture()
def api_client():
    """Return a TestClient without database (for API-only tests)."""
    return TestClient(app)


class TestPingEndpoint:
    """Test the ping endpoint."""

    def test_ping(self, api_client):
        """Ping returns alive status."""
        response = api_client.get("/health/ping")
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

    def test_receive_empty_metrics_list(self, api_client):
        """Empty metrics list returns 400."""
        payload = {"metrics": []}
        response = api_client.post("/health", json=payload)
        assert response.status_code == 400
        assert "No metrics provided" in response.text

    def test_receive_malformed_payload(self, api_client):
        """Payload without 'metrics' key triggers validation error."""
        payload = {"invalid": "data"}
        response = api_client.post("/health", json=payload)
        assert response.status_code == 422

    def test_receive_missing_metrics_field(self, api_client):
        """Missing metrics field triggers validation error."""
        payload = {"other_field": "value"}
        response = api_client.post("/health", json=payload)
        assert response.status_code == 422


class TestPatientsEndpoint:
    """Test the patients list endpoint."""

    def test_list_patients(self, api_client):
        """Returns list of demo patients."""
        response = api_client.get("/api/patients")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert all("id" in p and "name" in p for p in data)

    def test_patient_ids_unique(self, api_client):
        """All patient IDs are unique."""
        response = api_client.get("/api/patients")
        ids = [p["id"] for p in response.json()]
        assert len(ids) == len(set(ids))


class TestCheckupStartEndpoint:
    """Test checkup session creation."""

    def test_start_valid_patient(self, api_client):
        """Starting a checkup with valid patient returns session_id."""
        response = api_client.post(
            "/api/checkup/start", json={"patient_id": "patient-1"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_start_unknown_patient(self, api_client):
        """Starting a checkup with unknown patient returns 404."""
        response = api_client.post(
            "/api/checkup/start", json={"patient_id": "unknown"}
        )
        assert response.status_code == 404
