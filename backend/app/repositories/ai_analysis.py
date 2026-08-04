"""Repository for AI analysis CRUD operations."""

from sqlalchemy.orm import Session

from app.db.models import AIAnalysis
from app.repositories.base import BaseRepository


class AIAnalysisRepository(BaseRepository[AIAnalysis]):
    """Performs CRUD operations for AI analyses."""

    def __init__(self, db: Session) -> None:
        """Create an AI analysis repository bound to a database session."""
        super().__init__(db, AIAnalysis)

