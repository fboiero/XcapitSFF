"""API endpoints for Customer 360 views."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.customer360 import (
    Customer360,
    LeadInfo,
    LifetimeValue,
    OutreachSummary,
    SatisfactionIndicators,
    TicketSummary,
    build_customer_360,
    get_at_risk_customers,
    get_vip_customers,
)
from xcapitsff.core.database import get_db

router = APIRouter(prefix="/customers", tags=["Customer 360"])


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class TicketSummaryResponse(BaseModel):
    id: int
    subject: str
    status: str
    priority: str
    created_at: datetime
    resolved_at: datetime | None


class LeadInfoResponse(BaseModel):
    lead_id: int
    score_icp: float | None
    stage: str
    afinidad: str
    contact_name: str | None
    company_name: str | None
    created_at: datetime


class OutreachSummaryResponse(BaseModel):
    id: int
    channel: str
    subject: str | None
    status: str
    created_at: datetime


class SatisfactionIndicatorsResponse(BaseModel):
    avg_resolution_hours: float | None
    escalation_count: int
    sla_breach_count: int
    positive_signal: bool


class Customer360Response(BaseModel):
    customer_id: int
    name: str
    email: str
    company: str
    region: str
    plan: str | None
    created_at: datetime

    lead_info: LeadInfoResponse | None
    ticket_history: list[TicketSummaryResponse]
    open_tickets: int
    total_tickets: int
    avg_resolution_hours: float | None

    satisfaction_indicators: SatisfactionIndicatorsResponse
    outreach_history: list[OutreachSummaryResponse]

    engagement_score: float
    lifetime_value_indicator: str

    risk_indicators: list[str]
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_c360(c360: Customer360) -> dict[str, Any]:
    """Convert a Customer360 dataclass to a dict suitable for the response model."""
    lead = None
    if c360.lead_info:
        lead = LeadInfoResponse(
            lead_id=c360.lead_info.lead_id,
            score_icp=c360.lead_info.score_icp,
            stage=c360.lead_info.stage,
            afinidad=c360.lead_info.afinidad,
            contact_name=c360.lead_info.contact_name,
            company_name=c360.lead_info.company_name,
            created_at=c360.lead_info.created_at,
        )

    tickets = [
        TicketSummaryResponse(
            id=t.id,
            subject=t.subject,
            status=t.status,
            priority=t.priority,
            created_at=t.created_at,
            resolved_at=t.resolved_at,
        )
        for t in c360.ticket_history
    ]

    outreach = [
        OutreachSummaryResponse(
            id=o.id,
            channel=o.channel,
            subject=o.subject,
            status=o.status,
            created_at=o.created_at,
        )
        for o in c360.outreach_history
    ]

    satisfaction = SatisfactionIndicatorsResponse(
        avg_resolution_hours=c360.satisfaction_indicators.avg_resolution_hours,
        escalation_count=c360.satisfaction_indicators.escalation_count,
        sla_breach_count=c360.satisfaction_indicators.sla_breach_count,
        positive_signal=c360.satisfaction_indicators.positive_signal,
    )

    return Customer360Response(
        customer_id=c360.customer_id,
        name=c360.name,
        email=c360.email,
        company=c360.company,
        region=c360.region,
        plan=c360.plan,
        created_at=c360.created_at,
        lead_info=lead,
        ticket_history=tickets,
        open_tickets=c360.open_tickets,
        total_tickets=c360.total_tickets,
        avg_resolution_hours=c360.avg_resolution_hours,
        satisfaction_indicators=satisfaction,
        outreach_history=outreach,
        engagement_score=c360.engagement_score,
        lifetime_value_indicator=c360.lifetime_value_indicator.value,
        risk_indicators=c360.risk_indicators,
        recommendations=c360.recommendations,
    ).model_dump()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{customer_id}/360", response_model=Customer360Response)
async def api_customer_360(customer_id: int, db: AsyncSession = Depends(get_db)):
    """Full 360-degree view for a single customer."""
    c360 = await build_customer_360(db, customer_id)
    if c360 is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _serialize_c360(c360)


@router.get("/vip", response_model=list[Customer360Response])
async def api_vip_customers(
    limit: int = Query(default=10, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Top VIP customers by lifetime value and engagement."""
    vips = await get_vip_customers(db, limit=limit)
    return [_serialize_c360(c) for c in vips]


@router.get("/at-risk", response_model=list[Customer360Response])
async def api_at_risk_customers(db: AsyncSession = Depends(get_db)):
    """Customers with active risk indicators."""
    at_risk = await get_at_risk_customers(db)
    return [_serialize_c360(c) for c in at_risk]
