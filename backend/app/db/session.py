"""Database engine and session configuration."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from app.core.config import get_settings

settings = get_settings()
sqlite = settings.database_url.startswith("sqlite")
pool_options = {
    "pool_size": settings.database_pool_size,
    "max_overflow": settings.database_max_overflow,
    "pool_timeout": settings.database_pool_timeout,
}
if not sqlite:
    # Neon already pools database connections. Avoid a second pool in each function instance.
    pool_options = {"poolclass": NullPool}
elif settings.resolve_database_path() is None:
    pool_options = {"poolclass": StaticPool}

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if sqlite else {"connect_timeout": 10, "prepare_threshold": None},
    pool_pre_ping=True,
    hide_parameters=True,
    **pool_options,
)


if sqlite:

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

def get_db() -> Generator[Session, None, None]:
    """Close the session and roll back any open transaction after each request."""
    with SessionLocal() as db:
        yield db
