# ClinicalAI

ClinicalAI is a layered clinical decision support system foundation. The current repository contains only project boilerplate: React frontend shell, FastAPI backend shell, database wiring, tests, and Docker support.

## Architecture

- Frontend: React, TypeScript, Vite, Tailwind CSS, React Router, Axios, React Hook Form
- Backend: Python 3.12+, FastAPI, SQLAlchemy, Alembic, Pydantic, Uvicorn, python-dotenv
- Database: SQLite for development
- AI: OpenAI dependency is declared for future backend-only integration, but no AI logic is implemented yet

## Local Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload
```

## Local Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Docker

```powershell
docker compose up --build
```

The frontend is served on `http://localhost:5173` and the backend API is served on `http://localhost:8000`.

