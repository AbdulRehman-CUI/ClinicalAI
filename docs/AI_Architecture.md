# ClinicalAI
## Phase 4 – AI Architecture

---

# Objective

Transform ClinicalAI from a CRUD-based medical records application into an AI-powered Clinical Decision Support System (CDSS).

The AI layer must remain completely isolated from the REST API and database implementation.

The AI should NEVER make clinical decisions.

The implementation now uses a provider abstraction so the same service layer can call either OpenAI or Gemini based on configuration. The public API, response schema, and business workflow remain unchanged.

Instead it should:

- identify possible risks
- identify medication contraindications
- identify possible diagnoses
- summarize uploaded reports
- explain its reasoning
- state uncertainty when insufficient information exists

The software must always assist clinicians rather than replace them.

---

# Overall Architecture

Client

↓

FastAPI Router

↓

Service Layer

↓

Patient Context Builder

↓

AI Engine

↓

OpenAI API

↓

Structured JSON

↓

AIAnalysis Table

↓

API Response

The Router must never communicate with OpenAI directly.

The Repository must never communicate with OpenAI.

Only the AI Engine communicates with OpenAI.

---

# New Components

backend/app/ai/

    __init__.py

    engine.py

    prompt_builder.py

    response_parser.py

    report_processor.py

    context_builder.py

---

# Responsibilities

## Report Processor

Responsible for reading uploaded files.

Supported formats

- PDF
- DOCX
- TXT

Future support

- PNG
- JPG
- JPEG
- OCR

Responsibilities

- detect format
- extract text
- normalize whitespace
- remove empty pages
- return plain text

No AI logic belongs here.

---

## Patient Context Builder

Responsible for collecting

Patient

Medical History

Symptoms

Allergies

Current Medications

Medical Reports

AI never queries the database.

Instead the Context Builder constructs a single Python object.

Example

{
    patient: {...},
    medical_history:[...],
    allergies:[...],
    medications:[...],
    symptoms:[...],
    reports:"..."
}

---

## Prompt Builder

Responsible only for creating prompts.

No database access.

No HTTP requests.

No OpenAI calls.

Input

Patient Context

Output

System Prompt

User Prompt

---

## AI Engine

Responsible for

calling OpenAI

receiving response

validating JSON

handling API failures

returning structured Python objects

The AI Engine never accesses SQLAlchemy.

---

## Response Parser

Responsible for validating AI responses.

If the model returns malformed JSON

attempt repair

otherwise raise a recoverable exception.

---

# Design Principles

Single Responsibility Principle

Every class should have one purpose.

No duplicated prompt generation.

No duplicated report extraction.

No duplicated parsing logic.

---

# Configuration

Everything AI related must come from config.py

OPENAI_API_KEY

OPENAI_MODEL

OPENAI_TIMEOUT

MAX_REPORT_SIZE

MAX_CONTEXT_LENGTH

No hardcoded values.

---

# Error Handling

OpenAI unavailable

↓

Return

AI service temporarily unavailable.

Do not crash the application.

Do not return raw exceptions.

---

# Future Compatibility

The AI Engine must be easily replaceable.

Today

OpenAI

Tomorrow

Azure OpenAI

Local Llama

Anthropic

Gemini

Changing providers should require changing only engine.py.