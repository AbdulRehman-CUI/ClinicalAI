# Authentication Design

## Objective

Secure ClinicalAI using JWT authentication and role-based authorization while keeping the architecture modular and configuration-driven.

---

## Architecture

React Frontend
        │
        ▼
Login / Register
        │
        ▼
JWT Token
        │
        ▼
Auth Context
        │
        ▼
Axios Interceptor
        │
        ▼
FastAPI Backend
        │
        ▼
Authentication Dependency
        │
        ▼
Authorization (Roles)
        │
        ▼
Service Layer
        │
        ▼
Repository Layer
        │
        ▼
Database

---

## Roles

Doctor
- Full patient management
- Upload reports
- Run AI analysis

Admin
- Full system access
- User management
- AI analysis

Staff
- Patient CRUD
- Medical history
- Allergies
- Medications
- Symptoms
- No AI analysis

---

## Frontend Requirements

- Login page
- Register page
- Logout
- Auth Context
- Protected Routes
- Axios Interceptor
- Persistent login
- Automatic redirect after login
- Automatic redirect to login when unauthorized
- Friendly authentication errors

---

## Backend Requirements

- JWT validation
- Password hashing (bcrypt)
- Role-based authorization
- Configuration-driven secrets
- Alembic migration for users
- No hardcoded credentials

---

## Non-Goals

Do not modify:
- AI workflow
- CRUD logic
- Repository-Service architecture
- API response format

---

## Verification Checklist

- User registration
- User login
- JWT generation
- JWT validation
- Protected endpoints
- Role authorization
- Logout
- Fresh database migration
- Frontend build succeeds
- Backend tests pass