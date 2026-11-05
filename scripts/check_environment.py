"""Validate development settings and prepare directories without opening the database."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print only non-secret startup settings")
    args = parser.parse_args()
    try:
        from pydantic import ValidationError
        from pydantic_settings.exceptions import SettingsError
        from app.core.config import get_settings
    except ImportError:
        print("Backend dependencies are missing. Run scripts/setup.ps1.", file=sys.stderr)
        return 1
    try:
        settings = get_settings()
    except ValidationError as error:
        fields = ", ".join(".".join(map(str, item["loc"])) for item in error.errors())
        print(f"Invalid backend configuration in .env or process environment: {fields}. Check .env.example for valid values.", file=sys.stderr)
        return 1
    except SettingsError:
        print("Cannot parse backend configuration. Check .env; list settings must be valid JSON arrays.", file=sys.stderr)
        return 1
    try:
        database = settings.resolve_database_path() if settings.database_url.startswith("sqlite") else None
        if database:
            database.parent.mkdir(parents=True, exist_ok=True)
        uploads = settings.resolve_upload_directory()
        uploads.mkdir(parents=True, exist_ok=True)
        settings.resolve_local_storage_path().mkdir(parents=True, exist_ok=True)
    except OSError:
        print("Cannot prepare database or upload directories. Check the configured paths and Windows folder permissions. No files were deleted.", file=sys.stderr)
        return 1
    result = {"host": settings.host, "port": settings.port, "database": str(database) if database else "Configured external database", "upload_directory": str(uploads), "ai_provider": settings.ai_provider, "ai_configured": bool(settings.openai_api_key if settings.ai_provider == "openai" else settings.gemini_api_key)}
    if args.json:
        print(json.dumps(result))
    else:
        print(f"Backend configuration valid: {settings.host}:{settings.port}")
        print(f"Database location: {result['database']}")
        print(f"Uploads directory: {uploads}")
        if not result["ai_configured"]:
            print(f"AI analysis requires the selected {settings.ai_provider} API key; it is not needed for login.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
