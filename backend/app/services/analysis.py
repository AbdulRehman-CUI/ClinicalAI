"""Orchestrate the complete AI analysis workflow for a patient."""

from __future__ import annotations

import logging
import json
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
    AIServiceUnavailableError,
    ResourceNotFoundError,
    ValidationError,
)

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
        self.engine = engine or AIEngine()
        self.context_builder = context_builder or PatientContextBuilder()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_parser = response_parser or ResponseParser()

    def analyze_patient(self, patient_id: int) -> dict[str, Any]:
        """Build context, call the AI engine, validate the response, and persist it."""
        logger.info("Analysis started for patient %s", patient_id)
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

        try:
            parsed_response = self.engine.analyze(context)
        except Exception as exc:  # pragma: no cover - exercised through dependency injection in tests
            # Attempt to surface original SDK/HTTP details for debugging (status, body, url, model, type)
            exc_type = type(exc).__name__

            model_name = None
            try:
                provider = getattr(self.engine, "provider", None)
                if provider is not None:
                    settings = getattr(provider, "settings", None)
                    if settings is not None:
                        model_name = getattr(settings, "gemini_model", None) or getattr(settings, "openai_model", None)
            except Exception:
                model_name = None

            # Try to find a response-like object on the exception by common attribute names
            response_obj = None
            for attr in ("response", "raw_response", "http_response", "resp", "response_body"):
                response_obj = getattr(exc, attr, None)
                if response_obj is not None:
                    break

            status_code = None
            request_url = None
            response_body = None

            if response_obj is not None:
                # Status code: requests.Response uses .status_code, others may use .status
                status_code = getattr(response_obj, "status_code", getattr(response_obj, "status", None))

                # Try to get JSON body exactly as returned by the SDK/HTTP layer
                try:
                    if hasattr(response_obj, "json") and callable(response_obj.json):
                        response_body = response_obj.json()
                    elif hasattr(response_obj, "text"):
                        response_body = response_obj.text
                    elif hasattr(response_obj, "content"):
                        response_body = response_obj.content
                    else:
                        response_body = repr(response_obj)
                except Exception:
                    # Fall back to string representation if .json() or reading fails
                    try:
                        response_body = response_obj.text
                    except Exception:
                        response_body = repr(response_obj)

                # Request URL: requests.Response.request.url or .url
                req = getattr(response_obj, "request", None)
                if req is not None:
                    request_url = getattr(req, "url", None)
                request_url = request_url or getattr(response_obj, "url", None)
            else:
                # No nested response object; inspect exception attributes directly
                status_code = getattr(exc, "status_code", getattr(exc, "status", None))
                request_url = getattr(exc, "url", None)
                response_body = getattr(exc, "body", getattr(exc, "details", None) or getattr(exc, "message", None))

            # Normalize bytes to string for logging
            if isinstance(response_body, (bytes, bytearray)):
                try:
                    response_body = response_body.decode("utf-8")
                except Exception:
                    response_body = repr(response_body)

            # If response_body is a dict/list (from .json()), pretty-print it to preserve exact JSON
            if isinstance(response_body, (dict, list)):
                try:
                    response_body_str = json.dumps(response_body, ensure_ascii=False)
                except Exception:
                    response_body_str = str(response_body)
            else:
                response_body_str = str(response_body)

            logger.error(
                "AI engine exception for patient %s: type=%s model=%s status=%s url=%s response=%s",
                patient_id,
                exc_type,
                model_name,
                status_code,
                request_url,
                response_body_str,
                exc_info=True,
            )

            # Preserve existing user-facing behavior (wrap original exception)
            raise AIServiceUnavailableError("AI service temporarily unavailable.") from exc

        try:
            validated_response = self.response_parser.parse(parsed_response)
        except Exception as exc:  # pragma: no cover - exercised through dependency injection in tests
            logger.warning("AI response validation failed for patient %s", patient_id)
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

        logger.info("Analysis completed for patient %s with analysis_id %s", patient_id, instance.id)
        return {
            "analysis_id": instance.id,
            "patient_id": patient_id,
            "report_id": report_id,
            **validated_response,
        }

    def _load_related_records(self, patient_id: int, repository: Any) -> list[Any]:
        items = repository.list(offset=0, limit=1000)
        return [item for item in items if getattr(item, "patient_id", None) == patient_id]

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
