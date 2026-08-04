"""Pydantic schemas for medical history validation and serialization."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MedicalHistoryBase(BaseModel):
    """Shared medical history fields."""

    patient_id: int = Field(gt=0)
    condition_name: str = Field(min_length=1, max_length=255)
    diagnosis_date: date | None = None
    notes: str


class MedicalHistoryCreate(BaseModel):
    """Request schema for creating a medical history record."""

    condition_name: str = Field(min_length=1, max_length=255)
    diagnosis_date: date | None = None
    notes: str


class MedicalHistoryUpdate(BaseModel):
    """Request schema for updating a medical history record."""

    patient_id: int | None = Field(default=None, gt=0)
    condition_name: str | None = Field(default=None, min_length=1, max_length=255)
    diagnosis_date: date | None = None
    notes: str | None = None


class MedicalHistoryRead(MedicalHistoryBase):
    """Response schema for a medical history record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
