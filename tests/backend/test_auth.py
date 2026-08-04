"""Authentication and authorization behavior tests."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db import session as db_session_module
from app.main import app


def override_dependencies() -> TestClient:
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
    return TestClient(app)


def test_registration_and_login_flow() -> None:
    with override_dependencies() as client:
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Dr. Jane Doe",
                "email": "jane@example.com",
                "password": "SecurePass123!",
                "role": "Doctor",
            },
        )
        assert register_response.status_code == 201
        payload = register_response.json()
        assert payload["success"] is True
        assert payload["data"]["email"] == "jane@example.com"

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "jane@example.com", "password": "SecurePass123!"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["data"]["access_token"]


def test_protected_route_requires_authentication() -> None:
    with override_dependencies() as client:
        response = client.get("/api/v1/patients")
        assert response.status_code == 401
        assert response.json()["success"] is False


def test_role_permissions_block_ai_analysis_for_staff() -> None:
    with override_dependencies() as client:
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Staff User",
                "email": "staff@example.com",
                "password": "SecurePass123!",
                "role": "Staff",
            },
        )
        assert register_response.status_code == 201
        token = register_response.json()["data"]["access_token"]

        response = client.post(
            "/api/v1/patients/1/analysis",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403
        assert response.json()["success"] is False
