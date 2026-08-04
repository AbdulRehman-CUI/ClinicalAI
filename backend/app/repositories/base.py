"""Base repository with shared CRUD operations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Provides CRUD operations for a SQLAlchemy model."""

    def __init__(self, db: Session, model: type[ModelT]) -> None:
        """Create a repository bound to a database session and model."""
        self.db = db
        self.model = model

    def create(self, data: Mapping[str, Any]) -> ModelT:
        """Create and persist one model instance."""
        instance = self.model(**data)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def get(self, item_id: int) -> ModelT | None:
        """Return one model instance by primary key."""
        return self.db.get(self.model, item_id)

    def list(self, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        """Return model instances using offset and limit pagination."""
        statement = select(self.model).offset(offset).limit(limit)
        return self.db.scalars(statement).all()

    def count(self) -> int:
        """Return the total number of model records."""
        return self.db.query(self.model).count()

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

