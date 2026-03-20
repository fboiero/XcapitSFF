"""API endpoints for API key management."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.api_keys import get_default_manager

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateKeyRequest(BaseModel):
    tenant_id: str
    name: str
    scopes: list[str] | None = None
    expires_at: str | None = None  # ISO-8601


class CreateKeyResponse(BaseModel):
    key: str  # raw key — shown only once
    key_id: str
    name: str
    scopes: list[str]
    created_at: str
    expires_at: str | None = None


class KeyListItem(BaseModel):
    key_id: str
    name: str
    key_hint: str
    scopes: list[str]
    created_at: str
    last_used_at: str | None = None
    expires_at: str | None = None
    revoked: bool


class RotateKeyResponse(BaseModel):
    new_key: str  # raw key — shown only once
    key_id: str
    name: str
    scopes: list[str]
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=CreateKeyResponse)
async def create_api_key(request: CreateKeyRequest):
    """Create a new API key. The raw key is returned **only once**."""
    manager = get_default_manager()

    expires = None
    if request.expires_at:
        try:
            expires = datetime.fromisoformat(request.expires_at)
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at format")

    try:
        raw_key, meta = manager.create_key(
            tenant_id=request.tenant_id,
            name=request.name,
            scopes=request.scopes,
            expires_at=expires,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CreateKeyResponse(
        key=raw_key,
        key_id=meta.key_id,
        name=meta.name,
        scopes=meta.scopes,
        created_at=meta.created_at.isoformat(),
        expires_at=meta.expires_at.isoformat() if meta.expires_at else None,
    )


@router.get("/", response_model=list[KeyListItem])
async def list_api_keys(tenant_id: str = Query(...)):
    """List all API keys for a tenant (masked — no raw keys returned)."""
    manager = get_default_manager()
    keys = manager.list_keys(tenant_id)
    return [KeyListItem(**k) for k in keys]


@router.delete("/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key."""
    manager = get_default_manager()
    try:
        meta = manager.revoke_key(key_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"key_id": meta.key_id, "revoked": True}


@router.post("/{key_id}/rotate", response_model=RotateKeyResponse)
async def rotate_api_key(key_id: str):
    """Rotate an API key: revoke the old one and issue a new one."""
    manager = get_default_manager()
    try:
        raw_key, meta = manager.rotate_key(key_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return RotateKeyResponse(
        new_key=raw_key,
        key_id=meta.key_id,
        name=meta.name,
        scopes=meta.scopes,
        created_at=meta.created_at.isoformat(),
    )
