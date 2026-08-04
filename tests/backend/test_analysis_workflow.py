from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import session as db_session_module
from app.db.base import Base
from app.db.models import AIAnalysis
from app.main import app
from app.repositories.patient import PatientRepository
from app.repositories.symptom import SymptomRepository


@pytest.fixture()
def db_session() -> Session:
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

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def override_get_db() -> Session:
        db = db_session_module.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[db_session_module.get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def populated_patient(db_session: Session) -> int:
    patient = PatientRepository(db_session).create(
        {
            "first_name": "Dana",
            "last_name": "Kim",
            "age": 33,
            "biological_sex": "female",
            "blood_group": "B+",
            "height_cm": 160.0,
            "weight_kg": 60.0,
            "pregnancy_status": "none",
        }
    )
    SymptomRepository(db_session).create(
        {
            "patient_id": patient.id,
            "symptom_name": "Headache",
            "duration": "2 days",
            "severity": "moderate",
            "notes": "Persistent headache",
        }
    )
    return patient.id


def test_analysis_endpoint_creates_ai_analysis_record(client: TestClient, populated_patient: int, monkeypatch: pytest.MonkeyPatch) -> None:
    class StubEngine:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def analyze(self, context: object) -> dict[str, object]:
            return {
                "possible_diagnoses": [{"name": "Migraine", "confidence": "Medium", "reason": "Headache pattern"}],
                "medication_warnings": [{"drug": "Aspirin", "reason": "Possible interaction"}],
                "critical_alerts": [{"title": "Monitor", "reason": "Needs review"}],
                "recommended_tests": ["CBC"],
                "recommended_specialist": "Neurologist",
                "summary": "Patient should be reviewed by a clinician.",
            }

    monkeypatch.setattr("app.services.analysis.AIEngine", StubEngine)

    response = client.post(f"/api/v1/patients/{populated_patient}/analyze")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["summary"] == "Patient should be reviewed by a clinician."


def test_analysis_endpoint_returns_404_for_unknown_patient(client: TestClient) -> None:
    response = client.post("/api/v1/patients/999/analyze")

    assert response.status_code == 404


def test_analysis_endpoint_returns_503_when_openai_fails(client: TestClient, populated_patient: int, monkeypatch: pytest.MonkeyPatch) -> None:
    class StubEngine:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def analyze(self, context: object) -> dict[str, object]:
            raise RuntimeError("OpenAI unavailable")

    monkeypatch.setattr("app.services.analysis.AIEngine", StubEngine)

    response = client.post(f"/api/v1/patients/{populated_patient}/analyze")

    assert response.status_code == 503


def test_analysis_endpoint_returns_502_for_malformed_response(client: TestClient, populated_patient: int, monkeypatch: pytest.MonkeyPatch) -> None:
    class StubEngine:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def analyze(self, context: object) -> str:
            return "{bad json"

    monkeypatch.setattr("app.services.analysis.AIEngine", StubEngine)

    response = client.post(f"/api/v1/patients/{populated_patient}/analyze")

    assert response.status_code == 502
