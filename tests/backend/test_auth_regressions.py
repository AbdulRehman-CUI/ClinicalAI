"""Regression coverage for the token-to-profile failure and existing bcrypt accounts."""

from datetime import datetime, timedelta, timezone
import json
import logging

import bcrypt
import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.logging import JsonFormatter
from app.db.base import Base
from app.db.models import User
from app.db.session import get_db
from app.main import app
from app.services.auth import settings
from app.services.auth import AuthService
from app.repositories.user import UserRepository
from app.schemas.auth import UserRegisterRequest


@pytest.fixture()
def auth_client(monkeypatch):
    """Use a separate in-memory database; never reset the configured database."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    monkeypatch.setattr(settings, "password_hash_rounds", 4)

    def database():
        with sessions() as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, sessions
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def register(client):
    response = client.post("/api/v1/auth/register", json={"full_name": "Regression Clinician", "email": "regression@example.com", "password": "TestPassword123!", "role": "Doctor"})
    assert response.status_code == 201, response.text
    return response.json()["data"]


def test_registration_login_logout_relogin_refresh_and_complete_profile(auth_client):
    client, _ = auth_client
    registered = register(client)
    for attempt in range(2):
        login = client.post("/api/v1/auth/login", json={"email": "regression@example.com", "password": "TestPassword123!"})
        assert login.status_code == 200
        tokens = login.json()["data"]
        profile = client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert profile.status_code == 200, profile.text
        data = profile.json()["data"]
        assert data["id"] == registered["id"]
        assert data["created_at"] and data["updated_at"]
        assert "hashed_password" not in data
        assert client.post("/api/v1/auth/logout").status_code == 200
    renewed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert renewed.status_code == 200
    assert client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {renewed.json()['data']['access_token']}"}).status_code == 200


def test_wrong_password_unknown_email_and_duplicate_email_are_expected_errors(auth_client):
    client, _ = auth_client
    register(client)
    for email in ["regression@example.com", "unknown@example.com"]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "IncorrectPassword"})
        assert response.status_code == 401
        assert response.json()["message"] == "Invalid email or password."
        assert response.headers["www-authenticate"] == "Bearer"
    duplicate = client.post("/api/v1/auth/register", json={"full_name": "Duplicate", "email": "REGRESSION@example.com", "password": "TestPassword123!", "role": "Staff"})
    assert duplicate.status_code == 409


def test_duplicate_email_insert_race_rolls_back_without_changing_existing_account(auth_client, monkeypatch):
    client, sessions = auth_client
    register(client)
    with sessions() as session:
        repository = UserRepository(session)
        lookup = repository.get_by_email
        existing = lookup("regression@example.com")
        original_hash = existing.hashed_password
        calls = 0

        def race_lookup(email):
            nonlocal calls
            calls += 1
            return None if calls == 1 else lookup(email)

        monkeypatch.setattr(repository, "get_by_email", race_lookup)
        with pytest.raises(HTTPException) as error:
            AuthService(repository).register(UserRegisterRequest(full_name="Duplicate", email="regression@example.com", password="DifferentPassword123!"))
        assert error.value.status_code == 409
        assert lookup("regression@example.com").hashed_password == original_hash


@pytest.mark.parametrize("password", ["ExistingPassword123!", "x" * 80])
def test_preexisting_bcrypt_accounts_remain_usable_without_rehashing(auth_client, password):
    client, sessions = auth_client
    # Simulate a hash created before this change, including legacy truncation.
    original_hash = bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=4)).decode()
    with sessions() as session:
        session.add(User(full_name="Existing User", email="existing@example.com", hashed_password=original_hash, role="Staff", is_active=True))
        session.commit()
    response = client.post("/api/v1/auth/login", json={"email": "existing@example.com", "password": password})
    assert response.status_code == 200
    assert client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {response.json()['data']['access_token']}"}).status_code == 200
    with sessions() as session:
        assert session.scalar(select(User.hashed_password).where(User.email == "existing@example.com")) == original_hash


@pytest.mark.parametrize("changes", [{"exp": 1}, {"sub": "not-a-number"}, {"sub": "-1"}, {"sub": "9" * 100}, {"type": "refresh"}])
def test_expired_wrong_type_and_invalid_subject_access_tokens_return_401(auth_client, changes):
    client, _ = auth_client
    registered = register(client)
    claims = {"sub": str(registered["id"]), "type": "access", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), **changes}
    token = jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    response = client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize("token", ["invalid-token", "", "unsigned.payload.signature"])
def test_malformed_tokens_return_401_for_profile_and_refresh(auth_client, token):
    client, _ = auth_client
    assert client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == (422 if not token else 401)


def test_refresh_rejects_expired_access_and_invalid_subject_tokens(auth_client):
    client, _ = auth_client
    registered = register(client)
    for changes in [{"exp": 1}, {"sub": "invalid"}, {"type": "access"}]:
        token = jwt.encode({"sub": str(registered["id"]), "type": "refresh", "exp": datetime.now(timezone.utc) + timedelta(minutes=5), **changes}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        assert client.post("/api/v1/auth/refresh", json={"refresh_token": token}).status_code == 401


def test_disabled_user_and_corrupt_hash_do_not_cause_500(auth_client):
    client, sessions = auth_client
    registered = register(client)
    with sessions() as session:
        user = session.get(User, registered["id"])
        user.is_active = False
        session.commit()
    assert client.post("/api/v1/auth/login", json={"email": "regression@example.com", "password": "TestPassword123!"}).status_code == 403
    assert client.get("/api/v1/auth/users/me", headers={"Authorization": f"Bearer {registered['access_token']}"}).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]}).status_code == 401
    with sessions() as session:
        user = session.get(User, registered["id"])
        user.is_active = True
        user.hashed_password = "invalid-hash"
        session.commit()
    assert client.post("/api/v1/auth/login", json={"email": "regression@example.com", "password": "TestPassword123!"}).status_code == 401


@pytest.mark.parametrize("password", ["x" * 73, "é" * 37])
def test_new_password_byte_limit_is_safe_and_not_logged(auth_client, password, caplog):
    client, _ = auth_client
    response = client.post("/api/v1/auth/register", json={"full_name": "Test", "email": "limit@example.com", "password": password})
    assert response.status_code == 422
    assert password not in caplog.text


def test_json_logging_mode_formats_records():
    record = logging.LogRecord("auth-test", logging.INFO, __file__, 1, "Request completed with %s", (200,), None)
    data = json.loads(JsonFormatter().format(record))
    assert data["message"] == "Request completed with 200"
    assert data["level"] == "INFO"
