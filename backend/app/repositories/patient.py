"""Repository for patient CRUD operations."""

from sqlalchemy.orm import Session

from app.db.models import Patient
from app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    """Performs CRUD operations for patients."""

    def __init__(self, db: Session) -> None:
        """Create a patient repository bound to a database session."""
        super().__init__(db, Patient)

