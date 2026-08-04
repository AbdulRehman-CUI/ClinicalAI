# ClinicalAI
## Phase 5 – AI Analysis Workflow

---

# Objective

Integrate the previously implemented AI foundation into the backend workflow.

This phase should connect the existing components without redesigning the application architecture.

The existing Router → Service → Repository → Database architecture must remain unchanged.

---

# Existing Components

The following components already exist and must be reused.

- Report Processor
- Patient Context Builder
- Prompt Builder
- AI Engine
- Response Parser
- AIAnalysis Repository

No duplicate implementations should be created.

---

# Workflow

The complete workflow must follow the sequence below.

Client

↓

POST /patients/{patient_id}/analyze

↓

Analysis Service

↓

Load Patient

↓

Load Medical History

↓

Load Symptoms

↓

Load Allergies

↓

Load Current Medications

↓

Load Medical Reports

↓

Patient Context Builder

↓

Prompt Builder

↓

OpenAI Engine

↓

Response Parser

↓

Persist AIAnalysis

↓

Return Structured Response

---

# Analysis Service

Create a dedicated service responsible for orchestration.

Responsibilities

- load patient data
- build patient context
- build prompts
- call AI Engine
- parse AI response
- save AIAnalysis
- return response

The service must NOT contain SQLAlchemy queries.

The service must reuse repositories.

---

# API Endpoint

Create a dedicated endpoint.

POST

/api/v1/patients/{patient_id}/analyze

Input

patient_id

No request body is required because all information already exists in the database.

---

# AI Output Format

The AI must always return structured JSON.

Expected structure

{
    "possible_diagnoses":[
        {
            "name":"",
            "confidence":"",
            "reason":""
        }
    ],

    "medication_warnings":[
        {
            "drug":"",
            "reason":""
        }
    ],

    "critical_alerts":[
        {
            "title":"",
            "reason":""
        }
    ],

    "recommended_tests":[
        "...",
        "..."
    ],

    "recommended_specialist":"",

    "summary":""
}

No free-form responses.

---

# Persistence

Every successful AI execution must be saved.

Store

patient_id

report_id (if applicable)

raw_response

parsed_response

model_name

execution_timestamp

status

Any existing AIAnalysis schema should be reused.

---

# Error Handling

Possible failures

Patient not found

↓

404

No patient information available

↓

422

No symptoms or reports available

↓

422

OpenAI unavailable

↓

503

Malformed AI response

↓

502

Unexpected exception

↓

500

Errors must use the project's existing response envelope.

---

# Safety

The AI must never claim certainty.

The prompt must explicitly instruct the model to:

- avoid definitive diagnosis
- explain uncertainty
- recommend clinician review
- avoid fabricating information
- refuse unsupported conclusions

---

# Logging

Log

Analysis Started

Patient ID

Model Name

Execution Time

Success / Failure

Never log

Patient medical details

API keys

Prompt contents

---

# Performance

Patient context should be constructed only once.

Prompt generation should occur once.

OpenAI should be called once.

Database writes should occur only after successful response validation.

---

# Verification

The following should be verified.

✓ Analysis endpoint returns 200.

✓ AI response follows documented schema.

✓ AIAnalysis row is stored.

✓ Existing CRUD endpoints continue working.

✓ Existing upload functionality remains unchanged.

✓ Existing tests continue passing.