"""REST endpoints for AI analysis records."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.common import ApiResponse
from app.services.ai_analysis import AIAnalysisService, get_ai_analysis_service
from app.services.analysis import AnalysisService, get_analysis_service

router = APIRouter(prefix="/patients", tags=["ai-analysis"])


@router.post("/{patient_id}/analysis", response_model=ApiResponse[AIAnalysisRead], status_code=status.HTTP_201_CREATED)
async def create_analysis(
    patient_id: int,
    report_id: int | None = None,
    service: AIAnalysisService = Depends(get_ai_analysis_service),
) -> ApiResponse[AIAnalysisRead]:
    """Create a placeholder AI analysis record for a patient."""
    analysis = service.create(patient_id, report_id=report_id)
    return ApiResponse(success=True, message="AI analysis created successfully.", data=analysis)


@router.post("/{patient_id}/analyze", response_model=ApiResponse[dict[str, Any]], status_code=status.HTTP_200_OK)
def analyze_patient(
    patient_id: int,
    service: AnalysisService = Depends(get_analysis_service),
) -> ApiResponse[dict[str, Any]]:
    """Run the end-to-end AI workflow for a patient and persist the result."""
    result = service.analyze_patient(patient_id)
    return ApiResponse(success=True, message="AI analysis completed successfully.", data=result)


@router.get("/{patient_id}/analysis", response_model=ApiResponse[list[AIAnalysisRead]])
async def list_analyses(
    patient_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    service: AIAnalysisService = Depends(get_ai_analysis_service),
) -> ApiResponse[list[AIAnalysisRead]]:
    """Return analyses for one patient."""
    items, pagination = service.list_for_patient(patient_id=patient_id, page=page, page_size=page_size)
    return ApiResponse(success=True, message="", data=items, pagination=pagination)


@router.get("/analysis/{analysis_id}", response_model=ApiResponse[AIAnalysisRead])
async def get_analysis(
    analysis_id: int,
    service: AIAnalysisService = Depends(get_ai_analysis_service),
) -> ApiResponse[AIAnalysisRead]:
    """Return one stored AI analysis record."""
    analysis = service.get(analysis_id)
    return ApiResponse(success=True, message="AI analysis retrieved successfully.", data=analysis)
