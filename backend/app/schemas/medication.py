"""Pydantic schemas for medication validation and serialization."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MedicationBase(BaseModel):
    """Shared medication fields."""

    patient_id: int = Field(gt=0)
    medication_name: str = Field(min_length=1, max_length=255)
    dosage: str = Field(min_length=1, max_length=255)
    frequency: str = Field(min_length=1, max_length=255)
    start_date: date
    notes: str


class MedicationCreate(BaseModel):
    """Request schema for creating a medication."""

    medication_name: str = Field(min_length=1, max_length=255)
    dosage: str = Field(min_length=1, max_length=255)
    frequency: str = Field(min_length=1, max_length=255)
    start_date: date
    notes: str


class MedicationUpdate(BaseModel):
    """Request schema for updating a medication."""

    patient_id: int | None = Field(default=None, gt=0)
    medication_name: str | None = Field(default=None, min_length=1, max_length=255)
    dosage: str | None = Field(default=None, min_length=1, max_length=255)
    frequency: str | None = Field(default=None, min_length=1, max_length=255)
    start_date: date | None = None
    notes: str | None = None


class MedicationRead(MedicationBase):
    """Response schema for a medication."""

    model_config = ConfigDict(from_attributes=True)

    id: int
