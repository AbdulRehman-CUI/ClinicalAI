"""Build a structured context object for AI analysis from patient and report data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PatientContext:
    """Structured patient context passed to the AI prompt builder."""

    patient: dict[str, Any] = field(default_factory=dict)
    medical_history: list[dict[str, Any]] = field(default_factory=list)
    allergies: list[dict[str, Any]] = field(default_factory=list)
    medications: list[dict[str, Any]] = field(default_factory=list)
    symptoms: list[dict[str, Any]] = field(default_factory=list)
    reports: str = ""


class PatientContextBuilder:
    """Collect patient-centered information into a single structured object."""

    def build(
        self,
        *,
        patient: dict[str, Any] | None = None,
        medical_history: list[dict[str, Any]] | None = None,
        allergies: list[dict[str, Any]] | None = None,
        medications: list[dict[str, Any]] | None = None,
        symptoms: list[dict[str, Any]] | None = None,
        reports: str | None = None,
    ) -> PatientContext:
        return PatientContext(
            patient=patient or {},
            medical_history=medical_history or [],
            allergies=allergies or [],
            medications=medications or [],
            symptoms=symptoms or [],
            reports=reports or "",
        )
