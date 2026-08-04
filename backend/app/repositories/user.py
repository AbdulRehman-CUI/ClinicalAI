"""Repository for user persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Persist and query authenticated users."""

    def __init__(self, db: Session) -> None:
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        """Return one user by email address."""
        statement = select(User).where(User.email == email)
        return self.db.scalar(statement)
