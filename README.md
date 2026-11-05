# ClinicalAI

A React/TypeScript clinical workspace with a FastAPI backend, SQLite persistence, JWT authentication, medical report uploads, and configurable AI decision support.

## Windows quick start

Install native Windows Python 3.11 or 3.12 and Node.js LTS with npm. From the checkout root:

```powershell
.\scripts\setup.ps1
```

After moving a checkout containing an old virtual environment, use `-RecreateVenv`. The old `.venv` is retained as a backup; `.env`, databases, accounts, and uploaded reports are preserved.

Start each service in a separate PowerShell window:

```powershell
.\scripts\start-backend.ps1
```

```powershell
.\scripts\start-frontend.ps1
```

Default frontend: `http://127.0.0.1:5173`. API documentation: `http://127.0.0.1:8000/docs`.

The startup scripts work from any current directory when invoked using their full paths. No virtual environment activation is required. They use `python -m pip` and `python -m uvicorn`, avoiding stale executable launchers.

Read the [Windows development guide](docs/windows-development.md) for safe environment recreation, manual commands, configuration, troubleshooting, tests, and frontend builds.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest
npm.cmd --prefix frontend run build
```

The shared `.env` is created only if missing and remains ignored by Git. Keep `VITE_API_BASE_URL=/api/v1` to use Vite's backend proxy. AI provider keys are required for analysis, independently of authentication.

For frontend browser tests, see [frontend/README.md](frontend/README.md). For the separately fixed authentication issue and secure existing-account verification, see [docs/authentication-fix.md](docs/authentication-fix.md).

## Docker

```powershell
docker compose up --build
```

The existing `start.bat` and `start.sh` launch Docker Compose; use the PowerShell scripts above for native local development. Docker uses its configured volumes, which are separate from a native Windows database unless explicitly mounted.
