"""Manage a guest workspace's LLM configuration."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.workspace import cookie_name, get_workspace, set_browser_cookie
from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.services.llm import (
    LLMSelection, LLMSave, LLMStatus, configuration_status, model_registry, remove_configuration,
    save_configuration, test_selection, list_configurations, activate_configuration, LLMDiscovery, discover_models,
)

router = APIRouter(prefix="/llm", tags=["llm"])
workspace = Depends(get_workspace)


@router.get("/providers", response_model=ApiResponse[dict[str, list[str]]])
def providers():
    return ApiResponse(success=True, message="", data=model_registry())


@router.get("/config", response_model=ApiResponse[LLMStatus], dependencies=[workspace])
def config(db: Session = Depends(get_db)):
    return ApiResponse(success=True, message="", data=configuration_status(db))


@router.put("/config", response_model=ApiResponse[LLMStatus], dependencies=[workspace])
def save(payload: LLMSave, response: Response, db: Session = Depends(get_db)):
    result, session_token = save_configuration(db, payload)
    if session_token is not None:
        set_browser_cookie(response, "llm-session", session_token)
    return ApiResponse(success=True, message="LLM configuration saved.", data=result)


@router.delete("/config", status_code=204, dependencies=[workspace])
def remove(response: Response, id: str | None = None, db: Session = Depends(get_db)) -> None:
    remove_configuration(db, id)


@router.post("/test", response_model=ApiResponse[dict[str, bool]], dependencies=[workspace])
def test(payload: LLMSelection, db: Session = Depends(get_db)):
    test_selection(db, payload)
    return ApiResponse(success=True, message="The provider accepted the model request.", data={"tested": True})


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        cookie_name("llm-session"), path="/", httponly=True,
        secure=get_settings().is_production, samesite="lax",
    )


@router.get("/configs", dependencies=[workspace])
def configs(db: Session = Depends(get_db)):
    return ApiResponse(success=True, message="", data=list_configurations(db))


@router.post("/configs/{identifier}/activate", dependencies=[workspace])
def activate(identifier: str, db: Session = Depends(get_db)):
    return ApiResponse(success=True, message="Active configuration selected.", data=activate_configuration(db, identifier))


@router.post("/models", dependencies=[workspace])
def models(payload: LLMDiscovery, db: Session = Depends(get_db)):
    return ApiResponse(success=True, message="Discovered models; connection testing is still required.", data={"source": "discovered", "models": discover_models(db, payload)})

@router.get("/metadata")
def metadata():
    names = {"openrouter": "OpenRouter", "gemini": "Google Gemini", "openai": "OpenAI",
             "anthropic": "Anthropic", "groq": "Groq", "custom": "Custom endpoint"}
    return ApiResponse(success=True, message="Catalogs are fallback suggestions, not account access guarantees.", data=[
        {"id": key, "name": name, "protocol": "responses" if key == "openai" else "generateContent" if key == "gemini" else "messages" if key == "anthropic" else "chat-completions",
         "discovery": "credential-dependent", "catalog_source": "fallback", "models": model_registry()[key]}
        for key, name in names.items()])
