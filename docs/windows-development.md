# Windows development

Use a native Windows CPython installation (Python 3.11 or 3.12), Node.js LTS with npm, and PowerShell. Virtual environments and `node_modules` are local installation outputs: recreate them after cloning or moving the checkout. Never copy a virtual environment from another project location.

## Setup and recovery

From the repository root:

```powershell
Set-Location D:\ClinicalAI
python --version
node --version
.\scripts\setup.ps1
```

If `.venv` came from the previous project directory, close Python servers and terminals using it, then run:

```powershell
if (Get-Command deactivate -ErrorAction SilentlyContinue) { deactivate }
.\scripts\setup.ps1 -RecreateVenv
```

The script resolves the base Python interpreter before moving `.venv`, retains the old environment under `.venv.backup-<timestamp>`, and creates a new `.venv`. It installs dependencies using `python -m pip`, runs `pip check`, installs the frontend with `npm ci`, and validates the configured storage directories. It never deletes databases or uploaded files, and never overwrites an existing `.env`.

If `python` points to an unavailable Windows Store alias, select an installed native interpreter explicitly:

```powershell
.\scripts\setup.ps1 -RecreateVenv -Python 'C:\Path\To\Python311\python.exe'
```

When PowerShell blocks a downloaded script, use a process-scoped execution-policy override; no permanent policy change is required:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -RecreateVenv
```

Manual equivalent, if scripts are not desired:

```powershell
Set-Location D:\ClinicalAI
if (Get-Command deactivate -ErrorAction SilentlyContinue) { deactivate }
# Close servers before renaming this local installation directory.
if (Test-Path -LiteralPath .\.venv) {
    Rename-Item -LiteralPath .\.venv -NewName ".venv.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
}
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
if (-not (Test-Path -LiteralPath .\.env)) { Copy-Item .\.env.example .\.env }
.\.venv\Scripts\python.exe .\scripts\check_environment.py
npm.cmd --prefix .\frontend ci
```

Do not repair embedded paths in `pip.exe` or `uvicorn.exe`. Activation is optional: these commands use the environment's Python executable directly.

## Start both services

Open two PowerShell windows. From the checkout root:

```powershell
# Window 1
.\scripts\start-backend.ps1
```

```powershell
# Window 2
.\scripts\start-frontend.ps1
```

The scripts resolve paths relative to themselves, so this also works from another directory:

```powershell
& 'D:\ClinicalAI\scripts\start-backend.ps1'
& 'D:\ClinicalAI\scripts\start-frontend.ps1'
```

Use separate windows for those two long-running commands. Press Ctrl+C in each to stop. Add `-NoReload` to the backend script for a single-process server.

The backend script reads host and port from `.env` through the same settings object as FastAPI. It prepares parent directories before database initialization and launches `python -m uvicorn app.main:app --app-dir <backend-path>`. It does not depend on stale standalone launchers or the current working directory.

Direct equivalents with default ports, from the checkout root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --reload-dir backend
npm.cmd --prefix frontend run dev
```

The second command must run in another terminal. Running plain `npm run dev` in the repository root cannot work because its `package.json` is in `frontend`; use `--prefix frontend` or `Set-Location frontend`.

## Environment and API connection

The shared environment file is the checkout's `.env`. Setup creates it from `.env.example` only when absent. It remains ignored by Git. Vite also reads this file, but exposes only `VITE_` variables to browser code.

Defaults:

```dotenv
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=5173
VITE_API_BASE_URL=/api/v1
DATABASE_URL=sqlite:///./backend/data/clinicalai.db
UPLOAD_DIRECTORY=backend/data/uploads
```

Open `http://127.0.0.1:5173`; backend API documentation is at `http://127.0.0.1:8000/docs`. Browser requests use `/api/v1`, and Vite proxies `/api` to the configured backend host/port. A wildcard bind address is converted to loopback for the proxy. Vite uses a strict frontend port so a busy port is reported instead of silently changing the URL.

Restart Vite after changing port settings. Backend host and port can also be overridden by process environment variables. Relative SQLite and upload paths resolve against the checkout rather than the terminal's working directory. An intentionally absolute data path remains absolute after a move; review those settings yourself before changing them.

Provider API keys are required only for AI analysis. Login and patient entry do not require them. Invalid configuration is reported by `scripts/check_environment.py` using field names without printing secret values.

## Verification

From the checkout root:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe .\scripts\check_environment.py
.\.venv\Scripts\python.exe -m pytest
npm.cmd --prefix frontend run build
```

Browser regression tests:

```powershell
Set-Location frontend
npx.cmd playwright install chromium
npm.cmd test
```

Backend tests use isolated fixtures and migration tests use temporary databases. Browser tests intercept synthetic API records. They do not call a live AI provider. See [authentication investigation](authentication-fix.md) for the independently fixed profile response error and existing-account verification:

```powershell
# With the real backend running, from the checkout root:
.\.venv\Scripts\python.exe scripts\verify_auth.py
```

The helper prompts for the password without displaying it. The previous authentication HTTP 500 was caused by missing profile timestamps, independently of the relocated virtual environment. Preserve that fix when changing setup files; do not reset the users database.
