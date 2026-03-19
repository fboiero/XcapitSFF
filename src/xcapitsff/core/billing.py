"""Billing, pricing plans, subscription management, and usage metering."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Pricing Plans
# ---------------------------------------------------------------------------


@dataclass
class PricingPlan:
    """Describes a pricing tier."""

    plan_id: str  # "free", "pro", "enterprise"
    name: str
    price_monthly_usd: float
    price_annual_usd: float
    features: list[str]
    limits: dict[str, int | float]  # metric -> max value (-1 = unlimited)


FREE_PLAN = PricingPlan(
    plan_id="free",
    name="Free",
    price_monthly_usd=0.0,
    price_annual_usd=0.0,
    features=[
        "basic_scoring",
        "email_support",
    ],
    limits={
        "leads": 100,
        "tickets": 50,
        "users": 2,
        "api_calls": 1_000,
        "outreach_sent": 0,
        "agent_calls": 0,
        "exports": 5,
    },
)

PRO_PLAN = PricingPlan(
    plan_id="pro",
    name="Pro",
    price_monthly_usd=99.0,
    price_annual_usd=79.0,
    features=[
        "basic_scoring",
        "advanced_scoring",
        "outreach_sequences",
        "ab_testing",
        "priority_support",
        "crm_integration",
        "email_support",
    ],
    limits={
        "leads": 5_000,
        "tickets": 500,
        "users": 10,
        "api_calls": 50_000,
        "outreach_sent": 5_000,
        "agent_calls": 1_000,
        "exports": 100,
    },
)

ENTERPRISE_PLAN = PricingPlan(
    plan_id="enterprise",
    name="Enterprise",
    price_monthly_usd=499.0,
    price_annual_usd=399.0,
    features=[
        "basic_scoring",
        "advanced_scoring",
        "custom_scoring",
        "outreach_sequences",
        "ab_testing",
        "priority_support",
        "crm_integration",
        "email_support",
        "dedicated_agent",
        "sla_guarantee",
        "compliance_reports",
        "white_label",
        "api_priority",
    ],
    limits={
        "leads": -1,
        "tickets": -1,
        "users": -1,
        "api_calls": -1,
        "outreach_sent": -1,
        "agent_calls": -1,
        "exports": -1,
    },
)

PLANS: dict[str, PricingPlan] = {
    "free": FREE_PLAN,
    "pro": PRO_PLAN,
    "enterprise": ENTERPRISE_PLAN,
}

# Ordered tiers for upgrade / downgrade comparison
_PLAN_TIER_ORDER = {"free": 0, "pro": 1, "enterprise": 2}


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


@dataclass
class Subscription:
    """Represents a tenant's billing subscription."""

    subscription_id: str
    tenant_id: str
    plan_id: str
    status: str  # active | trial | past_due | cancelled
    started_at: datetime
    trial_ends_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at: datetime | None = None


# ---------------------------------------------------------------------------
# Usage Metering
# ---------------------------------------------------------------------------

TRACKED_METRICS = [
    "api_calls",
    "leads_created",
    "tickets_created",
    "outreach_sent",
    "agent_calls",
    "exports",
]


class UsageMeter:
    """In-memory usage metering (replace with Redis / DB in production)."""

    def __init__(self) -> None:
        # tenant_id -> period_key -> metric -> count
        self._usage: dict[str, dict[str, dict[str, int]]] = {}

    @staticmethod
    def _period_key(dt: datetime | None = None) -> str:
        dt = dt or datetime.now(timezone.utc)
        return dt.strftime("%Y-%m")

    def record_usage(
        self,
        tenant_id: str,
        metric: str,
        amount: int = 1,
    ) -> None:
        """Increment a usage counter for the current billing period."""
        if metric not in TRACKED_METRICS:
            raise ValueError(f"Unknown metric: {metric}")
        period = self._period_key()
        self._usage.setdefault(tenant_id, {}).setdefault(period, {})
        bucket = self._usage[tenant_id][period]
        bucket[metric] = bucket.get(metric, 0) + amount

    def get_usage(
        self,
        tenant_id: str,
        period: str | None = None,
    ) -> dict[str, int]:
        """Return usage counters for the given (or current) period."""
        period = period or self._period_key()
        tenant_data = self._usage.get(tenant_id, {})
        raw = tenant_data.get(period, {})
        return {m: raw.get(m, 0) for m in TRACKED_METRICS}

    def check_quota(
        self,
        tenant_id: str,
        metric: str,
        plan: PricingPlan | None = None,
    ) -> tuple[bool, int, int]:
        """Check whether a tenant is within quota for *metric*.

        Returns ``(within_limit, used, limit)``.
        A limit of ``-1`` means unlimited.
        """
        usage = self.get_usage(tenant_id)
        used = usage.get(metric, 0)

        if plan is None:
            # Without a plan we cannot determine the limit — assume unlimited
            return (True, used, -1)

        # Map leads_created -> leads, tickets_created -> tickets for limit lookup
        limit_key = metric
        if metric == "leads_created":
            limit_key = "leads"
        elif metric == "tickets_created":
            limit_key = "tickets"

        limit = plan.limits.get(limit_key, -1)
        if limit == -1:
            return (True, used, -1)
        return (used < limit, used, limit)

    def reset_monthly_usage(self, tenant_id: str) -> None:
        """Reset counters for the current billing period."""
        period = self._period_key()
        if tenant_id in self._usage:
            self._usage[tenant_id][period] = {m: 0 for m in TRACKED_METRICS}


# ---------------------------------------------------------------------------
# Billing Manager
# ---------------------------------------------------------------------------


class BillingManager:
    """Manages subscriptions and billing operations."""

    def __init__(self, usage_meter: UsageMeter | None = None) -> None:
        self._subscriptions: dict[str, Subscription] = {}
        self.usage_meter = usage_meter or UsageMeter()

    # -- helpers --

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:16]

    @staticmethod
    def get_all_plans() -> list[PricingPlan]:
        """Return all available pricing plans."""
        return [PLANS[k] for k in ("free", "pro", "enterprise")]

    def _get_plan(self, plan_id: str) -> PricingPlan:
        plan = PLANS.get(plan_id)
        if plan is None:
            raise ValueError(f"Unknown plan: {plan_id}")
        return plan

    # -- subscription lifecycle --

    def create_subscription(
        self,
        tenant_id: str,
        plan_id: str,
        trial_days: int = 14,
    ) -> Subscription:
        """Create a new subscription (with optional trial)."""
        self._get_plan(plan_id)  # validate plan exists
        now = self._now()
        trial_end = now + timedelta(days=trial_days) if trial_days > 0 else None
        status = "trial" if trial_days > 0 else "active"
        period_end = now + timedelta(days=30)

        sub = Subscription(
            subscription_id=self._new_id(),
            tenant_id=tenant_id,
            plan_id=plan_id,
            status=status,
            started_at=now,
            trial_ends_at=trial_end,
            current_period_start=now,
            current_period_end=period_end,
        )
        self._subscriptions[tenant_id] = sub
        return sub

    def get_subscription(self, tenant_id: str) -> Subscription | None:
        """Return the current subscription or ``None``."""
        return self._subscriptions.get(tenant_id)

    def upgrade_plan(self, tenant_id: str, new_plan_id: str) -> Subscription:
        """Upgrade tenant to a higher-tier plan."""
        sub = self._subscriptions.get(tenant_id)
        if sub is None:
            raise ValueError(f"No subscription for tenant {tenant_id}")
        if sub.status == "cancelled":
            raise ValueError("Cannot upgrade a cancelled subscription")
        current_tier = _PLAN_TIER_ORDER.get(sub.plan_id, 0)
        new_tier = _PLAN_TIER_ORDER.get(new_plan_id)
        if new_tier is None:
            raise ValueError(f"Unknown plan: {new_plan_id}")
        if new_tier <= current_tier:
            raise ValueError(
                f"Plan '{new_plan_id}' is not an upgrade from '{sub.plan_id}'"
            )
        sub.plan_id = new_plan_id
        sub.status = "active"
        return sub

    def downgrade_plan(self, tenant_id: str, new_plan_id: str) -> Subscription:
        """Downgrade tenant to a lower-tier plan."""
        sub = self._subscriptions.get(tenant_id)
        if sub is None:
            raise ValueError(f"No subscription for tenant {tenant_id}")
        if sub.status == "cancelled":
            raise ValueError("Cannot downgrade a cancelled subscription")
        current_tier = _PLAN_TIER_ORDER.get(sub.plan_id, 0)
        new_tier = _PLAN_TIER_ORDER.get(new_plan_id)
        if new_tier is None:
            raise ValueError(f"Unknown plan: {new_plan_id}")
        if new_tier >= current_tier:
            raise ValueError(
                f"Plan '{new_plan_id}' is not a downgrade from '{sub.plan_id}'"
            )
        sub.plan_id = new_plan_id
        sub.status = "active"
        return sub

    def cancel_subscription(self, tenant_id: str) -> Subscription:
        """Cancel the tenant's subscription."""
        sub = self._subscriptions.get(tenant_id)
        if sub is None:
            raise ValueError(f"No subscription for tenant {tenant_id}")
        sub.status = "cancelled"
        sub.cancel_at = self._now()
        return sub

    def check_feature_access(self, tenant_id: str, feature: str) -> bool:
        """Return ``True`` if the tenant's plan includes *feature*."""
        sub = self._subscriptions.get(tenant_id)
        if sub is None:
            return False
        if sub.status == "cancelled":
            return False
        plan = PLANS.get(sub.plan_id)
        if plan is None:
            return False
        return feature in plan.features

    def get_invoice_preview(self, tenant_id: str) -> dict[str, Any]:
        """Preview what the next invoice would look like."""
        sub = self._subscriptions.get(tenant_id)
        if sub is None:
            raise ValueError(f"No subscription for tenant {tenant_id}")
        plan = self._get_plan(sub.plan_id)
        usage = self.usage_meter.get_usage(tenant_id)
        return {
            "tenant_id": tenant_id,
            "plan": plan.plan_id,
            "plan_name": plan.name,
            "price_monthly_usd": plan.price_monthly_usd,
            "price_annual_usd": plan.price_annual_usd,
            "status": sub.status,
            "current_period_start": (
                sub.current_period_start.isoformat()
                if sub.current_period_start
                else None
            ),
            "current_period_end": (
                sub.current_period_end.isoformat()
                if sub.current_period_end
                else None
            ),
            "usage": usage,
            "amount_due_usd": plan.price_monthly_usd,
        }
