# ClinicalAI - Phase 12 Deployment

## Objective

Prepare the ClinicalAI application for production deployment without changing any existing business logic.

The application currently consists of:

Frontend
- React
- TypeScript
- Vite
- Axios

Backend
- Python
- FastAPI
- SQLAlchemy
- Alembic
- JWT Authentication
- OpenAI/Gemini integration layer (currently optional)
- SQLite (current development database)

The existing CRUD endpoints, authentication, AI workflow, and frontend functionality are already working.

Do NOT rewrite existing features.

---

# Goals

## 1. Dockerize the complete application

Create production-ready Dockerfiles for:

- frontend
- backend

Use multi-stage builds where appropriate.

---

## 2. Docker Compose

Create a production-ready docker-compose.yml that starts:

- frontend
- backend

Use named volumes where appropriate.

Use environment variables instead of hardcoded values.

---

## 3. Environment Variables

Move every configurable value into environment variables.

Examples:

OPENAI_API_KEY

JWT_SECRET_KEY

DATABASE_URL

UPLOAD_DIRECTORY

ALLOWED_FILE_TYPES

MAX_UPLOAD_SIZE

BACKEND_HOST

BACKEND_PORT

FRONTEND_URL

CORS_ORIGINS

Never hardcode secrets.

---

## 4. Production Backend

Configure FastAPI for production.

Requirements:

- production logging
- proper startup/shutdown
- health endpoint
- graceful error handling
- CORS configuration
- secure defaults

---

## 5. Frontend Production

The frontend should:

read the backend URL from environment variables.

work correctly after build.

No localhost should remain hardcoded.

---

## 6. File Uploads

Uploaded reports must persist using Docker volumes.

Uploads must survive container restarts.

---

## 7. Database

Keep SQLite for now.

Do NOT migrate to PostgreSQL.

Simply make SQLite persistent using Docker volumes.

---

## 8. Documentation

Create:

README.md

with:

Project overview

Architecture

Setup instructions

Docker deployment

Environment variables

Running locally

Running with Docker

Common troubleshooting

Folder structure

API overview

---

## 9. Deployment Scripts

Create helper scripts where appropriate.

Examples:

start.bat

start.sh

stop.sh

rebuild.sh

Only if useful.

---

## 10. Production Readiness

Ensure:

✓ no hardcoded paths

✓ no hardcoded localhost

✓ configurable ports

✓ environment variables documented

✓ upload persistence

✓ API remains backward compatible

✓ frontend communicates correctly with backend

---

# Important

Do NOT modify business logic.

Do NOT rewrite CRUD services.

Do NOT change authentication.

Do NOT change AI workflow.

Deployment only.

Maintain the existing architecture.