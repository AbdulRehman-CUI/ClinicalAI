"""Repository for symptom CRUD operations."""

from sqlalchemy.orm import Session

from app.db.models import Symptom
from app.repositories.base import BaseRepository


class SymptomRepository(BaseRepository[Symptom]):
    """Performs CRUD operations for symptoms."""

    def __init__(self, db: Session) -> None:
        """Create a symptom repository bound to a database session."""
        super().__init__(db, Symptom)

