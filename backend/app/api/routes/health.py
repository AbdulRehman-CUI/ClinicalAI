"""Placeholder health endpoint for infrastructure checks."""

from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.health import HealthCheck

router = APIRouter()


@router.get("/health", response_model=ApiResponse[HealthCheck], response_model_exclude_none=True)
async def health_check() -> ApiResponse[HealthCheck]:
    """Return basic service status without exposing internal details."""
    return ApiResponse(
        success=True,
        message="Backend service is healthy.",
        data=HealthCheck(status="ok"),
        pagination=None,
    )


@router.get("/readiness")
def readiness():
    """Configuration and schema readiness, without credentials or provider calls."""
    from app.core.config import get_settings
    from app.db.session import engine
    from sqlalchemy import text
    from fastapi.responses import JSONResponse
    issues = get_settings().storage_issues()
    database_ready = False
    try:
        with engine.connect() as connection:
            database_ready = connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "20261120_0001"
    except Exception:
        pass
    ready = not issues and database_ready
    return JSONResponse(status_code=200 if ready else 503, content={
        "ready": ready,
        "storage": {"configured": not issues, "issues": issues},
        "database": {"ready": database_ready, "message": "Schema current" if database_ready else "Check database connectivity and run Alembic upgrade head."},
    })
