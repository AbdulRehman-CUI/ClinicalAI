"""Pydantic schemas for API request and response contracts."""

from app.schemas.ai_analysis import AIAnalysisCreate, AIAnalysisRead, AIAnalysisUpdate
from app.schemas.allergy import AllergyCreate, AllergyRead, AllergyUpdate
from app.schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryRead,
    MedicalHistoryUpdate,
)
from app.schemas.medical_report import (
    MedicalReportCreate,
    MedicalReportRead,
    MedicalReportUpdate,
)
from app.schemas.medication import MedicationCreate, MedicationRead, MedicationUpdate
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.schemas.symptom import SymptomCreate, SymptomRead, SymptomUpdate

__all__ = [
    "AIAnalysisCreate",
    "AIAnalysisRead",
    "AIAnalysisUpdate",
    "AllergyCreate",
    "AllergyRead",
    "AllergyUpdate",
    "MedicalHistoryCreate",
    "MedicalHistoryRead",
    "MedicalHistoryUpdate",
    "MedicalReportCreate",
    "MedicalReportRead",
    "MedicalReportUpdate",
    "MedicationCreate",
    "MedicationRead",
    "MedicationUpdate",
    "PatientCreate",
    "PatientRead",
    "PatientUpdate",
    "SymptomCreate",
    "SymptomRead",
    "SymptomUpdate",
]
