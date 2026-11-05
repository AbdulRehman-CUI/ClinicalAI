# Development scripts

- `setup.ps1`: create/install the local Python and frontend environments. `-RecreateVenv` retains the old environment as a backup before creating a fresh one. `-Python <path>` selects a base interpreter; `-SkipFrontend` installs only the backend.
- `start-backend.ps1`: validate configuration, prepare storage directories, then start `python -m uvicorn` with the configured host/port. `-NoReload` disables the development reloader.
- `start-frontend.ps1`: start Vite from the correct frontend package directory.
- `check_environment.py`: validate backend settings and prepare directories without opening or changing database contents. `--json` prints only non-secret startup settings.
- `verify_auth.py`: securely prompt for an existing account and verify login, profile retrieval, refresh, and logout without printing passwords or tokens.

PowerShell scripts resolve paths relative to this directory. Invoke long-running backend/frontend scripts in separate terminals. See [Windows development](../docs/windows-development.md) for full commands and recovery instructions.

