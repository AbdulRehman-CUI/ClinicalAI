"""REST endpoints for patient management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.schemas.auth import AuthUser
from app.schemas.common import ApiResponse
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.services.patient import PatientService, get_patient_service
from app.services.exceptions import ResourceNotFoundError
from app.services.auth import get_current_user

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=ApiResponse[PatientRead], status_code=status.HTTP_201_CREATED)
async def create_patient(
    payload: PatientCreate,
    service: PatientService = Depends(get_patient_service),
    _current_user: AuthUser = Depends(get_current_user),
) -> ApiResponse[PatientRead]:
    """Create a new patient."""
    patient = service.create(payload)
    return ApiResponse(success=True, message="Patient created successfully.", data=patient)


@router.get("", response_model=ApiResponse[list[PatientRead]])
async def list_patients(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: PatientService = Depends(get_patient_service),
    _current_user: AuthUser = Depends(get_current_user),
) -> ApiResponse[list[PatientRead]]:
    """Return a paginated patient list."""
    items, pagination = service.list(page=page, page_size=page_size)
    return ApiResponse(success=True, message="", data=items, pagination=pagination)


@router.get("/{patient_id}", response_model=ApiResponse[PatientRead])
async def get_patient(
    patient_id: int,
    service: PatientService = Depends(get_patient_service),
    _current_user: AuthUser = Depends(get_current_user),
) -> ApiResponse[PatientRead]:
    """Return one patient by identifier."""
    patient = service.get(patient_id)
    return ApiResponse(success=True, message="Patient retrieved successfully.", data=patient)


@router.put("/{patient_id}", response_model=ApiResponse[PatientRead])
async def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    service: PatientService = Depends(get_patient_service),
    _current_user: AuthUser = Depends(get_current_user),
) -> ApiResponse[PatientRead]:
    """Update an existing patient."""
    patient = service.update(patient_id, payload)
    return ApiResponse(success=True, message="Patient updated successfully.", data=patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: int,
    service: PatientService = Depends(get_patient_service),
    _current_user: AuthUser = Depends(get_current_user),
) -> None:
    """Delete one patient."""
    service.delete(patient_id)
