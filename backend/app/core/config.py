"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
import json
import os
import re
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import AliasChoices, Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000")
DEV_SECRET = "dev-secret-key-change-in-production"


def _default_database_url() -> str:
    """Return a project-relative SQLite database URL that is independent from cwd."""
    db_path = (ROOT_DIR / "backend" / "data" / "clinicalai.db").resolve()
    return f"sqlite:///{db_path.as_posix()}"


def _parse_csv(value: Any) -> list[str]:
    """Parse comma-separated environment values into a clean list."""
    if value is None:
        return []
    if isinstance(value, str):
        if value.lstrip().startswith("["):
            return _parse_csv(json.loads(value))
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


class Settings(BaseSettings):
    """Typed settings used by the backend application."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    project_name: str = Field(default="ClinicalAI", description="Human-readable application name")
    project_root: Path = Field(default_factory=lambda: ROOT_DIR, description="Absolute path to the repository root")
    api_version: str = Field(default="0.1.0", description="API version exposed by the backend")
    api_v1_prefix: str = Field(
        default="/api/v1",
        validation_alias=AliasChoices("API_V1_PREFIX", "API_PREFIX"),
        description="Base API prefix used by the router",
    )
    environment: str = Field(default="development", description="Runtime environment name")
    host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("BACKEND_HOST", "HOST"),
        description="Host interface used by the ASGI server",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("BACKEND_PORT", "PORT"),
        description="Port used by the ASGI server",
    )
    debug: bool = Field(default=True, description="Enable debug mode for local development")
    log_level: str = Field(default="INFO", description="Logging level for the backend")
    log_format: str = Field(
        default="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        description="Logging format string",
    )
    workspace_signing_secret: str = Field(default=DEV_SECRET, validation_alias=AliasChoices("WORKSPACE_SIGNING_SECRET", "SECRET_KEY"))
    llm_encryption_key: str | None = None
    frontend_port: int = Field(default=5173, ge=1, le=65535)
    openai_models: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["gpt-4.1-mini", "gpt-4o-mini"])
    gemini_models: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["gemini-3.6-flash", "gemini-3.5-flash-lite"])
    database_url: str = Field(
        default_factory=_default_database_url,
        validation_alias=AliasChoices("DATABASE_URL"),
        description="SQLAlchemy database URL for SQLite or PostgreSQL",
    )
    direct_database_url: str | None = None
    database_pool_size: int = Field(default=5, ge=1, description="Database pool size for future PostgreSQL usage")
    database_max_overflow: int = Field(default=10, ge=0, description="Database pool overflow for future PostgreSQL usage")
    database_pool_timeout: int = Field(default=30, ge=1, description="Database pool timeout for future PostgreSQL usage")
    allowed_cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: list(DEFAULT_ORIGINS),
        validation_alias=AliasChoices("ALLOWED_CORS_ORIGINS", "ALLOWED_ORIGINS", "BACKEND_CORS_ORIGINS", "CORS_ORIGINS"),
        description="Allowed origins for CORS requests",
    )
    frontend_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FRONTEND_URL"),
        description="Public frontend URL used to shape CORS configuration",
    )
    upload_directory: str = Field(
        default="backend/data/uploads",
        validation_alias=AliasChoices("UPLOAD_DIRECTORY", "UPLOAD_DIR"),
        description="Directory used to persist uploaded reports",
    )
    max_upload_size_mb: int = Field(
        default=20,
        ge=1,
        validation_alias=AliasChoices("MAX_UPLOAD_SIZE_MB", "MAX_UPLOAD_SIZE"),
        description="Maximum size for uploaded files in megabytes",
    )
    allowed_file_extensions: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["PDF", "DOCX", "TXT", "PNG", "JPG", "JPEG"],
        validation_alias=AliasChoices("ALLOWED_FILE_TYPES", "ALLOWED_FILE_EXTENSIONS"),
        description="Allowed file extensions for uploads",
    )
    security_headers_enabled: bool = Field(default=True, description="Enable security headers middleware")
    max_request_size_mb: int = Field(default=20, ge=1, description="Maximum request size in megabytes")
    openai_temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Temperature used for AI generation")
    openai_timeout: int = Field(default=60, ge=1, description="Timeout in seconds for model requests")
    ocr_provider: str = Field(default="tesseract", description="OCR provider identifier")
    ocr_language: str = Field(default="eng", description="Default OCR language")
    ocr_timeout: int = Field(default=60, ge=1, description="Timeout in seconds for OCR requests")
    storage_provider: Literal["local", "s3"] = "local"
    storage_bucket: str | None = None
    storage_endpoint: str | None = None
    storage_region: str = "us-east-1"
    storage_access_key_id: str | None = None
    storage_secret_access_key: str | None = None
    local_storage_path: str = Field(
        default="backend/data/storage",
        description="Local storage path for future file-based storage scenarios",
    )
    default_page_size: int = Field(default=20, ge=1, description="Default pagination page size")
    max_page_size: int = Field(default=100, ge=1, description="Maximum pagination page size")
    timezone: str = Field(default="UTC", description="Default application timezone")
    date_format: str = Field(default="%Y-%m-%d", description="Default date format for display and serialization")
    max_ai_tokens: int = Field(default=2048, ge=1, description="Maximum number of tokens for AI responses")
    max_report_size: int = Field(default=10, ge=1, description="Maximum supported report size in megabytes for AI processing")
    max_context_length: int = Field(default=12000, ge=1, description="Maximum context length used when building prompts")

    @field_validator("allowed_cors_origins", mode="before")
    @classmethod
    def parse_allowed_cors_origins(cls, value: Any) -> list[str]:
        """Support comma-separated CORS origins from the environment."""
        parsed = _parse_csv(value)
        return [item.strip() for item in parsed if item.strip()]

    @field_validator("openai_models", "gemini_models", mode="before")
    @classmethod
    def parse_models(cls, value: Any) -> list[str]:
        models = list(dict.fromkeys(_parse_csv(value)))
        if not models or any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", model) for model in models):
            raise ValueError("Model lists must contain valid provider model identifiers.")
        return models

    @field_validator("allowed_file_extensions", mode="before")
    @classmethod
    def parse_allowed_file_extensions(cls, value: Any) -> list[str]:
        """Support comma-separated file extension lists from the environment."""
        parsed = _parse_csv(value)
        return [item.strip().upper() for item in parsed if item.strip()]

    @field_validator("database_url", "direct_database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any, info: ValidationInfo) -> str | None:
        """Resolve relative SQLite paths and select the PostgreSQL driver."""
        normalized = str(value or "").strip()
        if not normalized:
            return None if info.field_name == "direct_database_url" else _default_database_url()
        try:
            url = make_url(normalized)
        except ArgumentError:
            raise ValueError("Invalid database URL.") from None
        if url.get_backend_name() == "sqlite":
            if info.field_name == "direct_database_url":
                raise ValueError("DIRECT_DATABASE_URL must use PostgreSQL.")
            if url.database and url.database != ":memory:" and not Path(url.database).is_absolute():
                url = url.set(database=(ROOT_DIR / url.database).resolve().as_posix())
            return url.render_as_string(hide_password=False)
        if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
            raise ValueError("Use a SQLite or PostgreSQL database URL.")
        url = url.set(drivername="postgresql+psycopg")
        if "sslmode" not in url.query:
            url = url.update_query_dict({"sslmode": "require"})
        return url.render_as_string(hide_password=False)

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @model_validator(mode="after")
    def validate_deployment(self) -> Settings:
        if os.environ.get("VERCEL") == "1" and not self.is_production:
            raise ValueError("Set ENVIRONMENT=production on the Vercel backend.")
        if self.storage_provider == "s3" and not all(
            value and value.strip() for value in
            (self.storage_bucket, self.storage_region, self.storage_access_key_id, self.storage_secret_access_key)
        ):
            raise ValueError("S3 storage requires STORAGE_BUCKET, STORAGE_REGION and both storage credentials.")
        if self.llm_encryption_key:
            try:
                Fernet(self.llm_encryption_key.encode())
            except (ValueError, TypeError):
                raise ValueError("LLM_ENCRYPTION_KEY must be a generated Fernet key.") from None
        if not self.is_production:
            return self
        if self.debug:
            raise ValueError("Production requires DEBUG=false.")
        secret = self.workspace_signing_secret
        if len(secret.strip().encode()) < 32 or secret == DEV_SECRET:
            raise ValueError("WORKSPACE_SIGNING_SECRET requires a generated secret of at least 32 bytes.")
        if not self.llm_encryption_key:
            raise ValueError("Production requires LLM_ENCRYPTION_KEY.")
        for value in filter(None, (self.database_url, self.direct_database_url)):
            url = make_url(value)
            if url.drivername != "postgresql+psycopg" or url.query.get("sslmode") not in {
                "require", "verify-ca", "verify-full"
            }:
                raise ValueError("Production requires a TLS-enabled PostgreSQL database URL.")
        if self.storage_provider != "s3":
            raise ValueError("Production requires STORAGE_PROVIDER=s3.")
        if self.storage_endpoint:
            endpoint = urlsplit(self.storage_endpoint)
            if endpoint.scheme != "https" or not endpoint.hostname:
                raise ValueError("STORAGE_ENDPOINT must use HTTPS in production.")
        origins = self.effective_allowed_cors_origins
        if not origins:
            raise ValueError("Configure FRONTEND_URL or ALLOWED_CORS_ORIGINS in production.")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https" or not parsed.hostname or "*" in origin
                or parsed.username is not None or parsed.password is not None
                or origin != f"https://{parsed.netloc}" or parsed.port == 0
            ):
                raise ValueError("CORS origins must be exact HTTPS origins without a path or wildcard.")
        return self

    @property
    def backend_cors_origins(self) -> list[str]:
        """Backward-compatible alias for the CORS origins field."""
        return self.allowed_cors_origins

    @property
    def effective_allowed_cors_origins(self) -> list[str]:
        """Return the configured CORS allow-list combined with the frontend URL when provided."""
        origins = list(self.allowed_cors_origins)
        if self.is_production and "allowed_cors_origins" not in self.model_fields_set:
            origins = []
        if not self.is_production:
            origins.extend(f"http://{host}:{self.frontend_port}" for host in ("localhost", "127.0.0.1"))
        if self.frontend_url:
            origins.append(self.frontend_url.strip().rstrip("/"))
        return list(dict.fromkeys(origins))

    def resolve_database_path(self) -> Path | None:
        """Resolve the SQLite database path to an absolute filesystem path."""
        url = make_url(self.database_url)
        if url.get_backend_name() != "sqlite" or url.database in {None, "", ":memory:"}:
            return None
        path = Path(url.database)
        if not path.is_absolute():
            path = (self.project_root / path).resolve()
        return path.resolve()

    def resolve_upload_directory(self) -> Path:
        """Resolve the upload directory to an absolute filesystem path."""
        return self._resolve_path(self.upload_directory, self.project_root / "backend" / "data" / "uploads")

    def resolve_local_storage_path(self) -> Path:
        """Resolve the local storage path to an absolute filesystem path."""
        return self._resolve_path(self.local_storage_path, self.project_root / "backend" / "data" / "storage")

    def _resolve_path(self, value: str, fallback: Path) -> Path:
        """Resolve a project-relative path to an absolute path."""
        if value in (None, ""):
            return fallback.resolve()
        path = Path(value)
        if not path.is_absolute():
            path = (self.project_root / path).resolve()
        return path.resolve()


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so dependencies share one configuration object."""
    return Settings()

