"""Exercise preflight from another working directory without touching project data."""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def test_preflight_prepares_directories_without_creating_database(tmp_path):
    database = tmp_path / "nested" / "data" / "test.db"
    uploads = tmp_path / "uploads"
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{database.as_posix()}",
        "UPLOAD_DIRECTORY": str(uploads),
        "LOCAL_STORAGE_PATH": str(tmp_path / "storage"),
        "BACKEND_HOST": "127.0.0.1",
        "BACKEND_PORT": "8123",
        "AI_PROVIDER": "openai",
        "OPENAI_API_KEY": "",
    }
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_environment.py"), "--json"], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    configuration = json.loads(result.stdout)
    assert configuration["host"] == "127.0.0.1"
    assert configuration["port"] == 8123
    assert configuration["ai_configured"] is False
    assert database.parent.is_dir()
    assert uploads.is_dir()
    assert not database.exists()


def test_invalid_configuration_reports_field_without_echoing_value(tmp_path):
    invalid_value = "private-invalid-configuration-value"
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_environment.py"), "--json"], cwd=tmp_path, env={**os.environ, "BACKEND_PORT": invalid_value}, capture_output=True, text=True)
    assert result.returncode == 1
    assert "BACKEND_PORT" in result.stderr
    assert invalid_value not in result.stdout + result.stderr
