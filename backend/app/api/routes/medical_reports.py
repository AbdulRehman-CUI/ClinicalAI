"""REST endpoints for medical report uploads and retrieval."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse

from app.schemas.common import ApiResponse
from app.schemas.medical_report import MedicalReportRead, ReportUploadCompletion, ReportUploadIntent, ReportUploadRequest
from app.services.medical_report import MedicalReportService, get_medical_report_service

router = APIRouter(prefix="/patients", tags=["medical-reports"])


@router.post("/{patient_id}/reports", response_model=ApiResponse[MedicalReportRead], status_code=status.HTTP_201_CREATED)
def upload_report(
    patient_id: int,
    file: UploadFile = File(...),
    service: MedicalReportService = Depends(get_medical_report_service),
) -> ApiResponse[MedicalReportRead]:
    """Upload and persist one medical report."""
    report = service.create(patient_id, file)
    return ApiResponse(success=True, message="Medical report uploaded successfully.", data=report)


@router.post("/{patient_id}/reports/upload-intent", response_model=ApiResponse[ReportUploadIntent])
def authorize_report_upload(
    patient_id: int,
    payload: ReportUploadRequest,
    service: MedicalReportService = Depends(get_medical_report_service),
) -> ApiResponse[ReportUploadIntent]:
    intent = service.authorize_upload(patient_id, payload)
    return ApiResponse(success=True, message="Report upload authorized.", data=intent)


@router.post(
    "/{patient_id}/reports/complete",
    response_model=ApiResponse[MedicalReportRead],
    status_code=status.HTTP_201_CREATED,
)
def complete_report_upload(
    patient_id: int,
    payload: ReportUploadCompletion,
    service: MedicalReportService = Depends(get_medical_report_service),
) -> ApiResponse[MedicalReportRead]:
    report = service.complete_upload(patient_id, payload.token)
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
def delete_report(
    report_id: int,
    service: MedicalReportService = Depends(get_medical_report_service),
) -> None:
    """Delete one medical report."""
    service.delete(report_id)


@router.get("/reports/{report_id}/download", response_model=None)
def download_report(
    report_id: int,
    service: MedicalReportService = Depends(get_medical_report_service),
) -> FileResponse | RedirectResponse:
    """Serve a local attachment or redirect to a short-lived private download."""
    download = service.download(report_id)
    headers = {"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"}
    if isinstance(download, Path):
        return FileResponse(download, media_type="application/octet-stream",
                            filename=f"report{download.suffix}", headers=headers)
    return RedirectResponse(download, status_code=status.HTTP_303_SEE_OTHER, headers=headers)
