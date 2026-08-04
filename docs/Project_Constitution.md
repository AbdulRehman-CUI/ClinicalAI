# ClinicalAI
## Project Constitution

Version: 1.0

---

# Purpose

This document defines the engineering principles, coding standards, architectural rules, and AI development guidelines for ClinicalAI.

Every developer, AI coding assistant, and contributor must follow these rules.

If any future prompt or implementation conflicts with this document, this document takes precedence.

---

# Core Philosophy

ClinicalAI follows one fundamental principle:

> Never hallucinate.
> Never hide uncertainty.
> Always explain reasoning.

Patient safety is always more important than producing a complete answer.

---

# Engineering Principles

The project must always prioritise:

- Readability
- Maintainability
- Scalability
- Security
- Modularity
- Testability
- Explainability

Shortcuts that compromise long-term quality are not acceptable.

---

# Architecture Rules

ClinicalAI follows a layered architecture.

```
Frontend
    ↓
REST API
    ↓
Backend Services
    ↓
AI Layer
    ↓
Database
```

Each layer has exactly one responsibility.

No layer may bypass another layer.

Examples:

❌ Frontend → OpenAI

❌ AI → Database

❌ React → SQLite

✔ Frontend → FastAPI

✔ FastAPI → AI

✔ FastAPI → Database

---

# Separation of Concerns

Frontend

Responsible only for:

- UI
- User interaction
- Form validation
- Visualisation

Backend

Responsible only for:

- Business logic
- Validation
- Authentication
- AI communication
- Database

AI

Responsible only for:

- Clinical reasoning
- Report summarisation
- Structured analysis

Database

Responsible only for persistent storage.

---

# AI Rules

The AI must never:

- invent diagnoses
- invent allergies
- invent laboratory findings
- invent medications
- prescribe treatment
- prescribe dosage
- claim certainty without evidence

Every AI response must include:

- Findings
- Confidence
- Supporting Evidence
- Clinical Reasoning
- Missing Information
- Suggested Next Steps

---

# OpenAI Usage

OpenAI must only be accessed through the backend AI service.

No frontend component may contain:

- API Keys
- AI prompts
- OpenAI requests

The AI provider must be abstracted so another provider can replace OpenAI in the future.

---

# Coding Standards

Python

- Python 3.12+
- PEP 8
- Type hints everywhere
- Docstrings for public classes/functions
- Small, reusable functions
- No duplicated business logic

TypeScript

- Strict mode
- Strong typing
- Functional components
- No any unless unavoidable

React

- Reusable components
- Feature-based organisation
- Hooks instead of class components

---

# Environment Rules

Development must occur inside:

```
.venv
```

Secrets

Never hardcode:

- API keys
- passwords
- tokens

Use:

```
.env
```

---

# Docker Rules

The project must always remain Docker compatible.

Every service should build independently.

The repository must contain:

- Dockerfile (backend)
- Dockerfile (frontend)
- docker-compose.yml

---

# Database Rules

Development

SQLite

Production

PostgreSQL

The data access layer should be designed so PostgreSQL replaces SQLite with minimal code changes.

---

# API Rules

REST architecture

Consistent endpoints

Consistent HTTP status codes

Consistent JSON responses

Example

```
{
    "success": true,
    "message": "...",
    "data": { }
}
```

Errors

```
{
    "success": false,
    "error": "...",
    "details": { }
}
```

---

# Error Handling

Never expose:

- stack traces
- secrets
- API keys

Errors should be logged internally while returning safe responses to users.

---

# Validation Rules

Validate:

- User input
- Uploaded files
- AI output
- Database operations

Never trust external input.

---

# Logging

The backend should log:

- API requests
- AI requests
- AI failures
- Validation failures
- Database errors

Sensitive information must never appear in logs.

---

# Documentation Rules

Every new feature must include:

- Code comments where appropriate
- Updated documentation if behaviour changes
- Meaningful commit messages

---

# Testing

Business logic should be independently testable.

AI prompts should be isolated from business logic.

Database operations should be mockable.

---

# AI Development Rules

When generating code:

- Never contradict existing documentation.
- Prefer modular solutions.
- Prefer reusable code.
- Avoid unnecessary dependencies.
- Avoid large monolithic files.
- Explain non-obvious implementation decisions with comments.

---

# Project Expansion

Future features should be added by extending modules, not rewriting them.

The architecture should support:

- Authentication
- Multiple hospitals
- Additional AI providers
- Medical databases
- Cloud deployment
- Mobile applications

without major refactoring.

---

# Final Rule

If uncertainty exists during development:

Do not invent requirements.

Instead, follow the existing documentation or request clarification.