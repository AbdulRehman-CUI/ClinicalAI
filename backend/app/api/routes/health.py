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

