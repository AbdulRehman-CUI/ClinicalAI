import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_alembic_upgrade_head_creates_expected_tables(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    db_path = tmp_path / "migrations.db"

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(backend_dir), "DATABASE_URL": f"sqlite:///{db_path.as_posix()}"},
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }

    expected_tables = {
        "patients",
        "medical_histories",
        "medications",
        "allergies",
        "symptoms",
        "medical_reports",
        "ai_analyses",
        "alembic_version",
        "users",
    }

    assert expected_tables.issubset(tables)
