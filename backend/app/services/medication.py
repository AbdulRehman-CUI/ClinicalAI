"""Service layer for medication operations."""

from __future__ import annotations

from collections.abc import Sequence
import math

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.medication import MedicationRepository
from app.repositories.patient import PatientRepository
from app.schemas.common import PaginationMeta
from app.schemas.medication import MedicationCreate, MedicationRead, MedicationUpdate
from app.services.exceptions import ResourceNotFoundError


class MedicationService:
    """Coordinate medication CRUD behavior between repositories and API routers."""

    def __init__(self, medication_repository: MedicationRepository, patient_repository: PatientRepository) -> None:
        self.medication_repository = medication_repository
        self.patient_repository = patient_repository

    def create(self, patient_id: int, payload: MedicationCreate) -> MedicationRead:
        """Create one medication record for a patient."""
        self._ensure_patient_exists(patient_id)
        data = payload.model_dump(exclude_none=True)
        data["patient_id"] = patient_id
        instance = self.medication_repository.create(data)
        return MedicationRead.model_validate(instance)

    def get(self, medication_id: int) -> MedicationRead:
        """Return one medication record."""
        instance = self.medication_repository.get(medication_id)
        if instance is None:
            raise ResourceNotFoundError("Medication not found.")
        return MedicationRead.model_validate(instance)

    def list_for_patient(self, patient_id: int, page: int, page_size: int) -> tuple[list[MedicationRead], PaginationMeta]:
        """Return paginated medications for one patient."""
        self._ensure_patient_exists(patient_id)
        offset = (page - 1) * page_size
        total_items = self.medication_repository.count()
        instances: Sequence = self.medication_repository.list(offset=offset, limit=page_size)
        items = [MedicationRead.model_validate(instance) for instance in instances if instance.patient_id == patient_id]
        total_items = len(items)
        total_pages = math.ceil(total_items / page_size) if total_items else 1
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return items, pagination

    def update(self, medication_id: int, payload: MedicationUpdate) -> MedicationRead:
        """Update and return one medication record."""
        instance = self.medication_repository.get(medication_id)
        if instance is None:
            raise ResourceNotFoundError("Medication not found.")
        if payload.patient_id is not None:
            self._ensure_patient_exists(payload.patient_id)
        data = payload.model_dump(exclude_none=True)
        updated_instance = self.medication_repository.update(instance, data)
        return MedicationRead.model_validate(updated_instance)

    def delete(self, medication_id: int) -> None:
        """Delete one medication record."""
        instance = self.medication_repository.get(medication_id)
        if instance is None:
            raise ResourceNotFoundError("Medication not found.")
        self.medication_repository.delete(instance)

    def _ensure_patient_exists(self, patient_id: int) -> None:
        """Validate that the patient referenced by the request exists."""
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")


def get_medication_service(db: Session = Depends(get_db)) -> MedicationService:
    """Create a medication service bound to the current database session."""
    return MedicationService(MedicationRepository(db), PatientRepository(db))
