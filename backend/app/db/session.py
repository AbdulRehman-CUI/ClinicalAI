"""Database engine and session configuration."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
import logging
from app.db.base import Base

settings = get_settings()

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: Any,
        _connection_record: object,
    ) -> None:
        """Ensure SQLite enforces documented foreign key relationships."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models so the metadata is registered before creating tables.
from app.db import models  # noqa: F401

Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for future FastAPI dependencies."""
    logger = logging.getLogger(__name__)
    logger.debug("Creating new DB session")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("Closed DB session")
