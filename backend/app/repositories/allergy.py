"""Repository for allergy CRUD operations."""

from sqlalchemy.orm import Session

from app.db.models import Allergy
from app.repositories.base import BaseRepository


class AllergyRepository(BaseRepository[Allergy]):
    """Performs CRUD operations for allergies."""

    def __init__(self, db: Session) -> None:
        """Create an allergy repository bound to a database session."""
        super().__init__(db, Allergy)

