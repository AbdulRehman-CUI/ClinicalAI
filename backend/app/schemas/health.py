"""Schemas for non-domain infrastructure health checks."""

from pydantic import BaseModel


class HealthCheck(BaseModel):
    """Minimal status payload for the placeholder health endpoint."""

    status: str

