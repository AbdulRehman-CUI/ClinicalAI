"""Repository for medical report CRUD operations."""

from sqlalchemy.orm import Session

from app.db.models import MedicalReport
from app.repositories.base import BaseRepository


class MedicalReportRepository(BaseRepository[MedicalReport]):
    """Performs CRUD operations for medical reports."""

    def __init__(self, db: Session) -> None:
        """Create a medical report repository bound to a database session."""
        super().__init__(db, MedicalReport)

