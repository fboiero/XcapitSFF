"""API endpoints for tenant management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any

from xcapitsff.core.tenancy import TenantManager, tenant_manager
from .auth_api import get_current_user, require_admin

router = APIRouter(tags=["Tenant"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    slug: str
    plan: str
    is_active: bool
    created_at: str
    owner_email: str
    max_leads: int
    max_tickets: int
    max_users: int
    api_calls_limit_monthly: int
    settings: dict[str, Any] = {}


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    settings: dict[str, Any] | None = None


class UsageResponse(BaseModel):
    tenant_id: str
    plan: str
    leads: dict[str, int]
    tickets: dict[str, int]
    users: dict[str, int]
    api_calls: dict[str, int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tenant_response(tenant) -> TenantResponse:
    return TenantResponse(
        tenant_id=tenant.tenant_id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan.value,
        is_active=tenant.is_active,
        created_at=tenant.created_at.isoformat(),
        owner_email=tenant.owner_email,
        max_leads=tenant.max_leads,
        max_tickets=tenant.max_tickets,
        max_users=tenant.max_users,
        api_calls_limit_monthly=tenant.api_calls_limit_monthly,
        settings=tenant.settings,
    )


# ---------------------------------------------------------------------------
# Tenant endpoints (scoped to current user's tenant)
# ---------------------------------------------------------------------------

@router.get("/tenant", response_model=TenantResponse)
async def api_get_tenant(
    current_user: dict = Depends(get_current_user),
    _tm: TenantManager = Depends(lambda: tenant_manager),
):
    tenant = _tm.get_tenant(current_user["tenant_id"])
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return _tenant_response(tenant)


@router.patch("/tenant", response_model=TenantResponse)
async def api_update_tenant(
    data: TenantUpdateRequest,
    current_user: dict = Depends(require_admin),
    _tm: TenantManager = Depends(lambda: tenant_manager),
):
    """Update tenant settings (admin only)."""
    updates: dict[str, Any] = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.settings is not None:
        updates["settings"] = data.settings

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        tenant = _tm.update_tenant(current_user["tenant_id"], **updates)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _tenant_response(tenant)


@router.get("/tenant/usage", response_model=UsageResponse)
async def api_tenant_usage(
    current_user: dict = Depends(get_current_user),
    _tm: TenantManager = Depends(lambda: tenant_manager),
):
    usage = _tm.get_usage(current_user["tenant_id"])
    if not usage:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return usage


# ---------------------------------------------------------------------------
# Super-admin endpoint
# ---------------------------------------------------------------------------

@router.get("/admin/tenants", response_model=list[TenantResponse])
async def api_list_tenants(
    plan: str | None = None,
    active_only: bool = True,
    current_user: dict = Depends(require_admin),
    _tm: TenantManager = Depends(lambda: tenant_manager),
):
    """List all tenants (super-admin only)."""
    tenants = _tm.list_tenants(plan=plan, active_only=active_only)
    return [_tenant_response(t) for t in tenants]
