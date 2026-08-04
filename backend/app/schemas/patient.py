"""Pydantic schemas for patient validation and serialization."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    """Shared patient fields."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    age: int = Field(gt=0)
    biological_sex: str = Field(min_length=1, max_length=50)
    blood_group: str = Field(min_length=1, max_length=20)
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    pregnancy_status: str | None = Field(default=None, max_length=50)


class PatientCreate(PatientBase):
    """Request schema for creating a patient."""


class PatientUpdate(BaseModel):
    """Request schema for updating a patient."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    age: int | None = Field(default=None, gt=0)
    biological_sex: str | None = Field(default=None, min_length=1, max_length=50)
    blood_group: str | None = Field(default=None, min_length=1, max_length=20)
    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    pregnancy_status: str | None = Field(default=None, max_length=50)


class PatientRead(PatientBase):
    """Response schema for a patient."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime

