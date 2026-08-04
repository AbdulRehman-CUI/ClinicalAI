"""Pydantic schemas for symptom validation and serialization."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SymptomBase(BaseModel):
    """Shared symptom fields."""

    patient_id: int = Field(gt=0)
    symptom_name: str = Field(min_length=1, max_length=255)
    duration: str = Field(min_length=1, max_length=255)
    severity: str = Field(min_length=1, max_length=100)
    notes: str


class SymptomCreate(BaseModel):
    """Request schema for creating a symptom."""

    symptom_name: str = Field(min_length=1, max_length=255)
    duration: str = Field(min_length=1, max_length=255)
    severity: str = Field(min_length=1, max_length=100)
    notes: str


class SymptomUpdate(BaseModel):
    """Request schema for updating a symptom."""

    patient_id: int | None = Field(default=None, gt=0)
    symptom_name: str | None = Field(default=None, min_length=1, max_length=255)
    duration: str | None = Field(default=None, min_length=1, max_length=255)
    severity: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = None


class SymptomRead(SymptomBase):
    """Response schema for a symptom."""

    model_config = ConfigDict(from_attributes=True)

    id: int
