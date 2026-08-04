"""REST endpoints for medical report uploads and retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.schemas.common import ApiResponse
from app.schemas.medical_report import MedicalReportRead
from app.services.medical_report import MedicalReportService, get_medical_report_service

router = APIRouter(prefix="/patients", tags=["medical-reports"])


@router.post("/{patient_id}/reports", response_model=ApiResponse[MedicalReportRead], status_code=status.HTTP_201_CREATED)
async def upload_report(
    patient_id: int,
    file: UploadFile = File(...),
    service: MedicalReportService = Depends(get_medical_report_service),
) -> ApiResponse[MedicalReportRead]:
    """Upload and persist one medical report."""
    report = service.create(patient_id, file)
    return ApiResponse(success=True, message="Medical report uploaded successfully.", data=report)


@router.get("/{patient_id}/reports", response_model=ApiResponse[list[MedicalReportRead]])
async def list_reports(
    patient_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: MedicalReportService = Depends(get_medical_report_service),
) -> ApiResponse[list[MedicalReportRead]]:
    """Return medical reports for one patient."""
    items, pagination = service.list_for_patient(patient_id=patient_id, page=page, page_size=page_size)
    return ApiResponse(success=True, message="", data=items, pagination=pagination)


@router.get("/reports/{report_id}", response_model=ApiResponse[MedicalReportRead])
async def get_report(
    report_id: int,
    service: MedicalReportService = Depends(get_medical_report_service),
) -> ApiResponse[MedicalReportRead]:
    """Return one medical report by identifier."""
    report = service.get(report_id)
    return ApiResponse(success=True, message="Medical report retrieved successfully.", data=report)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    service: MedicalReportService = Depends(get_medical_report_service),
) -> None:
    """Delete one medical report."""
    service.delete(report_id)
