"""REST endpoints for symptom management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, status

from app.schemas.common import ApiResponse
from app.schemas.symptom import SymptomCreate, SymptomRead, SymptomUpdate
from app.services.symptom import SymptomService, get_symptom_service

router = APIRouter(prefix="/patients", tags=["symptoms"])


@router.post("/{patient_id}/symptoms", response_model=ApiResponse[SymptomRead], status_code=status.HTTP_201_CREATED)
async def create_symptom(
    payload: SymptomCreate,
    patient_id: int = Path(..., ge=1),
    service: SymptomService = Depends(get_symptom_service),
) -> ApiResponse[SymptomRead]:
    """Create one symptom record for a patient."""
    record = service.create(patient_id, payload)
    return ApiResponse(success=True, message="Symptom created successfully.", data=record)


@router.get("/{patient_id}/symptoms", response_model=ApiResponse[list[SymptomRead]])
async def list_symptoms(
    patient_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: SymptomService = Depends(get_symptom_service),
) -> ApiResponse[list[SymptomRead]]:
    """Return symptoms for one patient."""
    items, pagination = service.list_for_patient(patient_id=patient_id, page=page, page_size=page_size)
    return ApiResponse(success=True, message="", data=items, pagination=pagination)


@router.put("/symptoms/{symptom_id}", response_model=ApiResponse[SymptomRead])
async def update_symptom(
    symptom_id: int,
    payload: SymptomUpdate,
    service: SymptomService = Depends(get_symptom_service),
) -> ApiResponse[SymptomRead]:
    """Update one symptom record."""
    record = service.update(symptom_id, payload)
    return ApiResponse(success=True, message="Symptom updated successfully.", data=record)


@router.delete("/symptoms/{symptom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_symptom(
    symptom_id: int,
    service: SymptomService = Depends(get_symptom_service),
) -> None:
    """Delete one symptom record."""
    service.delete(symptom_id)
