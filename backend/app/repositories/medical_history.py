"""Repository for medical history CRUD operations."""

from sqlalchemy.orm import Session

from app.db.models import MedicalHistory
from app.repositories.base import BaseRepository


class MedicalHistoryRepository(BaseRepository[MedicalHistory]):
    """Performs CRUD operations for medical history records."""

    def __init__(self, db: Session) -> None:
        """Create a medical history repository bound to a database session."""
        super().__init__(db, MedicalHistory)

