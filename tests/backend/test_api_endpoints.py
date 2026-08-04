"""API contract tests for the ClinicalAI backend."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db import session as db_session_module
from app.main import app


def get_auth_headers(client: TestClient) -> dict[str, str]:
    """Register a default user and return bearer auth headers for protected API calls."""
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Admin",
            "email": "admin@example.com",
            "password": "SecurePass123!",
            "role": "Admin",
        },
    )
    assert register_response.status_code == 201
    access_token = register_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture()
def client() -> TestClient:
    """Create an isolated FastAPI test client with a temporary SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db_session_module.engine = engine
    db_session_module.SessionLocal = TestingSessionLocal
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Session:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[db_session_module.get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_patient_crud_flow(client: TestClient) -> None:
    """Patients should be created and listed using the documented response envelope."""
    headers = get_auth_headers(client)
    response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "age": 34,
            "biological_sex": "female",
            "blood_group": "O+",
            "height_cm": 168.5,
            "weight_kg": 62.5,
            "pregnancy_status": "none",
        },
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["first_name"] == "Jane"

    list_response = client.get("/api/v1/patients?page=1&page_size=10", headers=headers)
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["success"] is True
    assert list_payload["pagination"]["total_items"] == 1


def test_medical_history_flow(client: TestClient) -> None:
    """Patient-scoped medical history endpoints should work with the documented envelope."""
    headers = get_auth_headers(client)
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Smith",
            "age": 40,
            "biological_sex": "male",
            "blood_group": "A-",
            "height_cm": 175.0,
            "weight_kg": 80.0,
            "pregnancy_status": None,
        },
        headers=headers,
    )
    patient_id = patient_response.json()["data"]["id"]

    history_response = client.post(
        f"/api/v1/patients/{patient_id}/medical-history",
        json={
            "condition_name": "Hypertension",
            "diagnosis_date": "2024-01-01",
            "notes": "Managed with lifestyle changes.",
        },
        headers=headers,
    )

    assert history_response.status_code == 201
    assert history_response.json()["success"] is True

    list_response = client.get(
        f"/api/v1/patients/{patient_id}/medical-history?page=1&page_size=10",
        headers=headers,
    )
    assert list_response.status_code == 200
    assert list_response.json()["pagination"]["total_items"] == 1


def test_patient_scoped_resources_use_path_patient_id_in_create_contract(client: TestClient) -> None:
    """All patient-scoped create endpoints should accept patient_id from the path only."""
    headers = get_auth_headers(client)
    patient_response = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "age": 36,
            "biological_sex": "female",
            "blood_group": "B+",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "pregnancy_status": "none",
        },
        headers=headers,
    )
    patient_id = patient_response.json()["data"]["id"]

    allergy_response = client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        json={
            "allergen": "Penicillin",
            "reaction": "Rash",
            "severity": "Mild",
        },
        headers=headers,
    )
    assert allergy_response.status_code == 201
    assert allergy_response.json()["success"] is True

    medication_response = client.post(
        f"/api/v1/patients/{patient_id}/medications",
        json={
            "medication_name": "Metformin",
            "dosage": "500mg",
            "frequency": "Daily",
            "start_date": "2024-01-01",
            "notes": "Take with food.",
        },
        headers=headers,
    )
    assert medication_response.status_code == 201
    assert medication_response.json()["success"] is True

    symptom_response = client.post(
        f"/api/v1/patients/{patient_id}/symptoms",
        json={
            "symptom_name": "Cough",
            "duration": "3 days",
            "severity": "Moderate",
            "notes": "Worse at night.",
        },
        headers=headers,
    )
    assert symptom_response.status_code == 201
    assert symptom_response.json()["success"] is True


def test_openapi_create_schemas_exclude_patient_id_from_request_body(client: TestClient) -> None:
    """The OpenAPI schema should not advertise patient_id in create request bodies for patient-scoped resources."""
    openapi = client.get("/openapi.json").json()

    for path in [
        "/patients/{patient_id}/allergies",
        "/patients/{patient_id}/medications",
        "/patients/{patient_id}/symptoms",
        "/patients/{patient_id}/medical-history",
    ]:
        operation = openapi["paths"][path]["post"]
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        assert "patient_id" not in schema.get("properties", {})
