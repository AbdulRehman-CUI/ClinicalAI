"""Pydantic schemas for medical report validation and serialization."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SupportedFileType = Literal["PDF", "DOCX", "TXT", "PNG", "JPG", "JPEG"]


class MedicalReportBase(BaseModel):
    """Shared medical report fields."""

    patient_id: int = Field(gt=0)
    original_filename: str = Field(min_length=1, max_length=255)
    stored_filename: str = Field(min_length=1, max_length=255)
    file_type: SupportedFileType
    extracted_text: str | None = None
    summary: str | None = None


class MedicalReportCreate(MedicalReportBase):
    """Request schema for creating a medical report."""


class MedicalReportUpdate(BaseModel):
    """Request schema for updating a medical report."""

    patient_id: int | None = Field(default=None, gt=0)
    original_filename: str | None = Field(default=None, min_length=1, max_length=255)
    stored_filename: str | None = Field(default=None, min_length=1, max_length=255)
    file_type: SupportedFileType | None = None
    extracted_text: str | None = None
    summary: str | None = None


class MedicalReportRead(MedicalReportBase):
    """Response schema for a medical report."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    upload_timestamp: datetime
