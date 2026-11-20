"""Per-workspace LLM credentials, validation, and request budgets."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from time import time
from typing import Literal
from uuid import uuid4
import re

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import case, delete, or_, select, update
from sqlalchemy.orm import Session

from app.ai.providers import BaseAIProvider, build_ai_provider, provider_error
from app.core.config import get_settings
from app.db.models import GuestWorkspace, WorkspaceLLMConfiguration
from app.services.exceptions import LLMRequestError

Provider = Literal["openai", "gemini", "openrouter", "anthropic", "groq", "custom"]


class LLMSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    base_url: str | None = Field(default=None, max_length=2048)
    provider: Provider
    model: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/+@-]*$")
    api_key: SecretStr | None = Field(default=None, min_length=1, max_length=4096)


class LLMSave(LLMSelection):
    remember: bool = False


class LLMStatus(BaseModel):
    id: str | None = None
    active: bool = False
    base_url: str | None = None
    configured: bool
    provider: Provider | None = None
    model: str | None = None
    has_api_key: bool = False
    tested: bool = False
    remember: bool = False
    expires_at: datetime | None = None


def model_registry() -> dict[str, list[str]]:
    settings = get_settings()
    return {"openai": settings.openai_models, "gemini": settings.gemini_models,
            "openrouter": ["openai/gpt-4.1-mini"], "anthropic": ["claude-sonnet-4-5"],
            "groq": ["llama-3.3-70b-versatile"], "custom": []}


def _cipher() -> Fernet:
    key = get_settings().llm_encryption_key
    if not key:
        raise LLMRequestError("llm_storage_unavailable", "Encrypted LLM configuration is unavailable.", 503)
    return Fernet(key.encode())


def _active_config(db: Session) -> WorkspaceLLMConfiguration | None:
    return db.scalar(select(WorkspaceLLMConfiguration).where(
        WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"],
        WorkspaceLLMConfiguration.active.is_(True),
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
        id=config.id, active=config.active, base_url=config.base_url, configured=usable,
        provider=config.provider, model=config.model, has_api_key=True, tested=usable,
        remember=config.session_hash is None,
        expires_at=expiry.astimezone(timezone.utc) if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc),
    )


def _binding(workspace_id: str, provider: str, model: str) -> bytes:
    return f"{workspace_id}:{provider}:{model}:".encode()


def _decrypt(config: WorkspaceLLMConfiguration) -> str:
    try:
        plaintext = _cipher().decrypt(config.encrypted_api_key.encode())
        binding = _binding(config.workspace_id, config.provider, config.model)
        if config.base_url:
            binding += (config.base_url + ":").encode()
        if plaintext.startswith(binding):
            return plaintext[len(binding):].decode()
    except (InvalidToken, UnicodeError):
        pass
    raise LLMRequestError("llm_key_unreadable", "Save your provider key again to use this configuration.", 409)


def _check_model(provider: str, model: str) -> None:
    if provider not in model_registry() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,254}", model):
        raise LLMRequestError("llm_model_unsupported", "Enter a valid text generation model identifier.", 422)


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
    config = _active_config(db)
    if config is None:
        raise LLMRequestError("llm_not_configured", "Configure an LLM before running analysis.", 409)
    provider, model, key, base_url = config.provider, config.model, _decrypt(config), config.base_url
    _check_model(provider, model)
    _consume_budget(db)
    return _build(provider, model, key, base_url)


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
        config = _selected(db, selection.id)
        if config is None or config.provider != selection.provider or config.base_url != selection.base_url:
            raise LLMRequestError("llm_key_required", "Enter the API key for this provider.", 422)
        key = _decrypt(config)
    _consume_budget(db)
    try:
        _build(selection.provider, selection.model, key, selection.base_url).test_connection()
    except Exception as exc:
        raise provider_error(exc) from None
    return key


def _build(provider, model, key, base_url=None):
    if provider == "custom":
        return build_ai_provider(provider, model, key, base_url=base_url)
    if base_url:
        raise LLMRequestError("llm_endpoint_invalid", "Only Custom endpoint accepts a base URL.", 422)
    return build_ai_provider(provider, model, key)


def _selected(db, identifier):
    config = db.scalar(select(WorkspaceLLMConfiguration).where(
        WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"],
        WorkspaceLLMConfiguration.id == identifier,
        WorkspaceLLMConfiguration.expires_at > datetime.now(timezone.utc),
        or_(WorkspaceLLMConfiguration.session_hash.is_(None),
            WorkspaceLLMConfiguration.session_hash == db.info.get("llm_session_hash")),
    )) if identifier else _active_config(db)
    return config


def list_configurations(db):
    rows = db.scalars(select(WorkspaceLLMConfiguration).where(
        WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"])).all()
    result = []
    for row in rows:
        usable = _selected(db, row.id) is not None
        try:
            _decrypt(row)
        except LLMRequestError:
            usable = False
        result.append(LLMStatus(id=row.id, active=row.active, base_url=row.base_url,
            configured=usable, provider=row.provider, model=row.model, has_api_key=True,
            tested=usable, remember=row.session_hash is None, expires_at=row.expires_at))
    return result


def activate_configuration(db, identifier):
    # Serialize active-selection changes within a workspace.
    db.execute(select(GuestWorkspace).where(GuestWorkspace.id == db.info["workspace_id"]).with_for_update())
    config = _selected(db, identifier)
    if config is None:
        raise LLMRequestError("llm_not_configured", "This configuration has expired or is unavailable in this browser session.", 409)
    _decrypt(config)
    db.execute(update(WorkspaceLLMConfiguration).where(
        WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"]).values(active=False))
    config.active = True
    db.commit()
    return configuration_status(db)


def save_configuration(db: Session, selection: LLMSave) -> tuple[LLMStatus, str | None]:
    cipher = _cipher()
    key = test_selection(db, selection)
    workspace_id = db.info["workspace_id"]
    db.execute(select(GuestWorkspace).where(GuestWorkspace.id == workspace_id).with_for_update())
    config = _selected(db, selection.id) if selection.id else None
    if selection.id and config is None:
        raise LLMRequestError("llm_not_configured", "Configuration unavailable. Add a new configuration.", 409)
    session_token = None
    session_hash = None
    if not selection.remember:
        session_token = db.info.get("llm_session_token") if db.info.get("llm_session_hash") else token_urlsafe(32)
        session_hash = sha256(session_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + (timedelta(days=7) if selection.remember else timedelta(hours=8))
    if config is None:
        has_any = db.scalar(select(WorkspaceLLMConfiguration.id).where(WorkspaceLLMConfiguration.workspace_id == workspace_id))
        config = WorkspaceLLMConfiguration(id=uuid4().hex, workspace_id=workspace_id, active=has_any is None)
        db.add(config)
    binding = _binding(workspace_id, selection.provider, selection.model)
    if selection.base_url:
        binding += (selection.base_url + ":").encode()
    config.provider, config.model, config.base_url = selection.provider, selection.model, selection.base_url
    config.encrypted_api_key = cipher.encrypt(binding + key.encode()).decode()
    config.session_hash, config.expires_at = session_hash, expires_at
    db.commit()
    return LLMStatus(id=config.id, active=config.active, base_url=config.base_url, configured=True,
        provider=config.provider, model=config.model, has_api_key=True, tested=True,
        remember=selection.remember, expires_at=expires_at), session_token


def remove_configuration(db: Session, identifier=None) -> None:
    config = _selected(db, identifier) if not identifier else db.scalar(select(WorkspaceLLMConfiguration).where(
        WorkspaceLLMConfiguration.workspace_id == db.info["workspace_id"], WorkspaceLLMConfiguration.id == identifier))
    if config:
        db.delete(config)
        db.commit()


class LLMDiscovery(LLMSelection):
    model: str = "discovery"


def discover_models(db, selection):
    # Discovery never implies a model has been tested successfully.
    if selection.api_key:
        key = selection.api_key.get_secret_value()
    else:
        config = _selected(db, selection.id)
        if not config or config.provider != selection.provider or config.base_url != selection.base_url:
            raise LLMRequestError("llm_key_required", "Enter a key before loading models.", 422)
        key = _decrypt(config)
    _consume_budget(db)
    try:
        models = _build(selection.provider, "discovery", key, selection.base_url).discover_models()
        return sorted({m for m in models if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,254}", m)})
    except Exception as exc:
        raise provider_error(exc) from None


if __name__ == "__main__":
    from app.db.session import SessionLocal

    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as session:
        result = session.execute(delete(WorkspaceLLMConfiguration).where(or_(
            WorkspaceLLMConfiguration.expires_at <= now,
            WorkspaceLLMConfiguration.workspace_id.in_(select(GuestWorkspace.id).where(GuestWorkspace.expires_at <= now)),
        )))
        print(f"Removed {result.rowcount} expired LLM configurations.")
