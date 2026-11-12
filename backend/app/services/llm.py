"""Per-workspace LLM credentials, validation, and request budgets."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from time import time
from typing import Literal

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import case, delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.ai.providers import BaseAIProvider, build_ai_provider, provider_error
from app.core.config import get_settings
from app.db.models import GuestWorkspace, WorkspaceLLMConfiguration
from app.services.exceptions import LLMRequestError

Provider = Literal["openai", "gemini"]


class LLMSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Provider
    model: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=4096)


class LLMSave(LLMSelection):
    remember: bool = False


class LLMStatus(BaseModel):
    configured: bool
    provider: Provider | None = None
    model: str | None = None
    has_api_key: bool = False
    tested: bool = False
    remember: bool = False
    expires_at: datetime | None = None


def model_registry() -> dict[str, list[str]]:
    settings = get_settings()
    return {"openai": settings.openai_models, "gemini": settings.gemini_models}


def _cipher() -> Fernet:
    key = get_settings().llm_encryption_key
    if not key:
        raise LLMRequestError("llm_storage_unavailable", "Encrypted LLM configuration is unavailable.", 503)
    return Fernet(key.encode())


def _active_config(db: Session) -> WorkspaceLLMConfiguration | None:
    return db.scalar(select(WorkspaceLLMConfiguration).where(
        WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"],
        WorkspaceLLMConfiguration.expires_at > datetime.now(timezone.utc),
        or_(
            WorkspaceLLMConfiguration.session_hash.is_(None),
            WorkspaceLLMConfiguration.session_hash == db.info.get("llm_session_hash"),
        ),
    ))


def configuration_status(db: Session) -> LLMStatus:
    config = _active_config(db)
    if config is None:
        saved = db.scalar(select(WorkspaceLLMConfiguration.workspace_id).where(
            WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"],
        ))
        return LLMStatus(configured=False, has_api_key=saved is not None)
    try:
        _check_model(config.provider, config.model)
        _decrypt(config)
        usable = True
    except LLMRequestError:
        usable = False
    expiry = config.expires_at
    return LLMStatus(
        configured=usable,
        provider=config.provider, model=config.model, has_api_key=True, tested=True,
        remember=config.session_hash is None,
        expires_at=expiry.astimezone(timezone.utc) if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc),
    )


def _binding(workspace_id: str, provider: str, model: str) -> bytes:
    return f"{workspace_id}:{provider}:{model}:".encode()


def _decrypt(config: WorkspaceLLMConfiguration) -> str:
    try:
        plaintext = _cipher().decrypt(config.encrypted_api_key.encode())
        binding = _binding(config.workspace_id, config.provider, config.model)
        if plaintext.startswith(binding):
            return plaintext[len(binding):].decode()
    except (InvalidToken, UnicodeError):
        pass
    raise LLMRequestError("llm_key_unreadable", "Save your provider key again to use this configuration.", 409)


def _check_model(provider: str, model: str) -> None:
    if model not in model_registry().get(provider, ()):
        raise LLMRequestError("llm_model_unsupported", "Choose a model supported by ClinicalAI.", 422)


def _consume_budget(db: Session) -> None:
    """Count outbound calls atomically across function instances."""
    bucket = int(time()) // 60
    same_bucket = GuestWorkspace.llm_rate_bucket == bucket
    accepted = db.scalar(update(GuestWorkspace).where(
        GuestWorkspace.id == db.info["workspace_id"],
        GuestWorkspace.expires_at > datetime.now(timezone.utc),
        or_(~same_bucket, GuestWorkspace.llm_rate_count < 8),
    ).values(
        llm_rate_bucket=bucket,
        llm_rate_count=case((same_bucket, GuestWorkspace.llm_rate_count + 1), else_=1),
    ).returning(GuestWorkspace.id))
    db.commit()
    if accepted is None:
        raise LLMRequestError("workspace_rate_limited", "Too many LLM requests. Try again in a minute.", 429)


def configured_provider(db: Session) -> BaseAIProvider:
    provider, model, key = require_configuration(db)
    _consume_budget(db)
    return build_ai_provider(provider, model, key)


def require_configuration(db: Session) -> tuple[str, str, str]:
    config = _active_config(db)
    if config is None:
        raise LLMRequestError("llm_not_configured", "Configure an LLM before running analysis.", 409)
    provider, model = config.provider, config.model
    _check_model(provider, model)
    return provider, model, _decrypt(config)


def test_selection(db: Session, selection: LLMSelection) -> str:
    _check_model(selection.provider, selection.model)
    if selection.api_key is not None:
        key = selection.api_key.get_secret_value().strip()
        if not key or any(not 33 <= ord(char) <= 126 for char in key):
            raise LLMRequestError("llm_invalid_key", "Enter a valid provider API key.", 422)
    else:
        config = _active_config(db)
        if config is None or config.provider != selection.provider:
            raise LLMRequestError("llm_key_required", "Enter the API key for this provider.", 422)
        key = _decrypt(config)
    _consume_budget(db)
    try:
        build_ai_provider(selection.provider, selection.model, key).test_connection()
    except Exception as exc:
        raise provider_error(exc) from None
    return key


def save_configuration(db: Session, selection: LLMSave) -> tuple[LLMStatus, str | None]:
    cipher = _cipher()
    key = test_selection(db, selection)
    workspace_id = db.info["workspace_id"]
    session_token = None if selection.remember else token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + (timedelta(days=7) if selection.remember else timedelta(hours=8))
    values = {
        "provider": selection.provider,
        "model": selection.model,
        "encrypted_api_key": cipher.encrypt(_binding(workspace_id, selection.provider, selection.model) + key.encode()).decode(),
        "session_hash": sha256(session_token.encode()).hexdigest() if session_token else None,
        "expires_at": expires_at,
    }
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else postgres_insert
    db.execute(insert(WorkspaceLLMConfiguration).values(workspace_id=workspace_id, **values).on_conflict_do_update(
        index_elements=[WorkspaceLLMConfiguration.workspace_id], set_=values,
    ))
    db.commit()
    return LLMStatus(
        configured=True, provider=selection.provider, model=selection.model, has_api_key=True,
        tested=True, remember=selection.remember, expires_at=expires_at,
    ), session_token


def remove_configuration(db: Session) -> None:
    db.execute(delete(WorkspaceLLMConfiguration).where(
        WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"],
    ))
    db.commit()


if __name__ == "__main__":
    from app.db.session import SessionLocal

    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as session:
        result = session.execute(delete(WorkspaceLLMConfiguration).where(or_(
            WorkspaceLLMConfiguration.expires_at <= now,
            WorkspaceLLMConfiguration.workspace_id.in_(select(GuestWorkspace.id).where(GuestWorkspace.expires_at <= now)),
        )))
        print(f"Removed {result.rowcount} expired LLM configurations.")
