# ClinicalAI

A React and FastAPI clinical workspace with anonymous guest workspaces, private report storage, and AI decision support powered by each visitor’s OpenAI or Gemini key.

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

The shared `.env` is created only if missing and remains ignored by Git. Keep `VITE_API_BASE_URL=/api/v1` to use Vite's backend proxy. To enable LLM configuration, generate a server-side key and set it as `LLM_ENCRYPTION_KEY` in `.env`.

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Open the dashboard and select **Configure LLM** to choose your provider and model. Patient workflows are available as soon as you open the app. Read the [guest workspace and BYOK guide](docs/GUEST_WORKSPACES.md) for browser continuity, credential handling, and retention.

## Vercel

Use the [Vercel deployment guide](docs/VERCEL_DEPLOYMENT.md) to configure the separate frontend and backend projects, Neon migrations, private report storage, and deployment checks.

## Docker

```powershell
docker compose up --build
```

The existing `start.bat` and `start.sh` launch Docker Compose; use the PowerShell scripts above for native local development. Docker uses its configured volumes, which are separate from a native Windows database unless explicitly mounted.
