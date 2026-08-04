"""REST endpoints for allergy management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, status

from app.schemas.allergy import AllergyCreate, AllergyRead, AllergyUpdate
from app.schemas.common import ApiResponse
from app.services.allergy import AllergyService, get_allergy_service

router = APIRouter(prefix="/patients", tags=["allergies"])


@router.post("/{patient_id}/allergies", response_model=ApiResponse[AllergyRead], status_code=status.HTTP_201_CREATED)
async def create_allergy(
    payload: AllergyCreate,
    patient_id: int = Path(..., ge=1),
    service: AllergyService = Depends(get_allergy_service),
) -> ApiResponse[AllergyRead]:
    """Create one allergy record for a patient."""
    record = service.create(patient_id, payload)
    return ApiResponse(success=True, message="Allergy created successfully.", data=record)


@router.get("/{patient_id}/allergies", response_model=ApiResponse[list[AllergyRead]])
async def list_allergies(
    patient_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: AllergyService = Depends(get_allergy_service),
) -> ApiResponse[list[AllergyRead]]:
    """Return allergies for one patient."""
    items, pagination = service.list_for_patient(patient_id=patient_id, page=page, page_size=page_size)
    return ApiResponse(success=True, message="", data=items, pagination=pagination)


@router.put("/allergies/{allergy_id}", response_model=ApiResponse[AllergyRead])
async def update_allergy(
    allergy_id: int,
    payload: AllergyUpdate,
    service: AllergyService = Depends(get_allergy_service),
) -> ApiResponse[AllergyRead]:
    """Update one allergy record."""
    record = service.update(allergy_id, payload)
    return ApiResponse(success=True, message="Allergy updated successfully.", data=record)


@router.delete("/allergies/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_allergy(
    allergy_id: int,
    service: AllergyService = Depends(get_allergy_service),
) -> None:
    """Delete one allergy record."""
    service.delete(allergy_id)
