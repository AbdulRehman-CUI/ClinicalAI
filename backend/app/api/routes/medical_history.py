"""REST endpoints for medical history management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, status

from app.schemas.common import ApiResponse
from app.schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryRead,
    MedicalHistoryUpdate,
)
from app.services.exceptions import ResourceNotFoundError
from app.services.medical_history import MedicalHistoryService, get_medical_history_service

router = APIRouter(prefix="/patients", tags=["medical-history"])


@router.post("/{patient_id}/medical-history", response_model=ApiResponse[MedicalHistoryRead], status_code=status.HTTP_201_CREATED)
async def create_medical_history(
    payload: MedicalHistoryCreate,
    patient_id: int = Path(..., ge=1),
    service: MedicalHistoryService = Depends(get_medical_history_service),
) -> ApiResponse[MedicalHistoryRead]:
    """Create one medical history record for a patient."""
    record = service.create(patient_id, payload)
    return ApiResponse(success=True, message="Medical history created successfully.", data=record)


@router.get("/{patient_id}/medical-history", response_model=ApiResponse[list[MedicalHistoryRead]])
async def list_medical_history(
    patient_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: MedicalHistoryService = Depends(get_medical_history_service),
) -> ApiResponse[list[MedicalHistoryRead]]:
    """Return medical history for one patient."""
    items, pagination = service.list_for_patient(patient_id=patient_id, page=page, page_size=page_size)
    return ApiResponse(success=True, message="", data=items, pagination=pagination)


@router.put("/medical-history/{history_id}", response_model=ApiResponse[MedicalHistoryRead])
async def update_medical_history(
    history_id: int,
    payload: MedicalHistoryUpdate,
    service: MedicalHistoryService = Depends(get_medical_history_service),
) -> ApiResponse[MedicalHistoryRead]:
    """Update one medical history record."""
    record = service.update(history_id, payload)
    return ApiResponse(success=True, message="Medical history updated successfully.", data=record)


@router.delete("/medical-history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_history(
    history_id: int,
    service: MedicalHistoryService = Depends(get_medical_history_service),
) -> None:
    """Delete one medical history record."""
    service.delete(history_id)
