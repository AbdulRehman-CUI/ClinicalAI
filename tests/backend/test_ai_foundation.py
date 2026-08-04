from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from fastapi import UploadFile
from pypdf import PdfWriter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.context_builder import PatientContextBuilder
from app.ai.prompt_builder import PromptBuilder
from app.ai.report_processor import ReportProcessor
from app.db import session as db_session_module
from app.db.base import Base
from app.repositories.medical_report import MedicalReportRepository
from app.repositories.patient import PatientRepository
from app.services.medical_report import MedicalReportService


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db_session_module.engine = engine
    db_session_module.SessionLocal = TestingSessionLocal
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_report_processor_extracts_supported_formats(tmp_path: Path) -> None:
    processor = ReportProcessor()

    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("Patient has a fever.\nNeeds follow-up.", encoding="utf-8")
    assert processor.extract_text(txt_path) == "Patient has a fever.\nNeeds follow-up."

    docx_path = tmp_path / "report.docx"
    document = Document()
    document.add_paragraph("CBC shows mild leukocytosis.")
    document.save(docx_path)
    assert "CBC shows mild leukocytosis" in processor.extract_text(docx_path)

    pdf_path = tmp_path / "summary.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.add_blank_page(width=72, height=72)
    writer.write(pdf_path)
    assert processor.extract_text(pdf_path) == ""


def test_medical_report_service_stores_extracted_text(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.medical_report.REPORTS_STORAGE_DIR", tmp_path)
    patient_repository = PatientRepository(db_session)
    report_repository = MedicalReportRepository(db_session)
    service = MedicalReportService(report_repository, patient_repository)

    patient = patient_repository.create(
        {
            "first_name": "Alice",
            "last_name": "Nguyen",
            "age": 42,
            "biological_sex": "female",
            "blood_group": "A+",
            "height_cm": 165.0,
            "weight_kg": 69.0,
            "pregnancy_status": "none",
        }
    )

    upload = UploadFile(filename="sample.txt", file=BytesIO(b"Headache and dizziness"))
    report = service.create(patient.id, upload)

    assert report.extracted_text == "Headache and dizziness"


def test_prompt_builder_generates_structured_prompts() -> None:
    builder = PromptBuilder()
    context = PatientContextBuilder().build(
        patient={"first_name": "Diana", "last_name": "Lopez", "age": 29},
        medical_history=[{"condition_name": "Asthma"}],
        allergies=[{"allergen": "Penicillin"}],
        medications=[{"medication_name": "Metformin"}],
        symptoms=[{"symptom_name": "Cough"}],
        reports="Chest X-ray is clear.",
    )

    system_prompt = builder.build_system_prompt(context)
    user_prompt = builder.build_user_prompt(context)

    assert "You are a clinical decision support assistant" in system_prompt
    assert "Diana" in user_prompt
    assert "Chest X-ray is clear" in user_prompt
