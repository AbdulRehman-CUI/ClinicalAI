"""Orchestrate the complete AI analysis workflow for a patient."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai.context_builder import PatientContextBuilder
from app.ai.engine import AIEngine
from app.ai.prompt_builder import PromptBuilder
from app.ai.response_parser import ResponseParser
from app.db.session import get_db
from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.allergy import AllergyRepository
from app.repositories.medical_history import MedicalHistoryRepository
from app.repositories.medical_report import MedicalReportRepository
from app.repositories.medication import MedicationRepository
from app.repositories.patient import PatientRepository
from app.repositories.symptom import SymptomRepository
from app.services.exceptions import (
    AIResponseValidationError,
    ResourceNotFoundError,
    ValidationError,
)
from app.services.llm import configured_provider
from app.ai.providers import provider_error

logger = logging.getLogger(__name__)


class AnalysisService:
    """Coordinate patient context assembly, prompt generation, AI execution, and persistence."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        history_repository: MedicalHistoryRepository,
        allergy_repository: AllergyRepository,
        medication_repository: MedicationRepository,
        symptom_repository: SymptomRepository,
        report_repository: MedicalReportRepository,
        analysis_repository: AIAnalysisRepository,
        engine: AIEngine | None = None,
        context_builder: PatientContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        response_parser: ResponseParser | None = None,
    ) -> None:
        self.patient_repository = patient_repository
        self.history_repository = history_repository
        self.allergy_repository = allergy_repository
        self.medication_repository = medication_repository
        self.symptom_repository = symptom_repository
        self.report_repository = report_repository
        self.analysis_repository = analysis_repository
        self.engine = engine
        self.context_builder = context_builder or PatientContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_parser = response_parser or ResponseParser()

    def analyze_patient(self, patient_id: int) -> dict[str, Any]:
        """Build context, call the AI engine, validate the response, and persist it."""
        logger.info("Analysis started")
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")

        medical_history = self._load_related_records(patient_id, self.history_repository)
        allergies = self._load_related_records(patient_id, self.allergy_repository)
        medications = self._load_related_records(patient_id, self.medication_repository)
        symptoms = self._load_related_records(patient_id, self.symptom_repository)
        reports = self._load_related_records(patient_id, self.report_repository)

        if not any([medical_history, allergies, medications, symptoms, reports]):
            raise ValidationError("No patient information available for analysis.")
        if not symptoms and not reports:
            raise ValidationError("No symptoms or reports available for analysis.")

        report_text = self._collect_report_text(reports)
        context = self.context_builder.build(
            patient=self._serialize_patient(patient),
            medical_history=[self._serialize_history(item) for item in medical_history],
            allergies=[self._serialize_allergy(item) for item in allergies],
            medications=[self._serialize_medication(item) for item in medications],
            symptoms=[self._serialize_symptom(item) for item in symptoms],
            reports=report_text,
        )

        engine = self.engine or AIEngine(provider=configured_provider(self.analysis_repository.db))
        try:
            parsed_response = engine.analyze(context)
        except ValueError as exc:
            raise AIResponseValidationError("AI response was malformed or incomplete.") from exc
        except Exception as exc:
            logger.error("AI provider request failed (%s)", type(exc).__name__)
            raise provider_error(exc) from None

        try:
            validated_response = self.response_parser.parse(parsed_response)
        except Exception as exc:  # pragma: no cover - exercised through dependency injection in tests
            logger.warning("AI response validation failed")
            raise AIResponseValidationError("AI response was malformed or incomplete.") from exc

        report_id = reports[0].id if reports else None
        instance = self.analysis_repository.create(
            {
                "patient_id": patient_id,
                "report_id": report_id,
                "medication_warnings": validated_response.get("medication_warnings", []),
                "possible_diagnoses": validated_response.get("possible_diagnoses", []),
                "confidence": self._confidence_score(validated_response),
                "supporting_evidence": validated_response.get("medication_warnings", []),
                "missing_information": ["Review the AI output with a clinician for final interpretation."],
                "suggested_next_steps": [validated_response.get("recommended_specialist", "") or "Schedule clinician review"],
            }
        )

        logger.info("Analysis completed")
        return {
            "analysis_id": instance.id,
            "patient_id": patient_id,
            "report_id": report_id,
            **validated_response,
        }

    def _load_related_records(self, patient_id: int, repository: Any) -> list[Any]:
        return repository.list(offset=0, limit=1000, patient_id=patient_id)

    def _collect_report_text(self, reports: list[Any]) -> str:
        parts: list[str] = []
        for report in reports:
            text = getattr(report, "extracted_text", None)
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    def _serialize_patient(self, patient: Any) -> dict[str, Any]:
        return {
            "first_name": patient.first_name,
            "last_name": patient.last_name,
            "age": patient.age,
            "biological_sex": patient.biological_sex,
            "blood_group": patient.blood_group,
            "height_cm": patient.height_cm,
            "weight_kg": patient.weight_kg,
            "pregnancy_status": patient.pregnancy_status,
        }

    def _serialize_history(self, history: Any) -> dict[str, Any]:
        return {
            "condition_name": history.condition_name,
            "diagnosis_date": history.diagnosis_date,
            "notes": history.notes,
        }

    def _serialize_allergy(self, allergy: Any) -> dict[str, Any]:
        return {
            "allergen": allergy.allergen,
            "reaction": allergy.reaction,
            "severity": allergy.severity,
        }

    def _serialize_medication(self, medication: Any) -> dict[str, Any]:
        return {
            "medication_name": medication.medication_name,
            "dosage": medication.dosage,
            "frequency": medication.frequency,
            "start_date": medication.start_date,
            "notes": medication.notes,
        }

    def _serialize_symptom(self, symptom: Any) -> dict[str, Any]:
        return {
            "symptom_name": symptom.symptom_name,
            "duration": symptom.duration,
            "severity": symptom.severity,
            "notes": symptom.notes,
        }

    def _confidence_score(self, validated_response: dict[str, Any]) -> float:
        diagnoses = validated_response.get("possible_diagnoses", [])
        if not diagnoses:
            return 0.0
        score = 0.0
        for item in diagnoses:
            if isinstance(item, dict):
                confidence = item.get("confidence", "")
                if isinstance(confidence, str):
                    normalized = confidence.lower()
                    if normalized in {"high"}:
                        score += 0.8
                    elif normalized in {"medium"}:
                        score += 0.6
                    elif normalized in {"low"}:
                        score += 0.3
                elif isinstance(confidence, (int, float)):
                    score += float(confidence)
        if not diagnoses:
            return 0.0
        return round(score / len(diagnoses), 2)


def get_analysis_service(db: Session = Depends(get_db)) -> AnalysisService:
    """Create an analysis service bound to the current database session."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("Creating AnalysisService dependency")

    return AnalysisService(
        PatientRepository(db),
        MedicalHistoryRepository(db),
        AllergyRepository(db),
        MedicationRepository(db),
        SymptomRepository(db),
        MedicalReportRepository(db),
        AIAnalysisRepository(db),
    )
