"""Top-level API router for versioned REST endpoints."""

from fastapi import APIRouter

from app.api.routes import ai_analysis, allergies, auth, health, medical_history, medical_reports, medications, patients, symptoms

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(patients.router)
api_router.include_router(medical_history.router)
api_router.include_router(medications.router)
api_router.include_router(allergies.router)
api_router.include_router(symptoms.router)
api_router.include_router(medical_reports.router)
api_router.include_router(ai_analysis.router)

