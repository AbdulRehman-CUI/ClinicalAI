"""Service layer for patient medical history operations."""

from __future__ import annotations

from collections.abc import Sequence
import math

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.medical_history import MedicalHistoryRepository
from app.repositories.patient import PatientRepository
from app.schemas.common import PaginationMeta
from app.schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryRead,
    MedicalHistoryUpdate,
)
from app.services.exceptions import ResourceNotFoundError


class MedicalHistoryService:
    """Coordinate medical history CRUD behavior between repositories and API routers."""

    def __init__(self, history_repository: MedicalHistoryRepository, patient_repository: PatientRepository) -> None:
        self.history_repository = history_repository
        self.patient_repository = patient_repository

    def create(self, patient_id: int, payload: MedicalHistoryCreate) -> MedicalHistoryRead:
        """Create one medical history record for a patient."""
        self._ensure_patient_exists(patient_id)
        data = payload.model_dump(exclude_none=True)
        data["patient_id"] = patient_id
        instance = self.history_repository.create(data)
        return MedicalHistoryRead.model_validate(instance)

    def get(self, history_id: int) -> MedicalHistoryRead:
        """Return one medical history record."""
        instance = self.history_repository.get(history_id)
        if instance is None:
            raise ResourceNotFoundError("Medical history not found.")
        return MedicalHistoryRead.model_validate(instance)

    def list_for_patient(self, patient_id: int, page: int, page_size: int) -> tuple[list[MedicalHistoryRead], PaginationMeta]:
        """Return paginated medical history records for one patient."""
        self._ensure_patient_exists(patient_id)
        offset = (page - 1) * page_size
        total_items = self.history_repository.count()
        instances: Sequence = self.history_repository.list(offset=offset, limit=page_size)
        items = [
            MedicalHistoryRead.model_validate(instance)
            for instance in instances
            if instance.patient_id == patient_id
        ]
        total_items = len(items)
        total_pages = math.ceil(total_items / page_size) if total_items else 1
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return items, pagination

    def update(self, history_id: int, payload: MedicalHistoryUpdate) -> MedicalHistoryRead:
        """Update and return one medical history record."""
        instance = self.history_repository.get(history_id)
        if instance is None:
            raise ResourceNotFoundError("Medical history not found.")
        if payload.patient_id is not None:
            self._ensure_patient_exists(payload.patient_id)
        data = payload.model_dump(exclude_none=True)
        updated_instance = self.history_repository.update(instance, data)
        return MedicalHistoryRead.model_validate(updated_instance)

    def delete(self, history_id: int) -> None:
        """Delete one medical history record."""
        instance = self.history_repository.get(history_id)
        if instance is None:
            raise ResourceNotFoundError("Medical history not found.")
        self.history_repository.delete(instance)

    def _ensure_patient_exists(self, patient_id: int) -> None:
        """Validate that the patient referenced by the request exists."""
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")


def get_medical_history_service(db: Session = Depends(get_db)) -> MedicalHistoryService:
    """Create a medical history service bound to the current database session."""
    return MedicalHistoryService(MedicalHistoryRepository(db), PatientRepository(db))
