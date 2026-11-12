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
        env={**os.environ, "DIRECT_DATABASE_URL": "", "DATABASE_URL": f"sqlite:///{db_path.as_posix()}"},
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
        "report_storage_deletions",
        "guest_workspaces",
        "workspace_llm_configurations",
    }

    assert expected_tables.issubset(tables)


def test_workspace_migration_preserves_legacy_rows_without_assigning_them(tmp_path: Path) -> None:
    backend = Path(__file__).resolve().parents[2] / "backend"
    db_path = tmp_path / "legacy.db"
    env = os.environ | {"DIRECT_DATABASE_URL": "", "DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}

    def upgrade(revision: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", revision],
            cwd=backend, env=env, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    upgrade("20261112_0001")
    with sqlite3.connect(db_path) as connection:
        connection.execute("""
            INSERT INTO patients (id, first_name, last_name, age, biological_sex, blood_group, height_cm, weight_kg)
            VALUES (1, 'Legacy', 'Patient', 30, 'Female', 'A+', 165, 62)
        """)
        connection.execute("""
            INSERT INTO medical_reports (patient_id, original_filename, stored_filename, file_type, extracted_text)
            VALUES (1, 'report.txt', 'legacy.txt', 'TXT', 'synthetic text')
        """)
        connection.execute("""
            INSERT INTO users (full_name, email, hashed_password, role, is_active)
            VALUES ('Legacy User', 'legacy@example.com', 'synthetic-hash', 'Staff', 1)
        """)
    upgrade("head")
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT first_name, workspace_id FROM patients").fetchall() == [("Legacy", None)]
        assert connection.execute("SELECT stored_filename, extracted_text FROM medical_reports").fetchall() == [
            ("legacy.txt", "synthetic text"),
        ]
        assert connection.execute("SELECT email FROM users").fetchall() == [("legacy@example.com",)]
