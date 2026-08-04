# ClinicalAI
## Database Design

Version: 1.0

---

# 1. Purpose

This document defines the database architecture for ClinicalAI.

The database stores structured patient information, uploaded report metadata, and AI analysis results.

The database is **not** responsible for AI reasoning or prompt management.

Development database:
- SQLite

Production database:
- PostgreSQL

The schema must be compatible with both.

---

# 2. Design Principles

The database shall:

- Store only structured application data.
- Avoid duplicated information.
- Use foreign keys to maintain relationships.
- Keep AI reasoning separate from persistent storage.
- Support future expansion without major schema changes.

---

# 3. Main Entities

The system contains the following entities:

1. Patient
2. Medical History
3. Medication
4. Allergy
5. Symptom
6. Medical Report
7. AI Analysis

---

# 4. Entity Descriptions

## Patient

Represents one patient.

Fields

- id
- first_name
- last_name
- age
- biological_sex
- blood_group
- height_cm
- weight_kg
- pregnancy_status
- created_at
- updated_at

---

## Medical History

Stores previous medical conditions.

Fields

- id
- patient_id
- condition_name
- diagnosis_date (optional)
- notes

Examples

- Diabetes
- Hypertension
- Asthma
- Kidney Disease

Relationship

Many history records belong to one patient.

---

## Medication

Stores current medications.

Fields

- id
- patient_id
- medication_name
- dosage
- frequency
- start_date
- notes

Relationship

Many medications belong to one patient.

---

## Allergy

Stores allergies.

Fields

- id
- patient_id
- allergen
- reaction
- severity

Examples

- Penicillin
- Peanuts
- Latex

Relationship

Many allergies belong to one patient.

---

## Symptom

Stores symptoms entered for one consultation.

Fields

- id
- patient_id
- symptom_name
- duration
- severity
- notes

Relationship

Many symptoms belong to one patient.

---

## Medical Report

Represents uploaded reports.

Fields

- id
- patient_id
- original_filename
- stored_filename
- file_type
- upload_timestamp
- extracted_text
- summary

Supported files

- PDF
- PNG
- JPG
- JPEG

The AI-generated summary should be stored after successful analysis.

---

## AI Analysis

Stores the final structured analysis returned by the AI.

Fields

- id
- patient_id
- report_id (nullable)
- created_at

Analysis Results

- medication_warnings
- possible_diagnoses
- confidence
- supporting_evidence
- missing_information
- suggested_next_steps

Only the validated final response should be stored.

Do NOT store:

- raw prompts
- chain of thought
- internal reasoning

---

# 5. Relationships

Patient

↓

Medical History

Patient

↓

Medication

Patient

↓

Allergy

Patient

↓

Symptom

Patient

↓

Medical Report

Patient

↓

AI Analysis

One patient may have many analyses.

Each analysis belongs to exactly one patient.

A report may optionally be associated with one analysis.

---

# 6. Constraints

Patient

Age must be positive.

Height must be positive.

Weight must be positive.

Medication

Medication name is required.

Allergy

Allergen is required.

Medical Report

File type must be validated before storage.

AI Analysis

Cannot be saved until the AI response has been validated.

---

# 7. Indexing

Create indexes for:

- patient_id
- created_at
- upload_timestamp

Future optimisation may add additional indexes.

---

# 8. Repository Layer

Each entity should have its own repository.

PatientRepository

MedicalHistoryRepository

MedicationRepository

AllergyRepository

SymptomRepository

MedicalReportRepository

AIAnalysisRepository

Repositories must not contain business logic.

Repositories are responsible only for CRUD operations.

---

# 9. Migration

Use Alembic.

Every schema modification must be performed through migrations.

Do not modify SQLite directly.

---

# 10. Validation

Use Pydantic schemas.

Database models and API schemas must remain separate.

Never expose SQLAlchemy models directly through the API.

---

# 11. Future Expansion

The schema should support future additions without redesign.

Possible future entities:

- Hospital
- Doctor
- Appointment
- Laboratory Test
- Vital Signs
- Audit Log
- User Account

The current implementation should not create these tables.

---

# 12. Out of Scope

The database must not store:

- OpenAI prompts
- API keys
- Session tokens
- AI internal reasoning
- Temporary uploads
- Frontend state

---

# 13. Acceptance Criteria

The database implementation is considered complete when:

- All entities exist.
- Foreign keys are correctly configured.
- Alembic migrations run successfully.
- CRUD repositories exist.
- Validation schemas are separate from ORM models.
- SQLite works without modification.