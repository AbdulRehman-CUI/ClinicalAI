# ClinicalAI
## API Specification

Version: 1.0

---

# 1. Purpose

This document defines every REST API endpoint exposed by the ClinicalAI backend.

The API is responsible for communication between the frontend and backend.

The frontend must never communicate directly with the database or OpenAI.

---

# 2. API Principles

The API shall:

- Follow REST principles.
- Use JSON for all request and response bodies.
- Validate every request.
- Return consistent responses.
- Never expose database models directly.
- Never expose internal errors.

---

# 3. Base URL

Development

```
http://localhost:8000/api/v1
```

---

# 4. Patient Endpoints

## Create Patient

POST

```
/patients
```

Creates a new patient.

---

## Get Patient

GET

```
/patients/{patient_id}
```

Returns one patient.

---

## List Patients

GET

```
/patients
```

Supports pagination.

---

## Update Patient

PUT

```
/patients/{patient_id}
```

Updates patient information.

---

## Delete Patient

DELETE

```
/patients/{patient_id}
```

Deletes a patient.

---

# 5. Medical History

POST

```
/patients/{patient_id}/medical-history
```

GET

```
/patients/{patient_id}/medical-history
```

PUT

```
/medical-history/{history_id}
```

DELETE

```
/medical-history/{history_id}
```

---

# 6. Medication

POST

```
/patients/{patient_id}/medications
```

GET

```
/patients/{patient_id}/medications
```

PUT

```
/medications/{medication_id}
```

DELETE

```
/medications/{medication_id}
```

---

# 7. Allergy

POST

```
/patients/{patient_id}/allergies
```

GET

```
/patients/{patient_id}/allergies
```

PUT

```
/allergies/{allergy_id}
```

DELETE

```
/allergies/{allergy_id}
```

---

# 8. Symptoms

POST

```
/patients/{patient_id}/symptoms
```

GET

```
/patients/{patient_id}/symptoms
```

PUT

```
/symptoms/{symptom_id}
```

DELETE

```
/symptoms/{symptom_id}
```

---

# 9. Medical Reports

Upload Report

POST

```
/patients/{patient_id}/reports
```

Multipart form upload.

---

Get Reports

GET

```
/patients/{patient_id}/reports
```

---

Get One Report

GET

```
/reports/{report_id}
```

---

Delete Report

DELETE

```
/reports/{report_id}
```

---

# 10. AI Analysis

Analyse Patient

POST

```
/patients/{patient_id}/analysis
```

Triggers AI analysis.

The backend gathers:

- Patient
- History
- Medications
- Allergies
- Symptoms
- Uploaded reports

before calling the AI.

---

Get Analysis

GET

```
/analysis/{analysis_id}
```

---

List Analyses

GET

```
/patients/{patient_id}/analysis
```

---

# 11. Health

GET

```
/health
```

---

# 12. Future APIs

Authentication

Appointments

Doctors

Hospitals

FHIR Integration

Drug Databases

These are intentionally excluded from the MVP.