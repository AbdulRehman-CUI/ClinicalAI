"""Pydantic schemas for allergy validation and serialization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AllergyBase(BaseModel):
    """Shared allergy fields."""

    patient_id: int = Field(gt=0)
    allergen: str = Field(min_length=1, max_length=255)
    reaction: str = Field(min_length=1, max_length=255)
    severity: str = Field(min_length=1, max_length=100)


class AllergyCreate(BaseModel):
    """Request schema for creating an allergy."""

    allergen: str = Field(min_length=1, max_length=255)
    reaction: str = Field(min_length=1, max_length=255)
    severity: str = Field(min_length=1, max_length=100)


class AllergyUpdate(BaseModel):
    """Request schema for updating an allergy."""

    patient_id: int | None = Field(default=None, gt=0)
    allergen: str | None = Field(default=None, min_length=1, max_length=255)
    reaction: str | None = Field(default=None, min_length=1, max_length=255)
    severity: str | None = Field(default=None, min_length=1, max_length=100)


class AllergyRead(AllergyBase):
    """Response schema for an allergy."""

    model_config = ConfigDict(from_attributes=True)

    id: int
