"""Shared API response schemas."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int
    page_size: int
    total_items: int
    total_pages: int


class ApiResponse(BaseModel, Generic[DataT]):
    """Consistent successful response envelope used by REST endpoints."""

    success: bool
    message: str
    data: DataT | None = None
    pagination: PaginationMeta | None = None

    model_config = ConfigDict(populate_by_name=True)


class ApiErrorResponse(BaseModel):
    """Consistent safe error response envelope."""

    success: bool = False
    message: str
    errors: dict[str, list[str]] = Field(default_factory=dict)
    error: str | None = None
    details: dict[str, object] = Field(default_factory=dict)
