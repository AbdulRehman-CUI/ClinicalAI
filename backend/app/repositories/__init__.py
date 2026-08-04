"""Repository package for database CRUD access."""

from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.allergy import AllergyRepository
from app.repositories.medical_history import MedicalHistoryRepository
from app.repositories.medical_report import MedicalReportRepository
from app.repositories.medication import MedicationRepository
from app.repositories.patient import PatientRepository
from app.repositories.symptom import SymptomRepository

__all__ = [
    "AIAnalysisRepository",
    "AllergyRepository",
    "MedicalHistoryRepository",
    "MedicalReportRepository",
    "MedicationRepository",
    "PatientRepository",
    "SymptomRepository",
]

