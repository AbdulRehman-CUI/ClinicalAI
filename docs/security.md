# Phase 8 – Authentication & Security

## Objective

Introduce authentication and authorization without changing the existing application architecture.

The current architecture must remain:

React Frontend
        ↓
FastAPI Routers
        ↓
Services
        ↓
Repositories
        ↓
SQLAlchemy
        ↓
Database

Authentication should integrate into this architecture rather than replacing it.

---

# Goals

Implement production-style authentication and authorization using JWT while keeping the backend modular and configurable.

---

# Authentication

Implement:

- User Registration
- User Login
- JWT Access Tokens
- Refresh Tokens
- Logout
- Current Authenticated User dependency

Passwords must never be stored in plain text.

Use bcrypt hashing.

JWT secrets and expiry values must come from the Settings configuration.

No secrets may be hardcoded.

---

# User Model

Create a User entity.

Fields:

- id
- full_name
- email (unique)
- hashed_password
- role
- is_active
- created_at
- updated_at

---

# Roles

Implement Role-Based Access Control (RBAC).

Supported roles:

- Admin
- Doctor
- Staff

The architecture should make it easy to add more roles later.

---

# Permissions

Admin

- Full system access
- User management
- Patient CRUD
- Medical history
- Allergies
- Medications
- Symptoms
- Reports
- AI Analysis

Doctor

- Patient CRUD
- Medical history
- Allergies
- Medications
- Symptoms
- Reports
- AI Analysis

Staff

- Patient CRUD
- Medical history
- Allergies
- Medications
- Symptoms
- Report Upload

Staff should NOT be allowed to trigger AI analysis.

Return HTTP 403 when permissions are insufficient.

---

# API Endpoints

Create:

POST /auth/register

POST /auth/login

POST /auth/refresh

POST /auth/logout

GET /users/me

---

# Protect Existing Routes

Existing CRUD endpoints must require authentication.

Authorization should be implemented through reusable FastAPI dependencies.

Avoid duplicating permission checks inside routes.

---

# Security

Implement:

JWT Authentication

Password Hashing

Token Expiration

Refresh Tokens

Security Headers

CORS configuration via Settings

Maximum request size

Environment-based secrets

---

# Configuration

All authentication settings must come from config.py.

Examples:

JWT Secret

JWT Algorithm

Access Token Expiry

Refresh Token Expiry

Password Hashing Rounds

No hardcoded secrets.

---

# Database

Use Alembic migration.

Do NOT recreate the database.

Create a migration only for the User table.

---

# Frontend

Do not redesign the UI.

Add only what is required:

Login page

Registration page

Logout

Token storage

Automatic Authorization header

Automatic redirect to login when unauthenticated

---

# Error Handling

Maintain the existing API response envelope.

Unauthorized

401

Forbidden

403

Expired Token

401

Validation

422

Unexpected

500

---

# Tests

Add tests for:

Registration

Login

JWT validation

Protected routes

Role permissions

Password hashing

Refresh tokens

---

# Constraints

Do not modify existing CRUD logic.

Do not break existing APIs.

Keep Router → Service → Repository architecture.

Keep centralized configuration.

Keep dependency injection.

Keep logging.

Follow the project's existing coding style.

Update documentation where appropriate.
