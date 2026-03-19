"""API endpoints for tenant onboarding flow."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from xcapitsff.core.billing import BillingManager, UsageMeter

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# ---------------------------------------------------------------------------
# Shared state (in production replaced by DB / DI)
# ---------------------------------------------------------------------------

_usage_meter = UsageMeter()
_billing_manager = BillingManager(usage_meter=_usage_meter)

# tenant_id -> onboarding state
_onboarding_state: dict[str, dict] = {}

# tenant_id -> demo-data flag
_demo_seeded: dict[str, bool] = {}


def get_billing_manager() -> BillingManager:
    return _billing_manager


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class StartOnboardingRequest(BaseModel):
    company_name: str
    admin_name: str
    admin_email: EmailStr
    password: str
    industry: str = "general"


class StartOnboardingResponse(BaseModel):
    tenant_id: str
    user_id: str
    token: str
    trial_days: int


class SeedDemoRequest(BaseModel):
    tenant_id: str


class SeedDemoResponse(BaseModel):
    tenant_id: str
    leads_created: int
    tickets_created: int
    kb_articles_created: int


class OnboardingStep(BaseModel):
    name: str
    completed: bool
    description: str


class ChecklistResponse(BaseModel):
    tenant_id: str
    steps: list[OnboardingStep]


class CompleteOnboardingRequest(BaseModel):
    tenant_id: str


class CompleteOnboardingResponse(BaseModel):
    tenant_id: str
    completed: bool
    completed_at: str


# ---------------------------------------------------------------------------
# Default checklist template
# ---------------------------------------------------------------------------

_CHECKLIST_TEMPLATE = [
    OnboardingStep(
        name="create_account",
        completed=False,
        description="Create your account and start a trial",
    ),
    OnboardingStep(
        name="import_leads",
        completed=False,
        description="Import your first batch of leads",
    ),
    OnboardingStep(
        name="create_first_ticket",
        completed=False,
        description="Create your first support ticket",
    ),
    OnboardingStep(
        name="setup_outreach",
        completed=False,
        description="Set up your first outreach sequence",
    ),
    OnboardingStep(
        name="review_dashboard",
        completed=False,
        description="Review the analytics dashboard",
    ),
]


def _init_checklist(tenant_id: str) -> list[OnboardingStep]:
    """Create a fresh checklist, marking create_account as done."""
    steps = [
        OnboardingStep(name=s.name, completed=s.completed, description=s.description)
        for s in _CHECKLIST_TEMPLATE
    ]
    # The first step is always done right after onboarding starts
    steps[0].completed = True
    return steps


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/start", response_model=StartOnboardingResponse)
async def start_onboarding(request: StartOnboardingRequest):
    """Start onboarding — creates tenant, user, and trial subscription."""
    tenant_id = uuid.uuid4().hex[:16]
    user_id = uuid.uuid4().hex[:16]
    token = uuid.uuid4().hex  # placeholder token

    trial_days = 14

    bm = get_billing_manager()
    bm.create_subscription(tenant_id, "pro", trial_days=trial_days)

    # Store onboarding state
    _onboarding_state[tenant_id] = {
        "company_name": request.company_name,
        "admin_name": request.admin_name,
        "admin_email": request.admin_email,
        "industry": request.industry,
        "user_id": user_id,
        "checklist": _init_checklist(tenant_id),
        "completed": False,
        "completed_at": None,
    }

    return StartOnboardingResponse(
        tenant_id=tenant_id,
        user_id=user_id,
        token=token,
        trial_days=trial_days,
    )


@router.post("/seed-demo", response_model=SeedDemoResponse)
async def seed_demo_data(request: SeedDemoRequest):
    """Seed sample demo data (leads, tickets, KB articles) for the tenant."""
    tenant_id = request.tenant_id
    if tenant_id not in _onboarding_state:
        raise HTTPException(status_code=404, detail="Tenant not found in onboarding")

    # In production this would insert real DB rows.
    # Here we simulate the counts.
    leads_created = 25
    tickets_created = 10
    kb_articles_created = 5

    _demo_seeded[tenant_id] = True

    # Mark import_leads step as completed (demo counts)
    state = _onboarding_state[tenant_id]
    for step in state["checklist"]:
        if step.name == "import_leads":
            step.completed = True

    return SeedDemoResponse(
        tenant_id=tenant_id,
        leads_created=leads_created,
        tickets_created=tickets_created,
        kb_articles_created=kb_articles_created,
    )


@router.get("/checklist", response_model=ChecklistResponse)
async def get_checklist(tenant_id: str):
    """Return the onboarding checklist status for a tenant."""
    state = _onboarding_state.get(tenant_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Tenant not found in onboarding")

    return ChecklistResponse(
        tenant_id=tenant_id,
        steps=state["checklist"],
    )


@router.post("/complete", response_model=CompleteOnboardingResponse)
async def complete_onboarding(request: CompleteOnboardingRequest):
    """Mark onboarding as complete."""
    tenant_id = request.tenant_id
    state = _onboarding_state.get(tenant_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Tenant not found in onboarding")

    now = datetime.now(timezone.utc)
    state["completed"] = True
    state["completed_at"] = now.isoformat()

    # Mark all steps completed
    for step in state["checklist"]:
        step.completed = True

    return CompleteOnboardingResponse(
        tenant_id=tenant_id,
        completed=True,
        completed_at=now.isoformat(),
    )
