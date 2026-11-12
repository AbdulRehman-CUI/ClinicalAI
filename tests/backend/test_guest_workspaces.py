from datetime import datetime, timedelta, timezone
import json
from secrets import token_urlsafe
from types import SimpleNamespace

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import httpx
import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from app.api.workspace import capability_hash, cookie_name
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import AIAnalysis, GuestWorkspace, Patient, WorkspaceLLMConfiguration
from app.db.session import get_db
from app.main import app
from app.services import llm, medical_report
from tests.backend.workspace_helpers import start_workspace

PATIENT = {
    "first_name": "Synthetic", "last_name": "Patient", "age": 30,
    "biological_sex": "Female", "blood_group": "A+", "height_cm": 165, "weight_kg": 62,
}
CLINICAL = {
    "medical-history": {"condition_name": "History", "notes": "Synthetic notes"},
    "medications": {"medication_name": "Example", "dosage": "10 mg", "frequency": "daily", "start_date": "2026-01-01", "notes": ""},
    "allergies": {"allergen": "Example", "reaction": "Rash", "severity": "Mild"},
    "symptoms": {"symptom_name": "Headache", "duration": "1 day", "severity": "Mild", "notes": ""},
}
OPENAI = {"provider": "openai", "model": "gpt-4.1-mini", "api_key": "test-openai-secret"}
GEMINI = {"provider": "gemini", "model": "gemini-3.6-flash", "api_key": "test-gemini-secret"}
OUTPUT = {
    "possible_diagnoses": [], "medication_warnings": [], "critical_alerts": [],
    "recommended_tests": [], "recommended_specialist": "", "summary": "Synthetic analysis.",
}


@pytest.fixture()
def setup(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{(tmp_path / 'guest.db').as_posix()}")
    Base.metadata.create_all(engine)

    def db_dependency():
        with Session(engine) as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, db_dependency)
    monkeypatch.setattr(medical_report, "REPORTS_STORAGE_DIR", tmp_path / "uploads")
    encryption_key = Fernet.generate_key().decode()
    monkeypatch.setattr(llm, "get_settings", lambda: get_settings().model_copy(update={"llm_encryption_key": encryption_key}))
    monkeypatch.setattr(llm, "time", lambda: 1200)
    calls = []

    def fake_provider(provider, model, key):
        def check():
            calls.append(("test", provider, model, key))
            if key == "invalid-secret":
                error = RuntimeError(f"Sensitive input {key}")
                error.status_code = 401
                raise error

        def generate(*, system_prompt, user_prompt):
            calls.append(("analyze", provider, model, key))
            if key == "timeout-secret":
                raise httpx.ReadTimeout(f"Sensitive input {key}")
            assert system_prompt and user_prompt
            return json.dumps(OUTPUT)

        return SimpleNamespace(test_connection=check, generate_content=generate)

    monkeypatch.setattr(llm, "build_ai_provider", fake_provider)
    with TestClient(app) as left, TestClient(app) as right:
        start_workspace(left)
        start_workspace(right)
        yield engine, left, right, calls
    engine.dispose()


def test_guest_scope_and_csrf(setup):
    engine, left, right, _ = setup
    name = cookie_name("workspace")
    assert left.cookies.get(name) != right.cookies.get(name)
    assert left.post("/api/v1/auth/register", json={}).status_code == 404
    assert left.post("/api/v1/auth/login", json={}).status_code == 404
    assert left.post("/api/v1/workspace").status_code == 204
    patient = left.post("/api/v1/patients", json=PATIENT)
    assert patient.status_code == 201, patient.text
    patient_id = patient.json()["data"]["id"]
    owned = f"/api/v1/patients/{patient_id}"
    assert right.get("/api/v1/patients").json()["data"] == []
    assert right.get(owned).status_code == 404
    assert right.put(owned, json={"first_name": "Changed"}).status_code == 404
    assert right.delete(owned).status_code == 404
    assert left.put(owned, json={"first_name": "Changed"}, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert left.put(owned, json={"first_name": "Changed"}, headers={"X-ClinicalAI-Request": ""}).status_code == 403
    other = right.post("/api/v1/patients", json=PATIENT).json()["data"]["id"]
    for resource, payload in CLINICAL.items():
        added = left.post(f"{owned}/{resource}", json=payload)
        assert added.status_code == 201, added.text
        path = f"/api/v1/patients/{resource}/{added.json()['data']['id']}"
        assert right.get(f"{owned}/{resource}").status_code == 404
        assert right.post(f"{owned}/{resource}", json=payload).status_code == 404
        assert right.put(path, json={}).status_code == 404
        assert right.delete(path).status_code == 404
        assert left.put(path, json={"patient_id": other}).status_code == 404
        assert len(left.get(f"{owned}/{resource}").json()["data"]) == 1

    report = left.post(f"{owned}/reports", files={"file": ("test.txt", b"synthetic", "text/plain")})
    assert report.status_code == 201, report.text
    path = f"/api/v1/patients/reports/{report.json()['data']['id']}"
    assert left.get(f"{path}/download").content == b"synthetic"
    assert right.get(path).status_code == 404
    assert right.get(f"{path}/download").status_code == 404
    assert right.delete(path).status_code == 404
    assert right.post(f"{owned}/analyze").status_code == 404
    assert left.delete(owned).status_code == 204
    assert left.get(path).status_code == 404

    with Session(engine) as db:
        db.add(Patient(**PATIENT))
        db.commit()
        legacy = db.scalar(select(Patient.id).where(Patient.workspace_id.is_(None)))
    assert right.get(f"/api/v1/patients/{legacy}").status_code == 404


def test_forged_and_expired_credentials_do_not_restore_records(setup):
    engine, left, right, _ = setup
    name = cookie_name("workspace")
    response = left.post("/api/v1/patients", json=PATIENT)
    patient_path = f"/api/v1/patients/{response.json()['data']['id']}"
    previous = left.cookies.get(name)
    with Session(engine) as db:
        workspace = db.scalar(select(GuestWorkspace).where(GuestWorkspace.credential_hash == capability_hash(previous)))
        assert workspace.credential_hash != previous
        assert right.get(patient_path, headers={"Cookie": f"{name}={workspace.id}"}).status_code == 401
        assert right.get(patient_path, headers={"Cookie": f"{name}={token_urlsafe(32)}"}).status_code == 401
        workspace.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert left.get(patient_path).status_code == 401
    start_workspace(left)
    assert left.cookies.get(name) != previous
    assert left.get(patient_path).status_code == 404


def test_production_workspace_cookie_is_host_only_and_secure(setup, monkeypatch):
    from app.api import workspace

    production = get_settings().model_copy(update={
        "environment": "production", "frontend_url": "https://app.example.test",
        "allowed_cors_origins": ["https://app.example.test"],
    })
    monkeypatch.setattr(workspace, "get_settings", lambda: production)
    with TestClient(app, base_url="https://api.example.test") as browser:
        response = browser.post("/api/v1/workspace", headers={
            "Origin": "https://app.example.test", "X-ClinicalAI-Request": "1",
        })
        assert response.status_code == 204
        cookie = response.headers["set-cookie"]
        assert cookie.startswith("__Host-clinicalai-workspace=")
        assert all(attribute in cookie for attribute in ("Secure", "HttpOnly", "SameSite=lax", "Path=/"))
        assert "Domain=" not in cookie
        assert browser.get("/api/v1/patients").status_code == 200


def test_llm_configuration_is_encrypted_and_workspace_scoped(setup, monkeypatch, caplog):
    engine, left, right, calls = setup
    monkeypatch.setenv("OPENAI_API_KEY", "operator-key-must-never-be-used")
    assert left.get("/api/v1/llm/providers").json()["data"]["gemini"]
    patient_ids = []
    for browser in (left, right):
        patient = browser.post("/api/v1/patients", json=PATIENT).json()["data"]["id"]
        browser.post(f"/api/v1/patients/{patient}/symptoms", json=CLINICAL["symptoms"])
        patient_ids.append(patient)
    a, b = (f"/api/v1/patients/{pid}/analyze" for pid in patient_ids)
    assert left.post(a).json()["error"] == "llm_not_configured"
    assert not calls
    assert left.post("/api/v1/llm/test", json=OPENAI).json()["data"]["tested"]
    invalid = left.put("/api/v1/llm/config", json=OPENAI | {"api_key": "invalid-secret"})
    assert invalid.status_code == 422 and invalid.json()["error"] == "llm_invalid_key"
    assert "invalid-secret" not in invalid.text + caplog.text
    assert left.put("/api/v1/llm/config", json=OPENAI | {"model": "not-supported"}).json()["error"] == "llm_model_unsupported"

    saved = left.put("/api/v1/llm/config", json=OPENAI)
    assert saved.status_code == 200, saved.text
    assert "HttpOnly" in saved.headers["set-cookie"] and "Max-Age" not in saved.headers["set-cookie"]
    assert right.get("/api/v1/llm/config").json()["data"]["configured"] is False
    assert right.put("/api/v1/llm/config", json=GEMINI | {"remember": True}).status_code == 200
    metadata = left.get("/api/v1/llm/config")
    assert metadata.json()["data"]["has_api_key"]
    assert OPENAI["api_key"] not in metadata.text + saved.text
    with Session(engine) as db:
        encrypted = db.scalars(select(WorkspaceLLMConfiguration.encrypted_api_key)).all()
        assert len(encrypted) == 2
        assert all(key not in value for key in (OPENAI["api_key"], GEMINI["api_key"]) for value in encrypted)
    for browser, path in ((left, a), (right, b)):
        analyzed = browser.post(path)
        assert analyzed.status_code == 200, analyzed.text
        analysis_id = analyzed.json()["data"]["analysis_id"]
        other = right if browser is left else left
        assert other.get(f"/api/v1/patients/analysis/{analysis_id}").status_code == 404
    assert ("analyze", "openai", OPENAI["model"], OPENAI["api_key"]) in calls
    assert ("analyze", "gemini", GEMINI["model"], GEMINI["api_key"]) in calls

    changed = left.put("/api/v1/llm/config", json=OPENAI | {"model": "gpt-4o-mini", "api_key": "timeout-secret"})
    assert changed.status_code == 200
    failed = left.post(a)
    assert failed.status_code == 504 and failed.json()["error"] == "llm_timeout"
    assert "timeout-secret" not in failed.text + caplog.text
    assert left.delete("/api/v1/llm/config").status_code == 204
    assert left.post(a).json()["error"] == "llm_not_configured"
    assert right.get("/api/v1/llm/config").json()["data"]["configured"]
    with Session(engine) as db:
        assert len(db.scalars(select(AIAnalysis)).all()) == 2


def test_llm_session_expiry_and_shared_rate_budget(setup):
    engine, left, right, _ = setup
    assert left.put("/api/v1/llm/config", json=OPENAI).status_code == 200
    assert left.get("/api/v1/llm/config").json()["data"]["configured"]
    workspace = left.cookies.get(cookie_name("workspace"))
    assert not left.get("/api/v1/llm/config", headers={
        "Cookie": f"{cookie_name('workspace')}={workspace}",
    }).json()["data"]["configured"]
    with Session(engine) as db:
        db.execute(update(WorkspaceLLMConfiguration).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        db.commit()
    assert not left.get("/api/v1/llm/config").json()["data"]["configured"]
    for _ in range(7):
        assert left.post("/api/v1/llm/test", json=OPENAI).status_code == 200
    assert left.post("/api/v1/llm/test", json=OPENAI).json()["error"] == "workspace_rate_limited"
    assert right.post("/api/v1/llm/test", json=GEMINI).status_code == 200
