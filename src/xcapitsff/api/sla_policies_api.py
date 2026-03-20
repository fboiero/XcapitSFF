"""API endpoints for configurable SLA policy management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.sla_policies import (
    SLAPriority,
    SLATarget,
    sla_policy_manager,
)

router = APIRouter(prefix="/sla-policies", tags=["SLA Policies"])


# --- Request / Response schemas ---


class SLATargetSchema(BaseModel):
    first_response_minutes: int
    resolution_minutes: int
    update_frequency_minutes: int


class BusinessHoursSchema(BaseModel):
    start_hour: int = 9
    end_hour: int = 17
    timezone: str = "UTC"
    working_days: list[int] = [0, 1, 2, 3, 4]


class CreatePolicyRequest(BaseModel):
    tenant_id: str
    name: str
    description: str = ""
    priority: SLAPriority
    targets: SLATargetSchema
    business_hours_only: bool = False
    business_hours: BusinessHoursSchema | None = None


class UpdatePolicyRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    priority: SLAPriority | None = None
    targets: SLATargetSchema | None = None
    business_hours_only: bool | None = None
    business_hours: BusinessHoursSchema | None = None
    active: bool | None = None


# --- Endpoints ---


@router.post("/")
async def create_policy(req: CreatePolicyRequest):
    """Create a new SLA policy."""
    bh = req.business_hours.model_dump() if req.business_hours else None
    policy = sla_policy_manager.create_policy(
        tenant_id=req.tenant_id,
        name=req.name,
        description=req.description,
        priority=req.priority,
        targets=SLATarget(
            first_response_minutes=req.targets.first_response_minutes,
            resolution_minutes=req.targets.resolution_minutes,
            update_frequency_minutes=req.targets.update_frequency_minutes,
        ),
        business_hours_only=req.business_hours_only,
        business_hours=bh,
    )
    return _policy_to_dict(policy)


@router.get("/")
async def list_policies(tenant_id: str = Query(...)):
    """List all SLA policies for a tenant."""
    policies = sla_policy_manager.list_policies(tenant_id)
    return {
        "count": len(policies),
        "policies": [_policy_to_dict(p) for p in policies],
    }


@router.put("/{policy_id}")
async def update_policy(policy_id: str, req: UpdatePolicyRequest):
    """Update an existing SLA policy."""
    kwargs: dict = {}
    if req.name is not None:
        kwargs["name"] = req.name
    if req.description is not None:
        kwargs["description"] = req.description
    if req.priority is not None:
        kwargs["priority"] = req.priority
    if req.targets is not None:
        kwargs["targets"] = SLATarget(
            first_response_minutes=req.targets.first_response_minutes,
            resolution_minutes=req.targets.resolution_minutes,
            update_frequency_minutes=req.targets.update_frequency_minutes,
        )
    if req.business_hours_only is not None:
        kwargs["business_hours_only"] = req.business_hours_only
    if req.business_hours is not None:
        kwargs["business_hours"] = req.business_hours.model_dump()
    if req.active is not None:
        kwargs["active"] = req.active

    try:
        policy = sla_policy_manager.update_policy(policy_id, **kwargs)
    except ValueError:
        raise HTTPException(status_code=404, detail="Policy not found")
    return _policy_to_dict(policy)


@router.delete("/{policy_id}")
async def delete_policy(policy_id: str):
    """Delete an SLA policy."""
    deleted = sla_policy_manager.delete_policy(policy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"deleted": True, "policy_id": policy_id}


@router.post("/defaults")
async def setup_defaults(tenant_id: str = Query(...)):
    """Create the four default SLA policies for a tenant."""
    policies = sla_policy_manager.setup_defaults(tenant_id)
    return {
        "count": len(policies),
        "policies": [_policy_to_dict(p) for p in policies],
    }


@router.get("/compliance")
async def get_compliance(
    tenant_id: str = Query(...),
    days: int = Query(default=30, ge=1, le=365),
):
    """Get SLA compliance report for a tenant."""
    return sla_policy_manager.get_sla_compliance(tenant_id, days)


@router.get("/breaches")
async def get_breaches(
    tenant_id: str = Query(...),
    days: int = Query(default=30, ge=1, le=365),
):
    """List SLA breaches for a tenant."""
    breaches = sla_policy_manager.get_breaches(tenant_id, days)
    return {
        "count": len(breaches),
        "breaches": [
            {
                "id": b.id,
                "tenant_id": b.tenant_id,
                "ticket_id": b.ticket_id,
                "policy_id": b.policy_id,
                "breach_type": b.breach_type,
                "breached_at": b.breached_at.isoformat(),
                "target_minutes": b.target_minutes,
                "actual_minutes": b.actual_minutes,
                "escalated": b.escalated,
            }
            for b in breaches
        ],
    }


@router.get("/status/{ticket_id}")
async def get_sla_status(
    ticket_id: str,
    policy_id: str = Query(...),
    created_at: str = Query(..., description="Ticket creation time (ISO format)"),
    first_response_at: str | None = Query(default=None),
    resolved_at: str | None = Query(default=None),
    last_update_at: str | None = Query(default=None),
):
    """Get SLA status for a specific ticket."""
    from datetime import datetime

    try:
        created = datetime.fromisoformat(created_at)
        first_resp = (
            datetime.fromisoformat(first_response_at) if first_response_at else None
        )
        resolved = datetime.fromisoformat(resolved_at) if resolved_at else None
        last_upd = datetime.fromisoformat(last_update_at) if last_update_at else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {exc}")

    try:
        status = sla_policy_manager.calculate_sla_status(
            ticket_id=ticket_id,
            policy_id=policy_id,
            created_at=created,
            first_response_at=first_resp,
            resolved_at=resolved,
            last_update_at=last_upd,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Policy not found")

    return {
        "ticket_id": status.ticket_id,
        "policy_id": status.policy_id,
        "first_response_due": status.first_response_due.isoformat(),
        "first_response_met": status.first_response_met,
        "resolution_due": status.resolution_due.isoformat(),
        "resolution_met": status.resolution_met,
        "next_update_due": (
            status.next_update_due.isoformat() if status.next_update_due else None
        ),
        "breaches": [
            {
                "id": b.id,
                "breach_type": b.breach_type,
                "target_minutes": b.target_minutes,
                "actual_minutes": b.actual_minutes,
            }
            for b in status.breaches
        ],
        "is_within_sla": status.is_within_sla,
        "time_remaining_minutes": status.time_remaining_minutes,
    }


# --- Helpers ---


def _policy_to_dict(policy) -> dict:
    return {
        "id": policy.id,
        "tenant_id": policy.tenant_id,
        "name": policy.name,
        "description": policy.description,
        "priority": policy.priority.value,
        "targets": {
            "first_response_minutes": policy.targets.first_response_minutes,
            "resolution_minutes": policy.targets.resolution_minutes,
            "update_frequency_minutes": policy.targets.update_frequency_minutes,
        },
        "business_hours_only": policy.business_hours_only,
        "business_hours": policy.business_hours,
        "active": policy.active,
        "created_at": policy.created_at.isoformat(),
    }
