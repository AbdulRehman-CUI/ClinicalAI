"""Service layer for patient domain operations."""

from __future__ import annotations

from collections.abc import Sequence
import math

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.patient import PatientRepository
from app.schemas.common import PaginationMeta
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.services.exceptions import ResourceNotFoundError


class PatientService:
    """Coordinate patient CRUD behavior between repositories and API routers."""

    def __init__(self, repository: PatientRepository) -> None:
        self.repository = repository

    def create(self, payload: PatientCreate) -> PatientRead:
        """Create and return one patient."""
        instance = self.repository.create(payload.model_dump())
        return PatientRead.model_validate(instance)

    def get(self, patient_id: int) -> PatientRead:
        """Return one patient by its identifier."""
        instance = self.repository.get(patient_id)
        if instance is None:
            raise ResourceNotFoundError("Patient not found.")
        return PatientRead.model_validate(instance)

    def list(self, page: int, page_size: int) -> tuple[list[PatientRead], PaginationMeta]:
        """Return paginated patients."""
        offset = (page - 1) * page_size
        total_items = self.repository.count()
        instances: Sequence = self.repository.list(offset=offset, limit=page_size)
        items = [PatientRead.model_validate(instance) for instance in instances]
        total_pages = math.ceil(total_items / page_size) if total_items else 1
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return items, pagination

    def update(self, patient_id: int, payload: PatientUpdate) -> PatientRead:
        """Update and return one patient."""
        instance = self.repository.get(patient_id)
        if instance is None:
            raise ResourceNotFoundError("Patient not found.")
        data = payload.model_dump(exclude_none=True)
        updated_instance = self.repository.update(instance, data)
        return PatientRead.model_validate(updated_instance)

    def delete(self, patient_id: int) -> None:
        """Delete one patient."""
        instance = self.repository.get(patient_id)
        if instance is None:
            raise ResourceNotFoundError("Patient not found.")
        self.repository.delete(instance)


def get_patient_service(db: Session = Depends(get_db)) -> PatientService:
    """Create a patient service bound to the current database session."""
    return PatientService(PatientRepository(db))
