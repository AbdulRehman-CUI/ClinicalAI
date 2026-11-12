"""Service layer for medical report operations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from io import BytesIO
import logging
import math
from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

import jwt
from fastapi import Depends, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.report_processor import ReportProcessor
from app.core.config import get_settings
from app.db.models import MedicalReport, ReportStorageDeletion
from app.db.session import SessionLocal, get_db
from app.repositories.medical_report import MedicalReportRepository
from app.repositories.patient import PatientRepository
from app.schemas.common import PaginationMeta
from app.schemas.medical_report import MedicalReportRead, ReportUploadIntent, ReportUploadRequest
from app.services.exceptions import ResourceNotFoundError, StorageUnavailableError, ValidationError
from app.services.report_storage import LocalReportStorage, S3ReportStorage, get_s3_report_storage

settings = get_settings()
logger = logging.getLogger(__name__)
REPORTS_STORAGE_DIR = settings.resolve_upload_directory()
REPORT_PROCESSOR = ReportProcessor()
UPLOAD_AUDIENCE = "clinicalai-report-upload"
CONTENT_TYPES = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "TXT": "text/plain",
    "PNG": "image/png",
    "JPG": "image/jpeg",
    "JPEG": "image/jpeg",
}


def get_report_storage(workspace_id: str | None) -> LocalReportStorage | S3ReportStorage:
    if settings.storage_provider == "s3":
        return get_s3_report_storage()
    directory = REPORTS_STORAGE_DIR / workspace_id if workspace_id else REPORTS_STORAGE_DIR
    return LocalReportStorage(directory)


def object_name(workspace_id: str | None, name: str) -> str:
    if settings.storage_provider == "s3" and workspace_id:
        return f"{workspace_id}/{name}"
    return name


class MedicalReportService:
    """Coordinate medical report CRUD behavior between repositories and API routers."""

    def __init__(self, report_repository: MedicalReportRepository, patient_repository: PatientRepository) -> None:
        self.report_repository = report_repository
        self.patient_repository = patient_repository

    @property
    def workspace_id(self) -> str:
        return self.report_repository.workspace_id

    @property
    def max_bytes(self) -> int:
        return settings.max_upload_size_mb * 1024 * 1024

    def _extension(self, filename: str) -> str:
        extension = PureWindowsPath(filename).suffix.upper().lstrip(".")
        if "\x00" in filename or len(filename) > 255:
            raise ValidationError("Invalid report filename.")
        if extension not in CONTENT_TYPES or extension not in settings.allowed_file_extensions:
            raise ValidationError("Only supported upload file types are allowed.")
        return extension

    def _check_size(self, size: int) -> None:
        if size > self.max_bytes:
            raise ValidationError(f"File size exceeds the {settings.max_upload_size_mb} MB limit.")

    def create(self, patient_id: int, upload: UploadFile) -> MedicalReportRead:
        """Persist an uploaded medical report and return its metadata."""
        self._ensure_patient_exists(patient_id)
        if not upload.filename:
            raise ValidationError("A filename is required.")
        extension = self._extension(upload.filename)
        if upload.size is not None:
            self._check_size(upload.size)
        content = upload.file.read(self.max_bytes + 1)
        self._check_size(len(content))
        storage = get_report_storage(self.workspace_id)
        if isinstance(storage, S3ReportStorage):
            self._validate_content(content, extension)
        return self._persist(patient_id, upload.filename, self._new_name(extension), extension, content, storage)

    def authorize_upload(self, patient_id: int, request: ReportUploadRequest) -> ReportUploadIntent:
        """Issue a short-lived POST policy bound to this workspace and patient."""
        storage = self._direct_storage()
        self._ensure_patient_exists(patient_id)
        extension = self._extension(request.filename)
        self._check_size(request.size)
        name = self._new_name(extension)
        post = storage.authorize_upload(object_name(self.workspace_id, name), CONTENT_TYPES[extension], request.size)
        token = jwt.encode(
            {
                "aud": UPLOAD_AUDIENCE,
                "sub": self.workspace_id,
                "patient_id": patient_id,
                "name": name,
                "filename": request.filename,
                "size": request.size,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            },
            settings.workspace_signing_secret,
            algorithm="HS256",
        )
        return ReportUploadIntent(token=token, **post)

    def complete_upload(self, patient_id: int, token: str) -> MedicalReportRead:
        storage = self._direct_storage()
        try:
            claims = jwt.decode(
                token, settings.workspace_signing_secret, algorithms=["HS256"],
                audience=UPLOAD_AUDIENCE,
                options={"require": ["aud", "sub", "exp", "patient_id", "name", "filename", "size"]},
            )
        except jwt.PyJWTError as exc:
            raise ValidationError("Invalid or expired report upload.") from exc
        if claims["sub"] != self.workspace_id or claims["patient_id"] != patient_id:
            raise ValidationError("Invalid or expired report upload.")
        name, filename, size = claims["name"], claims["filename"], claims["size"]
        extension = self._extension(filename)
        self._check_size(size)
        db = self.report_repository.db
        # Serialize finalization per patient so a retry observes the committed report.
        if self.patient_repository.get(patient_id, for_update=True) is None:
            raise ResourceNotFoundError("Patient not found.")
        existing = db.scalar(self.report_repository.select_owned(patient_id).where(
            MedicalReport.stored_filename == name
        ))
        if existing is not None:
            return self._read(existing)
        key = object_name(self.workspace_id, name)
        try:
            content = storage.read_upload(key, CONTENT_TYPES[extension], size)
            self._validate_content(content, extension)
        except ValidationError:
            self._delete_staged(storage, key)
            raise
        result = self._persist(patient_id, filename, name, extension, content, storage)
        self._delete_staged(storage, key)
        return result

    @staticmethod
    def _direct_storage() -> S3ReportStorage:
        if settings.storage_provider != "s3":
            raise ResourceNotFoundError("Direct report uploads are not enabled.")
        return get_s3_report_storage()

    @staticmethod
    def _new_name(extension: str) -> str:
        return f"{uuid4().hex}.{extension.lower()}"

    @staticmethod
    def _validate_content(content: bytes, extension: str) -> None:
        valid = bool(content)
        if extension == "PDF":
            valid = content.startswith(b"%PDF-")
        elif extension == "PNG":
            valid = content.startswith(b"\x89PNG\r\n\x1a\n")
        elif extension in {"JPEG", "JPG"}:
            valid = content.startswith(b"\xff\xd8\xff")
        elif extension == "TXT":
            valid = bool(content) and b"\x00" not in content
        elif extension == "DOCX":
            try:
                with ZipFile(BytesIO(content)) as archive:
                    valid = (
                        {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist())
                        and sum(entry.file_size for entry in archive.infolist()) <= 100 * 1024 * 1024
                    )
            except BadZipFile:
                valid = False
        if not valid:
            raise ValidationError("The uploaded file does not match a supported report format.")

    @staticmethod
    def _delete_staged(storage: S3ReportStorage, name: str) -> None:
        try:
            storage.delete_upload(name)
        except StorageUnavailableError:
            logger.warning("Staged report cleanup deferred to bucket lifecycle policy")

    def _persist(
        self, patient_id: int, filename: str, name: str, extension: str, content: bytes,
        storage: LocalReportStorage | S3ReportStorage,
    ) -> MedicalReportRead:
        extracted_text = None
        if extension in REPORT_PROCESSOR.supported_extensions:
            with TemporaryDirectory() as directory:
                source = Path(directory) / name
                source.write_bytes(content)
                extracted_text = REPORT_PROCESSOR.extract_text(source).replace("\x00", "")

        db = self.report_repository.db
        instance = MedicalReport(
            patient_id=patient_id, original_filename=filename, stored_filename=name,
            file_type=extension, extracted_text=extracted_text,
        )
        db.add(instance)
        db.flush()
        result = self._read(instance)
        key = object_name(self.workspace_id, name)
        try:
            storage.put(key, content, CONTENT_TYPES[extension])
        except StorageUnavailableError:
            db.rollback()
            try:
                storage.delete(key)
            except StorageUnavailableError:
                logger.error("Could not clean up a failed report write")
            raise
        try:
            db.commit()
        except Exception:
            # A lost commit acknowledgement can mean the record exists. Keep the object
            # for an idempotent retry or reconciliation rather than deleting a live report.
            logger.error("Report metadata commit failed; verify storage against the database")
            raise
        return result

    @staticmethod
    def _read(instance: MedicalReport) -> MedicalReportRead:
        report = MedicalReportRead.model_validate(instance)
        if settings.is_production and report.extracted_text:
            # Keep paginated JSON within the function response limit.
            report.extracted_text = report.extracted_text.encode()[:4096].decode(errors="ignore")
        return report

    def get(self, report_id: int) -> MedicalReportRead:
        """Return one medical report."""
        instance = self.report_repository.get(report_id)
        if instance is None:
            raise ResourceNotFoundError("Medical report not found.")
        return self._read(instance)

    def download(self, report_id: int) -> str | Path:
        report = self.get(report_id)
        storage = get_report_storage(self.workspace_id)
        return storage.download(object_name(self.workspace_id, report.stored_filename), report.file_type)

    def list_for_patient(self, patient_id: int, page: int, page_size: int) -> tuple[list[MedicalReportRead], PaginationMeta]:
        """Return paginated medical reports for one patient."""
        self._ensure_patient_exists(patient_id)
        offset = (page - 1) * page_size
        total_items = self.report_repository.count(patient_id=patient_id)
        instances: Sequence = self.report_repository.list(offset=offset, limit=page_size, patient_id=patient_id)
        items = [self._read(instance) for instance in instances]
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
        db = self.report_repository.db
        instance = self.report_repository.get(report_id, for_update=True)
        if instance is not None:
            db.add(ReportStorageDeletion(report_id=report_id, stored_filename=instance.stored_filename,
                                         workspace_id=self.workspace_id))
            db.delete(instance)
            db.commit()
        if not purge_report_deletions(db, report_id, self.workspace_id) and instance is None:
            raise ResourceNotFoundError("Medical report not found.")

    def _ensure_patient_exists(self, patient_id: int) -> None:
        """Validate that the patient referenced by the request exists."""
        patient = self.patient_repository.get(patient_id)
        if patient is None:
            raise ResourceNotFoundError("Patient not found.")


def get_medical_report_service(db: Session = Depends(get_db)) -> MedicalReportService:
    """Create a medical report service bound to the current database session."""
    return MedicalReportService(MedicalReportRepository(db), PatientRepository(db))


def purge_report_deletions(db: Session, report_id: int | None = None, workspace_id: str | None = None) -> int:
    """Retry durable cleanup after a storage outage or interrupted request."""
    query = select(ReportStorageDeletion.stored_filename, ReportStorageDeletion.workspace_id)
    if report_id is not None:
        query = query.where(ReportStorageDeletion.report_id == report_id,
                            ReportStorageDeletion.workspace_id == workspace_id)
    rows = db.execute(query).all()
    db.rollback()
    for name, owner in rows:
        get_report_storage(owner).delete(object_name(owner, name))
        db.execute(delete(ReportStorageDeletion).where(ReportStorageDeletion.stored_filename == name))
        db.commit()
    return len(rows)


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"Removed {purge_report_deletions(session)} queued report objects.")
