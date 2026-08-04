"""Pydantic schemas for AI analysis validation and serialization."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AIAnalysisBase(BaseModel):
    """Shared AI analysis fields for validated final responses."""

    patient_id: int = Field(gt=0)
    report_id: int | None = Field(default=None, gt=0)
    medication_warnings: list[str]
    possible_diagnoses: list[str]
    confidence: float
    supporting_evidence: list[str]
    missing_information: list[str]
    suggested_next_steps: list[str]


class AIAnalysisCreate(AIAnalysisBase):
    """Request schema for storing a validated AI analysis."""


class AIAnalysisUpdate(BaseModel):
    """Request schema for updating a stored AI analysis."""

    patient_id: int | None = Field(default=None, gt=0)
    report_id: int | None = Field(default=None, gt=0)
    medication_warnings: list[str] | None = None
    possible_diagnoses: list[str] | None = None
    confidence: float | None = None
    supporting_evidence: list[str] | None = None
    missing_information: list[str] | None = None
    suggested_next_steps: list[str] | None = None


class AIAnalysisRead(AIAnalysisBase):
    """Response schema for a stored AI analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
