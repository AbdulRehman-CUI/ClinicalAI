"""Service layer for medical report operations."""

from __future__ import annotations

from collections.abc import Sequence
import math
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, UploadFile
from sqlalchemy.orm import Session

from app.ai.report_processor import ReportProcessor
from app.core.config import get_settings
from app.db.session import get_db
from app.repositories.medical_report import MedicalReportRepository
from app.repositories.patient import PatientRepository
from app.schemas.common import PaginationMeta
from app.schemas.medical_report import MedicalReportCreate, MedicalReportRead
from app.services.exceptions import ResourceNotFoundError, ValidationError

settings = get_settings()
REPORTS_STORAGE_DIR = settings.resolve_upload_directory()
REPORTS_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PROCESSOR = ReportProcessor()


class MedicalReportService:
    """Coordinate medical report CRUD behavior between repositories and API routers."""

    def __init__(self, report_repository: MedicalReportRepository, patient_repository: PatientRepository) -> None:
        self.report_repository = report_repository
        self.patient_repository = patient_repository

    def create(self, patient_id: int, upload: UploadFile) -> MedicalReportRead:
        """Persist an uploaded medical report and return its metadata."""
        self._ensure_patient_exists(patient_id)
        if upload.filename is None:
            raise ValidationError("A filename is required.")
        suffix = Path(upload.filename).suffix.upper().lstrip(".")
        if suffix not in settings.allowed_file_extensions:
            raise ValidationError("Only supported upload file types are allowed.")
        if upload.size and upload.size > settings.max_upload_size_mb * 1024 * 1024:
            raise ValidationError(f"File size exceeds the {settings.max_upload_size_mb} MB limit.")

        stored_filename = f"{uuid4().hex}_{Path(upload.filename).name}"
        destination = REPORTS_STORAGE_DIR / stored_filename
        content = upload.file.read()
        destination.write_bytes(content)

        extracted_text = None
        if suffix.upper() in REPORT_PROCESSOR.supported_extensions:
            extracted_text = REPORT_PROCESSOR.extract_text(destination)

        data = {
            "patient_id": patient_id,
            "original_filename": upload.filename,
            "stored_filename": stored_filename,
            "file_type": suffix.upper(),
            "extracted_text": extracted_text,
            "summary": None,
        }
        instance = self.report_repository.create(data)
        return MedicalReportRead.model_validate(instance)

    def get(self, report_id: int) -> MedicalReportRead:
        """Return one medical report."""
        instance = self.report_repository.get(report_id)
        if instance is None:
            raise ResourceNotFoundError("Medical report not found.")
        return MedicalReportRead.model_validate(instance)

    def list_for_patient(self, patient_id: int, page: int, page_size: int) -> tuple[list[MedicalReportRead], PaginationMeta]:
        """Return paginated medical reports for one patient."""
        self._ensure_patient_exists(patient_id)
        offset = (page - 1) * page_size
        total_items = self.report_repository.count()
        instances: Sequence = self.report_repository.list(offset=offset, limit=page_size)
        items = [MedicalReportRead.model_validate(instance) for instance in instances if instance.patient_id == patient_id]
        total_items = len(items)
        total_pages = math.ceil(total_items / page_size) if total_items else 1
        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )
        return items, pagination

    def delete(self, report_id: int) -> None:
        """Delete one medical report and its stored file."""
        instance = self.report_repository.get(report_id)
        if instance is None:
            raise ResourceNotFoundError("Medical report not found.")
        file_path = REPORTS_STORAGE_DIR / instance.stored_filename
        if file_path.exists():
            file_path.unlink()
        self.report_repository.delete(instance)

    def _ensure_patient_exists(self, patient_id: int) -> None:
        """Validate that the patient referenced by the request exists."""
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")


def get_medical_report_service(db: Session = Depends(get_db)) -> MedicalReportService:
    """Create a medical report service bound to the current database session."""
    return MedicalReportService(MedicalReportRepository(db), PatientRepository(db))
