"""Repository for medication CRUD operations."""

from sqlalchemy.orm import Session

from app.db.models import Medication
from app.repositories.base import BaseRepository


class MedicationRepository(BaseRepository[Medication]):
    """Performs CRUD operations for medications."""

    def __init__(self, db: Session) -> None:
        """Create a medication repository bound to a database session."""
        super().__init__(db, Medication)

