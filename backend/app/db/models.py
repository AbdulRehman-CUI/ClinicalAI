"""SQLAlchemy ORM models for the documented ClinicalAI entities."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """Represents an authenticated application user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="Staff")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Patient(Base):
    """Represents one patient record."""

    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("age > 0", name="ck_patients_age_positive"),
        CheckConstraint("height_cm > 0", name="ck_patients_height_positive"),
        CheckConstraint("weight_kg > 0", name="ck_patients_weight_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)
    biological_sex: Mapped[str] = mapped_column(String(50), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(20), nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    pregnancy_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    medical_histories: Mapped[list[MedicalHistory]] = relationship(
        back_populates="patient"
    )
    medications: Mapped[list[Medication]] = relationship(back_populates="patient")
    allergies: Mapped[list[Allergy]] = relationship(back_populates="patient")
    symptoms: Mapped[list[Symptom]] = relationship(back_populates="patient")
    medical_reports: Mapped[list[MedicalReport]] = relationship(back_populates="patient")
    ai_analyses: Mapped[list[AIAnalysis]] = relationship(back_populates="patient")


class MedicalHistory(Base):
    """Stores a previous medical condition for a patient."""

    __tablename__ = "medical_histories"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    condition_name: Mapped[str] = mapped_column(String(255), nullable=False)
    diagnosis_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="medical_histories")


class Medication(Base):
    """Stores a current medication for a patient."""

    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    medication_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(255), nullable=False)
    frequency: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="medications")


class Allergy(Base):
    """Stores an allergy for a patient."""

    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    allergen: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(100), nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="allergies")


class Symptom(Base):
    """Stores one symptom entered for a patient consultation."""

    __tablename__ = "symptoms"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    symptom_name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="symptoms")


class MedicalReport(Base):
    """Stores metadata and extracted content for an uploaded medical report."""

    __tablename__ = "medical_reports"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('PDF', 'DOCX', 'TXT', 'PNG', 'JPG', 'JPEG')",
            name="ck_medical_reports_file_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    upload_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="medical_reports")
    ai_analysis: Mapped[AIAnalysis | None] = relationship(
        back_populates="report",
        uselist=False,
    )


class AIAnalysis(Base):
    """Stores the final validated structured AI analysis response."""

    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"),
        nullable=False,
        index=True,
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("medical_reports.id"),
        nullable=True,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    medication_warnings: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    possible_diagnoses: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    supporting_evidence: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    missing_information: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    suggested_next_steps: Mapped[list[Any]] = mapped_column(JSON, nullable=False)

    patient: Mapped[Patient] = relationship(back_populates="ai_analyses")
    report: Mapped[MedicalReport | None] = relationship(back_populates="ai_analysis")
