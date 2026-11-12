from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from uuid import uuid4

from app.api.workspace import capability_hash
from app.db.models import GuestWorkspace

WORKSPACE_HEADERS = {"Origin": "http://localhost:5173", "X-ClinicalAI-Request": "1"}


def start_workspace(client):
    client.headers.update(WORKSPACE_HEADERS)
    response = client.post("/api/v1/workspace")
    assert response.status_code == 204, response.text
    return WORKSPACE_HEADERS


def seed_workspace(db):
    owner = uuid4().hex
    db.add(GuestWorkspace(
        id=owner, credential_hash=capability_hash(token_urlsafe(32)),
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    ))
    db.commit()
    db.info["workspace_id"] = owner
    return owner
