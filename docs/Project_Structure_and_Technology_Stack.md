# ClinicalAI
## Project Structure and Technology Stack

Version: 1.0

---

# 1. Purpose

This document defines the overall technical architecture of ClinicalAI, the technologies used, the responsibilities of each component, and how they interact.

The goal is to create a modular, maintainable, scalable, and production-ready AI-powered Clinical Decision Support System.

---

# 2. High-Level Architecture

```
                        User
                         │
                         ▼
            React + TypeScript Frontend
                         │
                HTTPS / REST API
                         │
                         ▼
               FastAPI Backend Server
                         │
      ┌──────────────────┼──────────────────┐
      │                  │                  │
      ▼                  ▼                  ▼
Patient Service     AI Service      File Service
      │                  │                  │
      └──────────────────┼──────────────────┘
                         │
                  OpenAI API
                         │
              Clinical Reasoning
                         │
                         ▼
                  SQLite Database
                         │
                   Uploaded Reports
                         │
                    Local Storage

Entire Application
        │
 Docker Container
        │
Cloud Deployment
```

---

# 3. Technology Stack

## Frontend

Framework
- React

Language
- TypeScript

Build Tool
- Vite

Styling
- Tailwind CSS

Routing
- React Router

State Management
- React Context API

HTTP Client
- Axios

Form Validation
- React Hook Form

UI Icons
- Lucide React

Notifications
- React Hot Toast

Charts (Optional)
- Recharts

---

## Backend

Language

Python 3.12+

Framework

FastAPI

ASGI Server

Uvicorn

Validation

Pydantic

ORM

SQLAlchemy

Database Migration

Alembic

Authentication (Future)

JWT

Environment Variables

python-dotenv

Testing

Pytest

---

## Artificial Intelligence

Provider

OpenAI

Purpose

- Clinical reasoning
- Report summarisation
- Medication safety analysis
- Diagnosis assistance
- Structured JSON generation

The AI is only responsible for reasoning.

Business logic remains inside the backend.

---

## AI Workflow (Optional)

ZenML

ZenML will be used if workflow orchestration becomes necessary.

Possible future uses:

- Prompt versioning
- Evaluation pipelines
- Dataset versioning
- AI workflow tracking
- Experiment management

ZenML is **not required for the MVP** but the architecture should allow easy integration.

---

## Storage

Development

SQLite

Production

PostgreSQL

Uploaded Files

Local storage during development

Cloud object storage in production

---

## Deployment

Containerisation

Docker

Reverse Proxy (Future)

Nginx

Cloud Platform

Any Docker-compatible cloud provider

Examples:

- Railway
- Render
- Azure
- AWS
- Google Cloud

---

# 4. Development Environment

The entire backend must be developed inside a dedicated Python virtual environment.

Example

```
ClinicalAI/
    .venv/
```

Reasons

- Dependency isolation
- Reproducibility
- Easier deployment
- Cleaner development
- Avoid global package conflicts

No Python packages should be installed globally.

---

# 5. Backend Responsibilities

The backend is responsible for:

- Receiving requests
- Validating data
- Managing patient records
- Processing uploaded files
- Calling the OpenAI API
- Structuring AI responses
- Logging
- Error handling
- Authentication (future)
- Database operations

The backend must never expose API keys.

---

# 6. Frontend Responsibilities

The frontend is responsible for:

- Patient registration forms
- Medical history forms
- File uploads
- Viewing AI results
- Displaying warnings
- Showing confidence scores
- Showing reasoning
- Authentication screens (future)
- Dashboard

The frontend must never directly communicate with OpenAI.

All AI requests must go through the backend.

---

# 7. AI Responsibilities

The OpenAI model is responsible for:

- Analysing patient information
- Summarising reports
- Identifying medication warnings
- Suggesting possible diagnoses
- Identifying missing information
- Explaining reasoning

The AI must never:

- Prescribe medication
- Recommend medication dosage
- Guarantee diagnoses
- Replace healthcare professionals
- Fabricate medical facts

---

# 8. Communication Flow

1. User enters patient information.

↓

2. Frontend validates input.

↓

3. Frontend sends request to FastAPI.

↓

4. Backend validates request.

↓

5. Backend prepares AI prompt.

↓

6. Backend calls OpenAI.

↓

7. OpenAI returns structured JSON.

↓

8. Backend validates JSON.

↓

9. Backend stores analysis.

↓

10. Backend returns response.

↓

11. Frontend displays results.

---

# 9. Design Principles

The project follows the following architectural principles.

## Separation of Concerns

Each layer has a single responsibility.

Frontend

Presentation only.

Backend

Business logic.

AI

Reasoning only.

Database

Storage only.

---

## Modularity

Each module should be replaceable without affecting the rest of the system.

---

## Scalability

The architecture should allow:

- multiple AI providers
- PostgreSQL
- authentication
- cloud deployment
- multiple hospitals

without major refactoring.

---

## Security

- API keys stored in .env
- Backend-only AI communication
- Input validation
- Output validation
- Structured logging
- Secure file uploads

---

## Explainability

Every AI conclusion should include:

- evidence
- confidence
- reasoning
- missing information

---

## Maintainability

The project should follow:

- clean architecture
- reusable services
- dependency injection where appropriate
- consistent coding standards

---

# 10. Expected Folder Structure

```
ClinicalAI/

docs/

frontend/

backend/

tests/

docker/

scripts/

.env.example

.gitignore

docker-compose.yml

README.md
```

---

# 11. Future Expansion

The architecture should support future integration with:

- Electronic Health Records (EHR)
- FHIR APIs
- PACS imaging systems
- Drug interaction databases
- Laboratory Information Systems
- Authentication providers
- Multi-user hospitals
- Analytics dashboards

without significant redesign.