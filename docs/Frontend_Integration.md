# Phase 6 – Frontend Integration

## Objective

Integrate the existing React frontend with the FastAPI backend.

The frontend must consume the existing REST API.

Do not change backend endpoints.

Do not modify database models.

Do not modify repositories.

Do not modify services.

The backend is considered the source of truth.

---

## Architecture

Frontend

Pages

Components

API Layer

Types

Backend REST API

Database

---

## API Layer

Every backend endpoint must have a corresponding API function.

Example:

patients.ts

createPatient()

updatePatient()

deletePatient()

getPatient()

listPatients()

Same applies for:

medical history

medications

allergies

symptoms

medical reports

AI analysis

---

## HTTP

Use Axios.

Do not perform fetch requests directly inside components.

---

## State

React state only.

No Redux.

No Zustand.

No MobX.

---

## Components

Components should never contain API logic.

Components only call API functions.

---

## Error Handling

Display backend validation errors.

Display loading indicators.

Display success notifications.

---

## Uploads

Medical report upload must support:

PDF

TXT

DOCX

Progress indication should be supported.

---

## AI

Frontend must support:

Run Analysis button

Loading indicator

Display returned analysis

Medication warnings

Diagnoses

Recommended tests

Recommended specialist

Summary

---

## Do Not

Do not change backend routes.

Do not duplicate validation.

Do not hardcode URLs.

Use configuration.

Do not introduce authentication.

Do not add WebSockets.

Do not add caching.

---

## Deliverables

Working frontend connected to backend.

No mock data.

No placeholder API calls.

Clean separation between UI and API layer.
