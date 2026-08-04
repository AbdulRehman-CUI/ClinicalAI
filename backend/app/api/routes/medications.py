"""REST endpoints for medication management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, status

from app.schemas.common import ApiResponse
from app.schemas.medication import MedicationCreate, MedicationRead, MedicationUpdate
from app.services.medication import MedicationService, get_medication_service

router = APIRouter(prefix="/patients", tags=["medications"])


@router.post("/{patient_id}/medications", response_model=ApiResponse[MedicationRead], status_code=status.HTTP_201_CREATED)
async def create_medication(
    payload: MedicationCreate,
    patient_id: int = Path(..., ge=1),
    service: MedicationService = Depends(get_medication_service),
) -> ApiResponse[MedicationRead]:
    """Create one medication record for a patient."""
    record = service.create(patient_id, payload)
    return ApiResponse(success=True, message="Medication created successfully.", data=record)


@router.get("/{patient_id}/medications", response_model=ApiResponse[list[MedicationRead]])
async def list_medications(
    patient_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: MedicationService = Depends(get_medication_service),
) -> ApiResponse[list[MedicationRead]]:
    """Return medications for one patient."""
    items, pagination = service.list_for_patient(patient_id=patient_id, page=page, page_size=page_size)
    return ApiResponse(success=True, message="", data=items, pagination=pagination)


@router.put("/medications/{medication_id}", response_model=ApiResponse[MedicationRead])
async def update_medication(
    medication_id: int,
    payload: MedicationUpdate,
    service: MedicationService = Depends(get_medication_service),
) -> ApiResponse[MedicationRead]:
    """Update one medication record."""
    record = service.update(medication_id, payload)
    return ApiResponse(success=True, message="Medication updated successfully.", data=record)


@router.delete("/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: int,
    service: MedicationService = Depends(get_medication_service),
) -> None:
    """Delete one medication record."""
    service.delete(medication_id)
