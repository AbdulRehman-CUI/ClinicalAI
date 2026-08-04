# 13. Configuration Guide

## ClinicalAI Configuration Standard

Version: 1.0

---

# Purpose

ClinicalAI is designed to run in multiple environments without requiring code changes.

The application must never rely on hardcoded environment-specific values.

Instead, all configurable behaviour must be controlled through a centralized configuration system.

The configuration layer is considered part of the architecture and must be respected throughout the project.

---

# Configuration Philosophy

The project follows the following hierarchy.

```
Environment Variables
        │
        ▼
Pydantic Settings
        │
        ▼
Application Components
        │
        ▼
Business Logic
```

Business logic must never read environment variables directly.

Only the configuration module may communicate with the operating system.

---

# Configuration Principles

The following rules apply throughout the project.

## Rule 1

Never hardcode values that may change between environments.

Bad

```python
DATABASE_URL = "sqlite:///clinicalai.db"
```

Good

```python
DATABASE_URL = settings.database_url
```

---

## Rule 2

All configuration must originate from the central configuration module.

No other module should call:

```python
os.getenv(...)
```

or

```python
dotenv.load_dotenv(...)
```

outside the configuration layer.

---

## Rule 3

Every configurable value must have

- a documented purpose
- a sensible default
- type validation
- optional environment override

---

## Rule 4

Changing environments must never require changing application code.

The application should work unchanged in:

- Local Development
- Docker
- PostgreSQL
- SQLite
- Testing
- Production
- Cloud Deployments

---

# Configuration Categories

## Database

Examples

DATABASE_URL

Future

POOL_SIZE

MAX_OVERFLOW

POOL_TIMEOUT

---

## Server

HOST

PORT

DEBUG

API_PREFIX

---

## Logging

LOG_LEVEL

LOG_FORMAT

---

## Security

SECRET_KEY

TOKEN_EXPIRATION

ALGORITHM

---

## AI

AI_PROVIDER

OPENAI_API_KEY

OPENAI_MODEL

GEMINI_API_KEY

GEMINI_MODEL

OPENAI_TEMPERATURE

OPENAI_TIMEOUT

MAX_AI_TOKENS

---

## OCR

OCR_PROVIDER

OCR_LANGUAGE

OCR_TIMEOUT

---

## File Upload

UPLOAD_DIRECTORY

MAX_UPLOAD_SIZE_MB

ALLOWED_FILE_EXTENSIONS

---

## Storage

STORAGE_PROVIDER

LOCAL_STORAGE_PATH

Future:

AWS S3

Azure Blob Storage

Google Cloud Storage

---

## Pagination

DEFAULT_PAGE_SIZE

MAX_PAGE_SIZE

---

## CORS

ALLOWED_ORIGINS

---

## Time

TIMEZONE

DATE_FORMAT

---

# Database Configuration

The project must never assume a specific database.

Changing from SQLite to PostgreSQL must require only changing the configuration.

The default local database should be

backend/data/clinicalai.db

The database location must never depend on the terminal's current working directory.

The configuration layer must resolve the correct path automatically.

---

# AI Configuration

The AI provider must never be hardcoded.

Business logic should communicate with an AI abstraction rather than directly with OpenAI.

Future providers may include

- OpenAI
- Azure OpenAI
- Anthropic
- Local LLMs

Changing provider should only require changing configuration.

---

# Storage Configuration

Business logic must never know where files are stored.

Storage should be abstracted behind a Storage Provider.

Possible implementations

- Local Storage

- Amazon S3

- Azure Blob

- Google Cloud Storage

The active provider is selected via configuration.

---

# OCR Configuration

OCR should be provider-based.

Possible providers

- Tesseract

- Azure OCR

- Google Vision

- AWS Textract

No OCR implementation should be hardcoded.

---

# Future Expandability

The configuration system should support future additions without architectural changes.

Examples

Redis

RabbitMQ

Celery

Background workers

Email services

SMS services

Authentication providers

Observability

Monitoring

Caching

---

# Validation

Configuration values should be validated whenever possible.

Examples

Port > 0

Upload Size > 0

Temperature between 0 and 2

Page Size > 0

Timeout > 0

---

# Documentation

Every configuration option should appear in

.env.example

with

- description
- default value
- expected type

---

# Developer Guidelines

Developers must never hardcode

- URLs

- API Keys

- Ports

- Database Paths

- Upload Directories

- AI Models

- Providers

- Secrets

- Storage Locations

- CORS Origins

- Time Zones

- Page Sizes

- Limits

Instead, use

settings.<property>

throughout the application.

---

# Architectural Goal

The same source code should run without modification in

Developer Machine

Docker

CI/CD

Cloud

Production

Only configuration should change.

This principle applies to all future project phases.