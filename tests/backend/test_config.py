from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.core.config import Settings, get_settings


def test_settings_exposes_core_runtime_options() -> None:
    settings = Settings()

    assert settings.database_url
    assert settings.api_v1_prefix
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.debug is True
    assert settings.log_level == "INFO"
    assert settings.log_format
    assert settings.secret_key
    assert settings.allowed_cors_origins
    assert settings.upload_directory
    assert settings.max_upload_size_mb > 0
    assert settings.allowed_file_extensions
    assert settings.ai_provider
    assert settings.ocr_provider
    assert settings.storage_provider
    assert settings.default_page_size > 0
    assert settings.max_page_size > 0
    assert settings.timezone


def test_database_path_is_project_relative() -> None:
    settings = get_settings()
    resolved = settings.resolve_database_path()

    assert resolved.is_absolute()
    assert resolved == (Path(settings.project_root) / "backend" / "data" / "clinicalai.db")
