"""Multi-tenant core — tenant isolation and management."""

from __future__ import annotations

import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Plan definitions
# ---------------------------------------------------------------------------

class Plan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Use -1 to represent "unlimited"
_UNLIMITED = -1

PLAN_LIMITS: dict[Plan, dict[str, int]] = {
    Plan.FREE: {
        "max_leads": 100,
        "max_tickets": 50,
        "max_users": 2,
        "api_calls_limit_monthly": 1_000,
    },
    Plan.PRO: {
        "max_leads": 5_000,
        "max_tickets": 500,
        "max_users": 10,
        "api_calls_limit_monthly": 50_000,
    },
    Plan.ENTERPRISE: {
        "max_leads": _UNLIMITED,
        "max_tickets": _UNLIMITED,
        "max_users": _UNLIMITED,
        "api_calls_limit_monthly": _UNLIMITED,
    },
}


# ---------------------------------------------------------------------------
# Tenant dataclass
# ---------------------------------------------------------------------------

@dataclass
class Tenant:
    tenant_id: str
    name: str
    slug: str
    plan: Plan
    is_active: bool
    created_at: datetime
    settings: dict[str, Any]
    owner_email: str
    max_leads: int
    max_tickets: int
    max_users: int
    api_calls_limit_monthly: int


def _slugify(name: str) -> str:
    """Convert a tenant name into a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


# ---------------------------------------------------------------------------
# TenantManager
# ---------------------------------------------------------------------------

class TenantManager:
    """In-memory tenant store (swap with DB-backed implementation later)."""

    def __init__(self) -> None:
        self._tenants: dict[str, Tenant] = {}
        # Track usage per tenant: {"leads": N, "tickets": N, "users": N, "api_calls": N}
        self._usage: dict[str, dict[str, int]] = {}

    # -- CRUD ---------------------------------------------------------------

    def create_tenant(
        self,
        name: str,
        owner_email: str,
        plan: str | Plan = Plan.FREE,
    ) -> Tenant:
        if isinstance(plan, str):
            plan = Plan(plan)

        limits = PLAN_LIMITS[plan]
        slug = _slugify(name)

        # Ensure slug uniqueness
        base_slug = slug
        counter = 1
        while any(t.slug == slug for t in self._tenants.values()):
            slug = f"{base_slug}-{counter}"
            counter += 1

        tenant_id = str(uuid.uuid4())
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            plan=plan,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            settings={},
            owner_email=owner_email,
            max_leads=limits["max_leads"],
            max_tickets=limits["max_tickets"],
            max_users=limits["max_users"],
            api_calls_limit_monthly=limits["api_calls_limit_monthly"],
        )
        self._tenants[tenant_id] = tenant
        self._usage[tenant_id] = {
            "leads": 0,
            "tickets": 0,
            "users": 0,
            "api_calls": 0,
        }
        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Tenant | None:
        for tenant in self._tenants.values():
            if tenant.slug == slug:
                return tenant
        return None

    def update_tenant(self, tenant_id: str, **kwargs: Any) -> Tenant:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            raise ValueError(f"Tenant {tenant_id} not found")

        # If plan is changing, update limits as well
        if "plan" in kwargs:
            new_plan = kwargs.pop("plan")
            if isinstance(new_plan, str):
                new_plan = Plan(new_plan)
            tenant.plan = new_plan
            limits = PLAN_LIMITS[new_plan]
            tenant.max_leads = limits["max_leads"]
            tenant.max_tickets = limits["max_tickets"]
            tenant.max_users = limits["max_users"]
            tenant.api_calls_limit_monthly = limits["api_calls_limit_monthly"]

        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
            else:
                raise ValueError(f"Unknown tenant attribute: {key}")

        return tenant

    def deactivate_tenant(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False
        tenant.is_active = False
        return True

    def list_tenants(
        self,
        plan: str | Plan | None = None,
        active_only: bool = True,
    ) -> list[Tenant]:
        results: list[Tenant] = []
        if isinstance(plan, str):
            plan = Plan(plan)

        for tenant in self._tenants.values():
            if active_only and not tenant.is_active:
                continue
            if plan is not None and tenant.plan != plan:
                continue
            results.append(tenant)
        return results

    # -- Limits & Usage -----------------------------------------------------

    def check_limit(
        self,
        tenant_id: str,
        resource: str,
        current_count: int,
    ) -> tuple[bool, str]:
        """Return (within_limit, message).

        ``resource`` must be one of: leads, tickets, users, api_calls.
        """
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return False, "Tenant not found"
        if not tenant.is_active:
            return False, "Tenant is deactivated"

        limit_map: dict[str, int] = {
            "leads": tenant.max_leads,
            "tickets": tenant.max_tickets,
            "users": tenant.max_users,
            "api_calls": tenant.api_calls_limit_monthly,
        }
        limit = limit_map.get(resource)
        if limit is None:
            return False, f"Unknown resource: {resource}"

        # -1 means unlimited
        if limit == _UNLIMITED:
            return True, "unlimited"

        if current_count >= limit:
            return False, f"{resource} limit reached ({current_count}/{limit})"

        return True, f"{current_count}/{limit}"

    def get_usage(self, tenant_id: str) -> dict[str, Any]:
        tenant = self._tenants.get(tenant_id)
        if tenant is None:
            return {}

        usage = self._usage.get(tenant_id, {})
        return {
            "tenant_id": tenant_id,
            "plan": tenant.plan.value,
            "leads": {"current": usage.get("leads", 0), "limit": tenant.max_leads},
            "tickets": {"current": usage.get("tickets", 0), "limit": tenant.max_tickets},
            "users": {"current": usage.get("users", 0), "limit": tenant.max_users},
            "api_calls": {
                "current": usage.get("api_calls", 0),
                "limit": tenant.api_calls_limit_monthly,
            },
        }

    def increment_usage(self, tenant_id: str, resource: str, amount: int = 1) -> None:
        """Increment a usage counter for a tenant."""
        if tenant_id in self._usage and resource in self._usage[tenant_id]:
            self._usage[tenant_id][resource] += amount


# ---------------------------------------------------------------------------
# TenantContext — context-var based current tenant tracking
# ---------------------------------------------------------------------------

_current_tenant_var: ContextVar[str | None] = ContextVar(
    "current_tenant_id", default=None,
)


def set_current_tenant(tenant_id: str) -> None:
    """Set the current tenant for this context (request / thread)."""
    _current_tenant_var.set(tenant_id)


def get_current_tenant() -> str | None:
    """Retrieve the current tenant id, or ``None``."""
    return _current_tenant_var.get()


# ---------------------------------------------------------------------------
# Module-level singleton for convenience
# ---------------------------------------------------------------------------

tenant_manager = TenantManager()
