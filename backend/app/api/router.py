"""Top-level API router for versioned REST endpoints."""

from fastapi import APIRouter, Depends

from app.api.routes import ai_analysis, allergies, health, llm, medical_history, medical_reports, medications, patients, symptoms
from app.api.workspace import get_workspace, router as workspace_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(workspace_router)
api_router.include_router(llm.router)
for clinical_router in (patients, medical_history, medications, allergies, symptoms, medical_reports, ai_analysis):
    api_router.include_router(clinical_router.router, dependencies=[Depends(get_workspace)])

