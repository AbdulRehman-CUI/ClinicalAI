# ClinicalAI
## AI Workflow

---

# Workflow

Patient submits

↓

Patient Data

↓

Medical History

↓

Symptoms

↓

Allergies

↓

Current Medications

↓

Medical Reports

↓

Report Processor

↓

Extract Text

↓

Patient Context Builder

↓

Prompt Builder

↓

OpenAI

↓

JSON Response

↓

Response Parser

↓

AIAnalysis Repository

↓

Save Result

↓

Return Response

---

# AI Responsibilities

The AI should perform the following tasks.

---

## Medication Warnings

Examples

Patient allergic to Penicillin

↓

Warn against Penicillin.

Patient has Kidney Disease

↓

Warn against NSAIDs.

Only produce warnings when evidence exists.

---

## Possible Diagnoses

Generate

possible diagnosis

confidence

reasoning

Never claim certainty.

Confidence values

Low

Medium

High

---

## Critical Alerts

Identify

life threatening situations

dangerous combinations

contraindications

high-risk findings

---

## Recommended Tests

Examples

CBC

MRI

ECG

Blood Culture

Only when justified.

---

## Specialist Recommendation

Recommend specialist if appropriate.

Examples

Cardiologist

Neurologist

Endocrinologist

---

## Report Summary

Summarize uploaded reports in plain language.

---

# AI Output Format

The AI MUST return JSON.

Never paragraphs.

Example

{
    "possible_diagnoses":[...],
    "medication_warnings":[...],
    "critical_alerts":[...],
    "recommended_tests":[...],
    "recommended_specialist":"...",
    "summary":"..."
}

---

# Safety Rules

Never fabricate information.

Never diagnose if evidence is insufficient.

Always explain uncertainty.

Always recommend clinician review.

Always state that this is a decision-support tool.