"""API endpoints for billing, pricing, subscriptions, and usage metering."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.billing import (
    BillingManager,
    PricingPlan,
    UsageMeter,
    PLANS,
)

router = APIRouter(prefix="/billing", tags=["Billing"])

# ---------------------------------------------------------------------------
# Shared instances (in production these would be injected via DI / Depends)
# ---------------------------------------------------------------------------

_usage_meter = UsageMeter()
_billing_manager = BillingManager(usage_meter=_usage_meter)


def get_billing_manager() -> BillingManager:
    return _billing_manager


def get_usage_meter() -> UsageMeter:
    return _usage_meter


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SubscribeRequest(BaseModel):
    tenant_id: str
    plan_id: str
    trial_days: int = 14


class CancelRequest(BaseModel):
    tenant_id: str


class UsageRequest(BaseModel):
    tenant_id: str
    period: str | None = None


class FeatureCheckRequest(BaseModel):
    tenant_id: str


class PlanResponse(BaseModel):
    plan_id: str
    name: str
    price_monthly_usd: float
    price_annual_usd: float
    features: list[str]
    limits: dict[str, int | float]


class SubscriptionResponse(BaseModel):
    subscription_id: str
    tenant_id: str
    plan_id: str
    status: str
    started_at: str
    trial_ends_at: str | None = None
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sub_to_response(sub) -> SubscriptionResponse:
    return SubscriptionResponse(
        subscription_id=sub.subscription_id,
        tenant_id=sub.tenant_id,
        plan_id=sub.plan_id,
        status=sub.status,
        started_at=sub.started_at.isoformat(),
        trial_ends_at=sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        current_period_start=(
            sub.current_period_start.isoformat() if sub.current_period_start else None
        ),
        current_period_end=(
            sub.current_period_end.isoformat() if sub.current_period_end else None
        ),
        cancel_at=sub.cancel_at.isoformat() if sub.cancel_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans():
    """List all available pricing plans."""
    plans = BillingManager.get_all_plans()
    return [
        PlanResponse(
            plan_id=p.plan_id,
            name=p.name,
            price_monthly_usd=p.price_monthly_usd,
            price_annual_usd=p.price_annual_usd,
            features=p.features,
            limits=p.limits,
        )
        for p in plans
    ]


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(tenant_id: str):
    """Get the current subscription for a tenant."""
    bm = get_billing_manager()
    sub = bm.get_subscription(tenant_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription found")
    return _sub_to_response(sub)


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe(request: SubscribeRequest):
    """Create or change a subscription."""
    bm = get_billing_manager()
    existing = bm.get_subscription(request.tenant_id)

    try:
        if existing is None:
            sub = bm.create_subscription(
                request.tenant_id, request.plan_id, request.trial_days
            )
        else:
            from xcapitsff.core.billing import _PLAN_TIER_ORDER

            current_tier = _PLAN_TIER_ORDER.get(existing.plan_id, 0)
            new_tier = _PLAN_TIER_ORDER.get(request.plan_id, 0)
            if new_tier > current_tier:
                sub = bm.upgrade_plan(request.tenant_id, request.plan_id)
            elif new_tier < current_tier:
                sub = bm.downgrade_plan(request.tenant_id, request.plan_id)
            else:
                sub = existing  # same plan, no-op
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _sub_to_response(sub)


@router.post("/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(request: CancelRequest):
    """Cancel a subscription."""
    bm = get_billing_manager()
    try:
        sub = bm.cancel_subscription(request.tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _sub_to_response(sub)


@router.get("/usage")
async def get_usage(tenant_id: str, period: str | None = None):
    """Get current usage and quotas for a tenant."""
    bm = get_billing_manager()
    um = get_usage_meter()

    sub = bm.get_subscription(tenant_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription found")

    plan = PLANS.get(sub.plan_id)
    usage = um.get_usage(tenant_id, period)

    quotas = {}
    for metric, used in usage.items():
        limit_key = metric
        if metric == "leads_created":
            limit_key = "leads"
        elif metric == "tickets_created":
            limit_key = "tickets"
        limit = plan.limits.get(limit_key, -1) if plan else -1
        quotas[metric] = {
            "used": used,
            "limit": limit,
            "within_limit": (limit == -1) or (used < limit),
        }

    return {
        "tenant_id": tenant_id,
        "plan_id": sub.plan_id,
        "period": period or um._period_key(),
        "usage": usage,
        "quotas": quotas,
    }


@router.get("/invoice-preview")
async def invoice_preview(tenant_id: str):
    """Preview next invoice."""
    bm = get_billing_manager()
    try:
        preview = bm.get_invoice_preview(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return preview


@router.get("/features")
async def list_features(tenant_id: str):
    """List features available on the tenant's current plan."""
    bm = get_billing_manager()
    sub = bm.get_subscription(tenant_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="No subscription found")

    plan = PLANS.get(sub.plan_id)
    if plan is None:
        raise HTTPException(status_code=400, detail="Unknown plan")

    return {
        "tenant_id": tenant_id,
        "plan_id": sub.plan_id,
        "features": plan.features,
    }
