from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from cryptography.fernet import Fernet
import pytest
from pydantic import ValidationError as ConfigurationError
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.base import Base
from app.db.models import MedicalReport, ReportStorageDeletion
from app.repositories.medical_report import MedicalReportRepository
from app.repositories.patient import PatientRepository
from app.schemas.medical_report import ReportUploadRequest
from app.services import medical_report
from app.services.exceptions import StorageUnavailableError, ValidationError
from app.services.report_storage import S3ReportStorage


from tests.backend.workspace_helpers import WORKSPACE_HEADERS, seed_workspace, start_workspace

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION = {
    "ENVIRONMENT": "production",
    "DEBUG": "false",
    "DATABASE_URL": "postgres://test:secret%25value@db.example.test/clinical",
    "WORKSPACE_SIGNING_SECRET": "synthetic-workspace-signing-secret",
    "LLM_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    "FRONTEND_URL": "https://web.example.test",
    "STORAGE_PROVIDER": "s3",
    "STORAGE_BUCKET": "synthetic-tests",
    "STORAGE_ACCESS_KEY_ID": "test-id",
    "STORAGE_SECRET_ACCESS_KEY": "test-key",
}
PATIENT = {
    "first_name": "Test", "last_name": "Patient", "age": 35,
    "biological_sex": "Female", "blood_group": "A+", "height_cm": 165, "weight_kg": 60,
}


@pytest.mark.parametrize("override", [
    {"DEBUG": "true"},
    {"DATABASE_URL": "sqlite://"},
    {"DATABASE_URL": "postgres://db.example.test/clinical?sslmode=disable"},
    {"WORKSPACE_SIGNING_SECRET": "dev-secret-key-change-in-production"},
    {"ALLOWED_CORS_ORIGINS": "*"},
    {"ALLOWED_CORS_ORIGINS": '["https://web.example.test/path"]'},
    {"STORAGE_PROVIDER": "local"},
])
def test_rejects_insecure_production_settings(monkeypatch, override):
    for key, value in (PRODUCTION | override).items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ConfigurationError):
        Settings(_env_file=None)


@pytest.mark.parametrize("missing_storage", [False, True])
def test_hosted_app_import_startup_and_cors(tmp_path, missing_storage):
    env = os.environ | PRODUCTION | {
        "VERCEL": "1",
        "ALLOWED_CORS_ORIGINS": "https://preview.example.test, https://web.example.test",
        "DIRECT_DATABASE_URL": "",
        "UPLOAD_DIRECTORY": str(tmp_path / "no-uploads"),
    }
    if missing_storage:
        env.update(STORAGE_BUCKET="", STORAGE_ACCESS_KEY_ID="", STORAGE_SECRET_ACCESS_KEY="")
    code = """
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.db.session import engine
from sqlalchemy.pool import NullPool

assert isinstance(engine.pool, NullPool)
assert engine.url.drivername == 'postgresql+psycopg'
assert engine.url.password == 'secret%value'
assert engine.url.query['sslmode'] == 'require'
assert get_settings().resolve_database_path() is None
with TestClient(app) as client:
    assert client.get('/api/v1/health').json()['data']['status'] == 'ok'
    catalog = client.get('/api/v1/llm/providers')
    assert catalog.status_code == 200
    assert set(catalog.json()['data']) == {'openai', 'gemini', 'anthropic', 'openrouter', 'groq', 'custom'}
    assert catalog.json()['data']['custom'] == []
    for path in ('/docs', '/redoc', '/openapi.json'):
        assert client.get(path).status_code == 200
    for path in ('/patients', '/patients/1/reports', '/patients/1/symptoms', '/patients/1/analysis'):
        assert client.get('/api/v1' + path).status_code == 401
    for origin, status in [('https://web.example.test', 200), ('https://other.example.test', 400)]:
        response = client.options('/api/v1/llm/config', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'x-clinicalai-request, content-type',
        })
        assert response.status_code == status
        assert response.headers.get('access-control-allow-origin') == (origin if status == 200 else None)
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "backend", env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "no-uploads").exists()


def test_hosted_startup_reports_missing_settings_without_values():
    synthetic_bad_value = "synthetic-private-value"
    env = os.environ | PRODUCTION | {
        "VERCEL": "1", "DEBUG": "true", "LLM_ENCRYPTION_KEY": "",
        "WORKSPACE_SIGNING_SECRET": synthetic_bad_value,
        "STORAGE_PROVIDER": "s3", "STORAGE_BUCKET": "", "STORAGE_SECRET_ACCESS_KEY": "",
    }
    result = subprocess.run(
        [sys.executable, "-c", "from app.main import app"],
        cwd=ROOT / "backend", env=env, capture_output=True, text=True,
    )
    assert result.returncode != 0
    for name in ("DEBUG", "WORKSPACE_SIGNING_SECRET", "LLM_ENCRYPTION_KEY"):
        assert name in result.stderr
    assert synthetic_bad_value not in result.stderr


class FakeReportStorage:
    staged = b""
    fail_put = False
    fail_delete = False

    def __init__(self):
        self.objects = {}

    def authorize_upload(self, name, content_type, size):
        return {"url": "https://objects.example.test", "fields": {"key": name, "Content-Type": content_type}}

    def read_upload(self, name, content_type, size):
        assert size == len(self.staged)
        return self.staged

    def put(self, name, content, content_type):
        self.objects[name] = content
        if self.fail_put:
            raise StorageUnavailableError("synthetic upload failure")

    def delete(self, name):
        if self.fail_delete:
            raise StorageUnavailableError("synthetic delete failure")
        self.objects.pop(name, None)

    def delete_upload(self, name):
        self.staged = b""


def test_direct_report_upload_ownership_retry_and_cleanup(monkeypatch):
    for key, value in PRODUCTION.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(medical_report, "settings", Settings(_env_file=None))
    storage = FakeReportStorage()
    monkeypatch.setattr(medical_report, "get_s3_report_storage", lambda: storage)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = seed_workspace(db)
        patients = PatientRepository(db)
        reports = MedicalReportRepository(db)
        patient_id = patients.create(PATIENT).id
        other_patient = patients.create(PATIENT).id
        service = medical_report.MedicalReportService(reports, patients)
        size = 20 * 1024 * 1024
        with pytest.raises(ValidationError, match="20 MB"):
            service.authorize_upload(patient_id, ReportUploadRequest(filename="report.txt", size=size + 1))

        intent = service.authorize_upload(patient_id, ReportUploadRequest(filename="report.txt", size=size))
        seed_workspace(db)
        with pytest.raises(ValidationError):
            service.complete_upload(patient_id, intent.token)
        db.info["workspace_id"] = owner
        with pytest.raises(ValidationError):
            service.complete_upload(other_patient, intent.token)

        storage.staged = b"x" * size
        report = service.complete_upload(patient_id, intent.token)
        assert len(report.extracted_text) == 4096
        assert len(reports.get(report.id).extracted_text) == size
        assert not storage.staged
        assert len(storage.objects[f"{owner}/{report.stored_filename}"]) == size
        assert service.complete_upload(patient_id, intent.token).id == report.id
        assert reports.count(patient_id=patient_id) == 1

        storage.fail_delete = True
        with pytest.raises(StorageUnavailableError):
            service.delete(report.id)
        assert reports.get(report.id) is None
        assert db.get(ReportStorageDeletion, report.stored_filename) is not None
        storage.fail_delete = False
        service.delete(report.id)
        assert not storage.objects
        assert db.get(ReportStorageDeletion, report.stored_filename) is None

        intent = service.authorize_upload(patient_id, ReportUploadRequest(filename="report.pdf", size=4))
        storage.staged = b"text"
        with pytest.raises(ValidationError, match="format"):
            service.complete_upload(patient_id, intent.token)
        assert not storage.staged
        assert reports.count(patient_id=patient_id) == 0

        intent = service.authorize_upload(patient_id, ReportUploadRequest(filename="report.txt", size=4))
        storage.staged = b"text"
        storage.fail_put = True
        with pytest.raises(StorageUnavailableError):
            service.complete_upload(patient_id, intent.token)
        assert reports.count(patient_id=patient_id) == 0
        assert not storage.objects
        storage.fail_put = False
        assert service.complete_upload(patient_id, intent.token).extracted_text == "text"


def test_s3_post_policy_enforces_exact_size_type_and_key(monkeypatch):
    from app.services import report_storage

    monkeypatch.setattr(report_storage, "get_settings", lambda: SimpleNamespace(
        storage_issues=lambda: [], storage_bucket="synthetic-tests", storage_endpoint=None, storage_region="us-east-1",
        storage_access_key_id="test-id", storage_secret_access_key="test-key",
    ))
    storage = S3ReportStorage()
    size = 20 * 1024 * 1024
    post = storage.authorize_upload("opaque.txt", "text/plain", size)
    conditions = json.loads(base64.b64decode(post["fields"]["policy"]))["conditions"]
    assert ["content-length-range", size, size] in conditions
    assert {"Content-Type": "text/plain"} in conditions
    assert {"key": "pending-reports/opaque.txt"} in conditions
    assert "acl" not in post["fields"]


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="requires a disposable PostgreSQL database")
def test_postgresql_migrations_workspaces_and_report_lifecycle(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.db.session import get_db
    from app.main import app
    from app.core.config import get_settings
    from app.services import llm

    url = os.environ["TEST_POSTGRES_URL"]
    engine = create_engine(Settings(DATABASE_URL=url, _env_file=None).database_url)
    assert not inspect(engine).get_table_names(), "TEST_POSTGRES_URL must reference an empty disposable database"

    def postgres_session():
        with Session(engine) as db:
            yield db

    monkeypatch.setitem(app.dependency_overrides, get_db, postgres_session)
    client = TestClient(app)
    catalog = client.get("/api/v1/llm/providers")
    assert catalog.status_code == 200
    assert catalog.json()["data"]["openai"] and catalog.json()["data"]["gemini"]
    before_migration = client.post("/api/v1/workspace", headers=WORKSPACE_HEADERS)
    assert before_migration.status_code == 503
    assert before_migration.json()["error"] == "database_schema_incomplete"
    assert "set-cookie" not in before_migration.headers

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=os.environ | {"DATABASE_URL": "postgresql://unused.example.test/db", "DIRECT_DATABASE_URL": url},
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    monkeypatch.setattr(medical_report, "REPORTS_STORAGE_DIR", tmp_path)

    assert client.get("/api/v1/patients").status_code == 401
    headers = start_workspace(client)
    other_visitor = TestClient(app)
    start_workspace(other_visitor)
    settings = get_settings().model_copy(update={
        "llm_encryption_key": Fernet.generate_key().decode(),
    })
    monkeypatch.setattr(llm, "get_settings", lambda: settings)
    monkeypatch.setattr(llm, "build_ai_provider", lambda *args: SimpleNamespace(test_connection=lambda: None))
    config = client.put("/api/v1/llm/config", json={
        "provider": "openai", "model": "gpt-4.1-mini", "api_key": "synthetic-visitor-key", "remember": True,
    })
    assert config.status_code == 200, config.text
    assert client.get("/api/v1/llm/config").json()["data"]["configured"]
    assert not other_visitor.get("/api/v1/llm/config").json()["data"]["configured"]

    response = client.post("/api/v1/patients", json=PATIENT, headers=headers)
    assert response.status_code == 201, response.text
    patient_id = response.json()["data"]["id"]
    assert other_visitor.get(f"/api/v1/patients/{patient_id}").status_code == 404
    response = client.post(
        f"/api/v1/patients/{patient_id}/reports",
        files={"file": ("test.txt", BytesIO(b"synthetic report"), "text/plain")},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    report = response.json()["data"]
    assert report["extracted_text"] == "synthetic report"
    path = f"/api/v1/patients/reports/{report['id']}"
    assert client.get(f"{path}/download", headers=headers).content == b"synthetic report"
    assert client.delete(path, headers=headers).status_code == 204
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(MedicalReport)) == 0
        assert db.scalar(select(func.count()).select_from(ReportStorageDeletion)) == 0
    assert not list(tmp_path.rglob("*.txt"))
    assert client.delete(f"/api/v1/patients/{patient_id}", headers=headers).status_code == 204
    engine.dispose()
