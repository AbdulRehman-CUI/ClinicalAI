"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


def _default_database_url() -> str:
    """Return a project-relative SQLite database URL that is independent from cwd."""
    db_path = (ROOT_DIR / "backend" / "data" / "clinicalai.db").resolve()
    return f"sqlite:///{db_path.as_posix()}"


def _parse_csv(value: Any) -> list[str]:
    """Parse comma-separated environment values into a clean list."""
    if value is None:
        return []
    if isinstance(value, str):
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
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        validation_alias=AliasChoices("SECRET_KEY", "APP_SECRET_KEY"),
        description="Secret key used for signing and internal security features",
    )
    database_url: str = Field(
        default_factory=_default_database_url,
        validation_alias=AliasChoices("DATABASE_URL"),
        description="SQLAlchemy database URL for SQLite or PostgreSQL",
    )
    database_pool_size: int = Field(default=5, ge=1, description="Database pool size for future PostgreSQL usage")
    database_max_overflow: int = Field(default=10, ge=0, description="Database pool overflow for future PostgreSQL usage")
    database_pool_timeout: int = Field(default=30, ge=1, description="Database pool timeout for future PostgreSQL usage")
    allowed_cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
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
        validation_alias=AliasChoices("MAX_UPLOAD_SIZE", "MAX_UPLOAD_SIZE_MB"),
        description="Maximum size for uploaded files in megabytes",
    )
    allowed_file_extensions: list[str] = Field(
        default_factory=lambda: ["PDF", "DOCX", "TXT", "PNG", "JPG", "JPEG"],
        validation_alias=AliasChoices("ALLOWED_FILE_TYPES", "ALLOWED_FILE_EXTENSIONS"),
        description="Allowed file extensions for uploads",
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY"),
        description="API key used by the OpenAI integration",
    )
    gemini_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_API_KEY"),
        description="API key used by the Gemini integration",
    )
    ai_provider: str = Field(default="openai", description="AI provider identifier")
    jwt_secret_key: str = Field(
        default="dev-jwt-secret-change-in-production",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
        description="Secret key used to sign JWT access tokens",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=30, ge=1, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, ge=1, description="Refresh token expiration in days")
    password_hash_rounds: int = Field(default=12, ge=4, le=31, description="Bcrypt cost factor")
    auth_enabled: bool = Field(default=True, description="Enable authentication and authorization enforcement")
    security_headers_enabled: bool = Field(default=True, description="Enable security headers middleware")
    max_request_size_mb: int = Field(default=20, ge=1, description="Maximum request size in megabytes")
    openai_model: str = Field(default="gpt-4o-mini", description="Default OpenAI model name")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Default Gemini model name")
    openai_temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Temperature used for AI generation")
    openai_timeout: int = Field(default=60, ge=1, description="Timeout in seconds for model requests")
    ocr_provider: str = Field(default="tesseract", description="OCR provider identifier")
    ocr_language: str = Field(default="eng", description="Default OCR language")
    ocr_timeout: int = Field(default=60, ge=1, description="Timeout in seconds for OCR requests")
    storage_provider: str = Field(default="local", description="Storage provider identifier")
    local_storage_path: str = Field(
        default="backend/data/storage",
        description="Local storage path for future file-based storage scenarios",
    )
    default_page_size: int = Field(default=20, ge=1, description="Default pagination page size")
    max_page_size: int = Field(default=100, ge=1, description="Maximum pagination page size")
    timezone: str = Field(default="UTC", description="Default application timezone")
    date_format: str = Field(default="%Y-%m-%d", description="Default date format for display and serialization")
    token_expiration_minutes: int = Field(default=60, ge=1, description="Default token expiration in minutes")
    algorithm: str = Field(default="HS256", description="Default signing algorithm")
    max_ai_tokens: int = Field(default=2048, ge=1, description="Maximum number of tokens for AI responses")
    max_report_size: int = Field(default=10, ge=1, description="Maximum supported report size in megabytes for AI processing")
    max_context_length: int = Field(default=12000, ge=1, description="Maximum context length used when building prompts")

    @field_validator("allowed_cors_origins", mode="before")
    @classmethod
    def parse_allowed_cors_origins(cls, value: Any) -> list[str]:
        """Support comma-separated CORS origins from the environment."""
        parsed = _parse_csv(value)
        return [item.strip() for item in parsed if item.strip()]

    @field_validator("ai_provider", mode="before")
    @classmethod
    def normalize_ai_provider(cls, value: Any) -> str:
        """Normalize AI provider names so the environment accepts openai or gemini."""
        if value is None:
            return "openai"
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"openai", "gemini"}:
                return normalized
        return str(value).strip().lower()

    @field_validator("allowed_file_extensions", mode="before")
    @classmethod
    def parse_allowed_file_extensions(cls, value: Any) -> list[str]:
        """Support comma-separated file extension lists from the environment."""
        parsed = _parse_csv(value)
        return [item.strip().upper() for item in parsed if item.strip()]

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: Any) -> str:
        """Ensure SQLite URLs are resolved relative to the project root."""
        if value in (None, ""):
            return _default_database_url()
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return _default_database_url()
            if normalized.startswith("sqlite"):
                prefix = "sqlite:///"
                if normalized.startswith(prefix):
                    relative_path = normalized[len(prefix) :]
                    if relative_path.startswith("./"):
                        relative_path = relative_path[2:]
                    path = Path(relative_path)
                    if not path.is_absolute():
                        path = (ROOT_DIR / path).resolve()
                    return f"sqlite:///{path.as_posix()}"
            return normalized
        return str(value)

    @property
    def backend_cors_origins(self) -> list[str]:
        """Backward-compatible alias for the CORS origins field."""
        return self.allowed_cors_origins

    @property
    def effective_allowed_cors_origins(self) -> list[str]:
        """Return the configured CORS allow-list combined with the frontend URL when provided."""
        origins = list(self.allowed_cors_origins)
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins

    def resolve_database_path(self) -> Path:
        """Resolve the SQLite database path to an absolute filesystem path."""
        if not self.database_url.startswith("sqlite"):
            return self.project_root
        path_value = self.database_url.removeprefix("sqlite:///")
        path = Path(path_value)
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

