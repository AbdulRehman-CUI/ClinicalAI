"""Service layer for allergy operations."""

from __future__ import annotations

from collections.abc import Sequence
import math

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.allergy import AllergyRepository
from app.repositories.patient import PatientRepository
from app.schemas.allergy import AllergyCreate, AllergyRead, AllergyUpdate
from app.schemas.common import PaginationMeta
from app.services.exceptions import ResourceNotFoundError


class AllergyService:
    """Coordinate allergy CRUD behavior between repositories and API routers."""

    def __init__(self, allergy_repository: AllergyRepository, patient_repository: PatientRepository) -> None:
        self.allergy_repository = allergy_repository
        self.patient_repository = patient_repository

    def create(self, patient_id: int, payload: AllergyCreate) -> AllergyRead:
        """Create one allergy record for a patient."""
        self._ensure_patient_exists(patient_id)
        data = payload.model_dump(exclude_none=True)
        data["patient_id"] = patient_id
        instance = self.allergy_repository.create(data)
        return AllergyRead.model_validate(instance)

    def get(self, allergy_id: int) -> AllergyRead:
        """Return one allergy record."""
        instance = self.allergy_repository.get(allergy_id)
        if instance is None:
            raise ResourceNotFoundError("Allergy not found.")
        return AllergyRead.model_validate(instance)

    def list_for_patient(self, patient_id: int, page: int, page_size: int) -> tuple[list[AllergyRead], PaginationMeta]:
        """Return paginated allergies for one patient."""
        self._ensure_patient_exists(patient_id)
        offset = (page - 1) * page_size
        total_items = self.allergy_repository.count()
        instances: Sequence = self.allergy_repository.list(offset=offset, limit=page_size)
        items = [AllergyRead.model_validate(instance) for instance in instances if instance.patient_id == patient_id]
        total_items = len(items)
        total_pages = math.ceil(total_items / page_size) if total_items else 1
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return items, pagination

    def update(self, allergy_id: int, payload: AllergyUpdate) -> AllergyRead:
        """Update and return one allergy record."""
        instance = self.allergy_repository.get(allergy_id)
        if instance is None:
            raise ResourceNotFoundError("Allergy not found.")
        if payload.patient_id is not None:
            self._ensure_patient_exists(payload.patient_id)
        data = payload.model_dump(exclude_none=True)
        updated_instance = self.allergy_repository.update(instance, data)
        return AllergyRead.model_validate(updated_instance)

    def delete(self, allergy_id: int) -> None:
        """Delete one allergy record."""
        instance = self.allergy_repository.get(allergy_id)
        if instance is None:
            raise ResourceNotFoundError("Allergy not found.")
        self.allergy_repository.delete(instance)

    def _ensure_patient_exists(self, patient_id: int) -> None:
        """Validate that the patient referenced by the request exists."""
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")


def get_allergy_service(db: Session = Depends(get_db)) -> AllergyService:
    """Create an allergy service bound to the current database session."""
    return AllergyService(AllergyRepository(db), PatientRepository(db))
