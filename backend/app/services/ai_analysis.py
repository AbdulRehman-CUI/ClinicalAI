"""Service layer for AI analysis placeholder operations."""

from __future__ import annotations

from collections.abc import Sequence
import math

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.ai_analysis import AIAnalysisRepository
from app.repositories.patient import PatientRepository
from app.repositories.medical_report import MedicalReportRepository
from app.schemas.ai_analysis import AIAnalysisCreate, AIAnalysisRead
from app.schemas.common import PaginationMeta
from app.services.exceptions import ResourceNotFoundError, ValidationError


class AIAnalysisService:
    """Provide placeholder AI analysis persistence for the REST API layer."""

    def __init__(
        self,
        analysis_repository: AIAnalysisRepository,
        patient_repository: PatientRepository,
        report_repository: MedicalReportRepository,
    ) -> None:
        self.analysis_repository = analysis_repository
        self.patient_repository = patient_repository
        self.report_repository = report_repository

    def create(self, patient_id: int, report_id: int | None = None) -> AIAnalysisRead:
        """Create a placeholder analysis record for a patient or report."""
        self._ensure_patient_exists(patient_id)
        if report_id is not None:
            self._ensure_report_exists(report_id)
            if self._report_belongs_to_patient(report_id, patient_id) is False:
                raise ValidationError("The provided report does not belong to the patient.")

        data = {
            "patient_id": patient_id,
            "report_id": report_id,
            "medication_warnings": ["Placeholder analysis pending AI engine integration."],
            "possible_diagnoses": ["Placeholder diagnosis pending AI engine integration."],
            "confidence": 0.0,
            "supporting_evidence": ["Patient data collected; AI reasoning not yet enabled."],
            "missing_information": ["OpenAI integration is not implemented in this MVP."],
            "suggested_next_steps": ["Integrate the AI engine in a future phase."],
        }
        instance = self.analysis_repository.create(data)
        return AIAnalysisRead.model_validate(instance)

    def get(self, analysis_id: int) -> AIAnalysisRead:
        """Return one stored analysis record."""
        instance = self.analysis_repository.get(analysis_id)
        if instance is None:
            raise ResourceNotFoundError("Analysis not found.")
        return AIAnalysisRead.model_validate(instance)

    def list_for_patient(self, patient_id: int, page: int, page_size: int) -> tuple[list[AIAnalysisRead], PaginationMeta]:
        """Return paginated analysis records for one patient."""
        self._ensure_patient_exists(patient_id)
        offset = (page - 1) * page_size
        total_items = self.analysis_repository.count()
        instances: Sequence = self.analysis_repository.list(offset=offset, limit=page_size)
        items = [AIAnalysisRead.model_validate(instance) for instance in instances if instance.patient_id == patient_id]
        total_items = len(items)
        total_pages = math.ceil(total_items / page_size) if total_items else 1
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return items, pagination

    def _ensure_patient_exists(self, patient_id: int) -> None:
        """Validate that the patient exists."""
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")

    def _ensure_report_exists(self, report_id: int) -> None:
        """Validate that the referenced report exists."""
        report = self.report_repository.get(report_id)
        if report is None:
            raise ResourceNotFoundError("Medical report not found.")

    def _report_belongs_to_patient(self, report_id: int, patient_id: int) -> bool:
        """Return whether a report is owned by the given patient."""
        report = self.report_repository.get(report_id)
        return report is not None and report.patient_id == patient_id


def get_ai_analysis_service(db: Session = Depends(get_db)) -> AIAnalysisService:
    """Create an AI analysis service bound to the current database session."""
    return AIAnalysisService(AIAnalysisRepository(db), PatientRepository(db), MedicalReportRepository(db))
