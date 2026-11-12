"""Browser-issued capabilities for isolated anonymous workspaces."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import logging
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import GuestWorkspace
from app.db.session import get_db

WORKSPACE_TTL = timedelta(days=30)
router = APIRouter(tags=["workspace"])
logger = logging.getLogger(__name__)


def cookie_name(name: str) -> str:
    prefix = "__Host-" if get_settings().is_production else ""
    return f"{prefix}clinicalai-{name}"


def set_browser_cookie(response: Response, name: str, value: str, max_age: int | None = None) -> None:
    response.set_cookie(
        cookie_name(name), value, max_age=max_age, path="/",
        httponly=True, secure=get_settings().is_production, samesite="lax",
    )


def capability_hash(credential: str | None) -> str | None:
    if credential and len(credential) == 43 and credential.isascii():
        return sha256(credential.encode()).hexdigest()
    return None


def require_browser_write(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    settings = get_settings()
    if (
        request.headers.get("x-clinicalai-request") != "1"
        or request.headers.get("origin") not in settings.effective_allowed_cors_origins
    ):
        raise HTTPException(403, "Workspace changes require an approved browser origin.")


def find_workspace(request: Request, db: Session) -> GuestWorkspace | None:
    digest = capability_hash(request.cookies.get(cookie_name("workspace")))
    if digest is None:
        return None
    return db.scalar(select(GuestWorkspace).where(
        GuestWorkspace.credential_hash == digest,
        GuestWorkspace.expires_at > datetime.now(timezone.utc),
    ))


def get_workspace(
    request: Request,
    db: Session = Depends(get_db),
    _csrf: None = Depends(require_browser_write),
) -> str:
    workspace = find_workspace(request, db)
    if workspace is None:
        raise HTTPException(401, "Workspace unavailable or expired. Retry workspace setup or reload the page.")
    db.info["workspace_id"] = workspace.id
    db.info["llm_session_hash"] = capability_hash(request.cookies.get(cookie_name("llm-session")))
    return workspace.id


@router.post("/workspace", status_code=204, dependencies=[Depends(require_browser_write)])
def initialize_workspace(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    if find_workspace(request, db) is not None:
        logger.info("Guest workspace restored")
        return
    credential = token_urlsafe(32)
    db.add(GuestWorkspace(
        id=uuid4().hex, credential_hash=capability_hash(credential),
        expires_at=datetime.now(timezone.utc) + WORKSPACE_TTL,
    ))
    db.commit()
    set_browser_cookie(response, "workspace", credential, int(WORKSPACE_TTL.total_seconds()))
    logger.info("Guest workspace created")
