"""Service layer for symptom operations."""

from __future__ import annotations

from collections.abc import Sequence
import math

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.patient import PatientRepository
from app.repositories.symptom import SymptomRepository
from app.schemas.common import PaginationMeta
from app.schemas.symptom import SymptomCreate, SymptomRead, SymptomUpdate
from app.services.exceptions import ResourceNotFoundError


class SymptomService:
    """Coordinate symptom CRUD behavior between repositories and API routers."""

    def __init__(self, symptom_repository: SymptomRepository, patient_repository: PatientRepository) -> None:
        self.symptom_repository = symptom_repository
        self.patient_repository = patient_repository

    def create(self, patient_id: int, payload: SymptomCreate) -> SymptomRead:
        """Create one symptom record for a patient."""
        self._ensure_patient_exists(patient_id)
        data = payload.model_dump(exclude_none=True)
        data["patient_id"] = patient_id
        instance = self.symptom_repository.create(data)
        return SymptomRead.model_validate(instance)

    def get(self, symptom_id: int) -> SymptomRead:
        """Return one symptom record."""
        instance = self.symptom_repository.get(symptom_id)
        if instance is None:
            raise ResourceNotFoundError("Symptom not found.")
        return SymptomRead.model_validate(instance)

    def list_for_patient(self, patient_id: int, page: int, page_size: int) -> tuple[list[SymptomRead], PaginationMeta]:
        """Return paginated symptoms for one patient."""
        self._ensure_patient_exists(patient_id)
        offset = (page - 1) * page_size
        total_items = self.symptom_repository.count()
        instances: Sequence = self.symptom_repository.list(offset=offset, limit=page_size)
        items = [SymptomRead.model_validate(instance) for instance in instances if instance.patient_id == patient_id]
        total_items = len(items)
        total_pages = math.ceil(total_items / page_size) if total_items else 1
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return items, pagination

    def update(self, symptom_id: int, payload: SymptomUpdate) -> SymptomRead:
        """Update and return one symptom record."""
        instance = self.symptom_repository.get(symptom_id)
        if instance is None:
            raise ResourceNotFoundError("Symptom not found.")
        if payload.patient_id is not None:
            self._ensure_patient_exists(payload.patient_id)
        data = payload.model_dump(exclude_none=True)
        updated_instance = self.symptom_repository.update(instance, data)
        return SymptomRead.model_validate(updated_instance)

    def delete(self, symptom_id: int) -> None:
        """Delete one symptom record."""
        instance = self.symptom_repository.get(symptom_id)
        if instance is None:
            raise ResourceNotFoundError("Symptom not found.")
        self.symptom_repository.delete(instance)

    def _ensure_patient_exists(self, patient_id: int) -> None:
        """Validate that the patient referenced by the request exists."""
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")


def get_symptom_service(db: Session = Depends(get_db)) -> SymptomService:
    """Create a symptom service bound to the current database session."""
    return SymptomService(SymptomRepository(db), PatientRepository(db))
