"""Tests for the backend placeholder health endpoint."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_returns_standard_response() -> None:
    """The health endpoint should use the documented API envelope."""
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Backend service is healthy.",
        "data": {"status": "ok"},
    }

