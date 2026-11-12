"""Base repository with shared CRUD operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import Patient

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Provides CRUD operations for a SQLAlchemy model."""

    def __init__(self, db: Session, model: type[ModelT]) -> None:
        """Create a repository bound to a database session and model."""
        self.db = db
        self.model = model

    @property
    def workspace_id(self) -> str:
        return self.db.info["workspace_id"]

    def select_owned(self, patient_id: int | None = None):
        if self.model is Patient:
            return select(Patient).where(Patient.workspace_id == self.workspace_id)
        owned_patients = select(Patient.id).where(Patient.workspace_id == self.workspace_id)
        statement = select(self.model).where(self.model.patient_id.in_(owned_patients))
        if patient_id is not None:
            statement = statement.where(self.model.patient_id == patient_id)
        return statement

    def create(self, data: Mapping[str, Any]) -> ModelT:
        """Create and persist one model instance."""
        values = dict(data)
        if self.model is Patient:
            values["workspace_id"] = self.workspace_id
        instance = self.model(**values)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get(self, item_id: int, *, for_update: bool = False) -> ModelT | None:
        """Return one model instance by primary key."""
        statement = self.select_owned().where(self.model.id == item_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def list(self, offset: int = 0, limit: int = 100, *, patient_id: int | None = None) -> Sequence[ModelT]:
        """Return model instances using offset and limit pagination."""
        statement = self.select_owned(patient_id).order_by(self.model.id).offset(offset).limit(limit)
        return self.db.scalars(statement).all()

    def count(self, *, patient_id: int | None = None) -> int:
        """Return the total number of model records."""
        return self.db.scalar(select(func.count()).select_from(self.select_owned(patient_id).subquery()))

    def update(self, instance: ModelT, data: Mapping[str, Any]) -> ModelT:
        """Update and persist one existing model instance."""
        for field_name, value in data.items():
            setattr(instance, field_name, value)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        """Delete one existing model instance."""
        self.db.delete(instance)
        self.db.commit()

