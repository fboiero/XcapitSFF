"""Customer 360 — unified view of everything we know about a customer.

Consolidates data from Customer, Ticket, Lead, and OutreachMessage models
into a single actionable profile with engagement scoring, churn risk
assessment, and personalised recommendations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import (
    Customer,
    Lead,
    OutreachMessage,
    Ticket,
    TicketMessage,
    TicketPriority,
    TicketStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class LifetimeValue(str, Enum):
    """Customer lifetime-value indicator."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class TicketSummary:
    """Lightweight summary of a single ticket."""

    id: int
    subject: str
    status: str
    priority: str
    created_at: datetime
    resolved_at: datetime | None


@dataclass
class LeadInfo:
    """Snapshot of the original lead that converted into this customer."""

    lead_id: int
    score_icp: float | None
    stage: str
    afinidad: str
    contact_name: str | None
    company_name: str | None
    created_at: datetime


@dataclass
class OutreachSummary:
    """Lightweight summary of an outreach message."""

    id: int
    channel: str
    subject: str | None
    status: str
    created_at: datetime


@dataclass
class SatisfactionIndicators:
    """Derived satisfaction signals."""

    avg_resolution_hours: float | None
    escalation_count: int
    sla_breach_count: int
    positive_signal: bool  # True if resolution times are good & few escalations


@dataclass
class Customer360:
    """Unified 360-degree view of a customer."""

    # --- basic info ---
    customer_id: int
    name: str
    email: str
    company: str
    region: str
    plan: str | None
    created_at: datetime

    # --- lead origin ---
    lead_info: LeadInfo | None

    # --- tickets ---
    ticket_history: list[TicketSummary]
    open_tickets: int
    total_tickets: int
    avg_resolution_hours: float | None

    # --- satisfaction ---
    satisfaction_indicators: SatisfactionIndicators

    # --- outreach ---
    outreach_history: list[OutreachSummary]

    # --- scores ---
    engagement_score: float  # 0-100
    lifetime_value_indicator: LifetimeValue

    # --- risk & recommendations ---
    risk_indicators: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring helpers (pure functions — easy to test)
# ---------------------------------------------------------------------------

# Plan tiers used for lifetime-value classification
_PREMIUM_PLANS = {"enterprise", "premium", "pro", "business"}
_MID_PLANS = {"standard", "growth", "plus"}


def calculate_engagement_score(
    tickets: list[TicketSummary],
    outreach: list[OutreachSummary],
) -> float:
    """Return a 0-100 engagement score based on ticket interactions and outreach.

    Scoring breakdown (all values are capped so the total never exceeds 100):
      - Ticket activity  : up to 40 pts (2 pts per ticket, max 40)
      - Recency bonus    : up to 20 pts (20 if a ticket was created in the last 30 days)
      - Outreach replies : up to 25 pts (5 pts per replied message, max 25)
      - Outreach sent    : up to 15 pts (3 pts per sent message, max 15)
    """
    score = 0.0

    # Ticket activity (2 pts each, max 40)
    score += min(len(tickets) * 2, 40)

    # Recency bonus (20 pts if any ticket in the last 30 days)
    now = datetime.now(tz=None)
    for t in tickets:
        delta = (now - t.created_at).days
        if delta <= 30:
            score += 20
            break

    # Outreach — replied messages (5 pts each, max 25)
    replied = [o for o in outreach if o.status == "replied"]
    score += min(len(replied) * 5, 25)

    # Outreach — sent messages (3 pts each, max 15)
    sent = [o for o in outreach if o.status == "sent"]
    score += min(len(sent) * 3, 15)

    return min(round(score, 1), 100.0)


def _classify_lifetime_value(
    plan: str | None,
    engagement_score: float,
    total_tickets: int,
) -> LifetimeValue:
    """Classify a customer's lifetime value as HIGH / MEDIUM / LOW."""
    plan_lower = (plan or "").strip().lower()

    if plan_lower in _PREMIUM_PLANS:
        return LifetimeValue.HIGH

    if plan_lower in _MID_PLANS and engagement_score >= 40:
        return LifetimeValue.HIGH

    if engagement_score >= 60 or (plan_lower in _MID_PLANS):
        return LifetimeValue.MEDIUM

    if total_tickets >= 5 and engagement_score >= 30:
        return LifetimeValue.MEDIUM

    return LifetimeValue.LOW


def assess_churn_risk(c360: Customer360) -> list[str]:
    """Return a list of risk-flag strings for the customer.

    Each flag is a short, machine-readable identifier suitable for dashboards
    and alerting rules.
    """
    risks: list[str] = []

    # High open-ticket ratio
    if c360.open_tickets >= 3:
        risks.append("high_ticket_volume")

    # Slow resolutions
    if c360.avg_resolution_hours is not None and c360.avg_resolution_hours > 48:
        risks.append("slow_resolutions")

    # SLA breaches
    if c360.satisfaction_indicators.sla_breach_count > 0:
        risks.append("sla_breaches")

    # Multiple escalations
    if c360.satisfaction_indicators.escalation_count >= 2:
        risks.append("frequent_escalations")

    # Low engagement on a paid plan
    if c360.plan and c360.engagement_score < 20:
        risks.append("low_engagement")

    # Approaching churn: combination of low engagement + open tickets
    if c360.engagement_score < 30 and c360.open_tickets >= 1:
        risks.append("approaching_churn")

    # No recent activity (engagement score is zero)
    if c360.engagement_score == 0 and c360.total_tickets > 0:
        risks.append("inactive_customer")

    return risks


def generate_recommendations(c360: Customer360) -> list[str]:
    """Return actionable recommendations based on the customer's 360 profile."""
    recs: list[str] = []

    if "high_ticket_volume" in c360.risk_indicators:
        recs.append("Schedule a proactive check-in call to address recurring issues.")

    if "slow_resolutions" in c360.risk_indicators:
        recs.append("Escalate to senior support to improve resolution times.")

    if "sla_breaches" in c360.risk_indicators:
        recs.append("Review SLA compliance and assign a dedicated support agent.")

    if "frequent_escalations" in c360.risk_indicators:
        recs.append("Assign a customer success manager to prevent further escalations.")

    if "low_engagement" in c360.risk_indicators:
        recs.append("Launch a re-engagement outreach campaign with personalised content.")

    if "approaching_churn" in c360.risk_indicators:
        recs.append("Initiate churn-prevention workflow: discount offer or executive outreach.")

    if "inactive_customer" in c360.risk_indicators:
        recs.append("Send a win-back email sequence highlighting new features.")

    # Positive recommendations
    if c360.lifetime_value_indicator == LifetimeValue.HIGH and not c360.risk_indicators:
        recs.append("Consider upsell opportunities — customer is highly engaged.")

    if c360.engagement_score >= 70 and c360.open_tickets == 0:
        recs.append("Invite customer to participate in case-study or referral programme.")

    if c360.lead_info and c360.lead_info.afinidad == "HIGH" and not c360.risk_indicators:
        recs.append("Explore cross-sell opportunities given high original lead affinity.")

    return recs


# ---------------------------------------------------------------------------
# Database-backed builders (async)
# ---------------------------------------------------------------------------


async def _fetch_lead_info(db: AsyncSession, lead_id: int) -> LeadInfo | None:
    """Load lead info by ID, returning None if not found."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        return None
    return LeadInfo(
        lead_id=lead.id,
        score_icp=lead.score_icp,
        stage=lead.stage if isinstance(lead.stage, str) else lead.stage.value,
        afinidad=lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
        contact_name=lead.contact_name,
        company_name=lead.company_name,
        created_at=lead.created_at,
    )


async def _fetch_tickets(db: AsyncSession, customer_id: int) -> list[Ticket]:
    """Fetch all tickets for a customer, ordered by creation date desc."""
    result = await db.execute(
        select(Ticket)
        .where(Ticket.customer_id == customer_id)
        .order_by(Ticket.created_at.desc())
    )
    return list(result.scalars().all())


async def _fetch_outreach(db: AsyncSession, lead_id: int) -> list[OutreachMessage]:
    """Fetch all outreach messages linked to the original lead."""
    result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.lead_id == lead_id)
        .order_by(OutreachMessage.created_at.desc())
    )
    return list(result.scalars().all())


async def _count_escalations(db: AsyncSession, customer_id: int) -> int:
    """Count tickets that were assigned to a different agent (proxy for escalation)."""
    result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.customer_id == customer_id,
            Ticket.priority.in_([TicketPriority.HIGH.value, TicketPriority.URGENT.value]),
        )
    )
    return result.scalar() or 0


async def _count_sla_breaches(db: AsyncSession, customer_id: int) -> int:
    """Count tickets that were resolved after the SLA deadline."""
    result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.customer_id == customer_id,
            Ticket.sla_deadline.isnot(None),
            Ticket.resolved_at.isnot(None),
            Ticket.resolved_at > Ticket.sla_deadline,
        )
    )
    return result.scalar() or 0


def _build_ticket_summaries(tickets: list[Ticket]) -> list[TicketSummary]:
    """Convert ORM ticket objects to lightweight summaries."""
    summaries: list[TicketSummary] = []
    for t in tickets:
        summaries.append(
            TicketSummary(
                id=t.id,
                subject=t.subject,
                status=t.status if isinstance(t.status, str) else t.status.value,
                priority=t.priority if isinstance(t.priority, str) else t.priority.value,
                created_at=t.created_at,
                resolved_at=t.resolved_at,
            )
        )
    return summaries


def _build_outreach_summaries(messages: list[OutreachMessage]) -> list[OutreachSummary]:
    """Convert ORM outreach messages to lightweight summaries."""
    return [
        OutreachSummary(
            id=m.id,
            channel=m.channel,
            subject=m.subject,
            status=m.status,
            created_at=m.created_at,
        )
        for m in messages
    ]


def _compute_avg_resolution_hours(tickets: list[Ticket]) -> float | None:
    """Compute average resolution time in hours for resolved tickets."""
    hours: list[float] = []
    for t in tickets:
        if t.resolved_at and t.created_at:
            delta = t.resolved_at - t.created_at
            hours.append(delta.total_seconds() / 3600)
    if not hours:
        return None
    return round(sum(hours) / len(hours), 1)


async def build_customer_360(db: AsyncSession, customer_id: int) -> Customer360 | None:
    """Build the full 360-degree view for a single customer.

    Returns ``None`` if the customer does not exist.
    """
    # Fetch customer
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        return None

    # Fetch related data
    tickets = await _fetch_tickets(db, customer_id)

    lead_info: LeadInfo | None = None
    outreach_messages: list[OutreachMessage] = []
    if customer.lead_id:
        lead_info = await _fetch_lead_info(db, customer.lead_id)
        outreach_messages = await _fetch_outreach(db, customer.lead_id)

    escalation_count = await _count_escalations(db, customer_id)
    sla_breach_count = await _count_sla_breaches(db, customer_id)

    # Derive summaries
    ticket_summaries = _build_ticket_summaries(tickets)
    outreach_summaries = _build_outreach_summaries(outreach_messages)

    open_statuses = {TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value, TicketStatus.WAITING_CUSTOMER.value}
    open_tickets = sum(
        1 for t in tickets
        if (t.status if isinstance(t.status, str) else t.status.value) in open_statuses
    )
    avg_hours = _compute_avg_resolution_hours(tickets)

    # Satisfaction
    satisfaction = SatisfactionIndicators(
        avg_resolution_hours=avg_hours,
        escalation_count=escalation_count,
        sla_breach_count=sla_breach_count,
        positive_signal=(
            (avg_hours is not None and avg_hours <= 24)
            and escalation_count == 0
            and sla_breach_count == 0
        ),
    )

    # Scores
    engagement = calculate_engagement_score(ticket_summaries, outreach_summaries)
    ltv = _classify_lifetime_value(customer.plan, engagement, len(tickets))

    # Build initial C360 (without risk/recs so we can derive them)
    region_val = customer.region if isinstance(customer.region, str) else customer.region.value

    c360 = Customer360(
        customer_id=customer.id,
        name=customer.contact_name,
        email=customer.contact_email,
        company=customer.company_name,
        region=region_val,
        plan=customer.plan,
        created_at=customer.created_at,
        lead_info=lead_info,
        ticket_history=ticket_summaries,
        open_tickets=open_tickets,
        total_tickets=len(tickets),
        avg_resolution_hours=avg_hours,
        satisfaction_indicators=satisfaction,
        outreach_history=outreach_summaries,
        engagement_score=engagement,
        lifetime_value_indicator=ltv,
    )

    # Risk & recommendations (depend on the assembled c360)
    c360.risk_indicators = assess_churn_risk(c360)
    c360.recommendations = generate_recommendations(c360)

    logger.info(
        "Customer360 built: id=%d engagement=%.1f ltv=%s risks=%d recs=%d",
        customer_id,
        engagement,
        ltv.value,
        len(c360.risk_indicators),
        len(c360.recommendations),
    )
    return c360


async def get_vip_customers(db: AsyncSession, limit: int = 10) -> list[Customer360]:
    """Return the highest-value customers sorted by engagement score descending.

    VIP = lifetime_value_indicator is HIGH.  Falls back to all customers
    sorted by engagement when fewer than ``limit`` HIGH-value customers exist.
    """
    result = await db.execute(select(Customer).order_by(Customer.created_at.desc()))
    customers = list(result.scalars().all())

    profiles: list[Customer360] = []
    for cust in customers:
        c360 = await build_customer_360(db, cust.id)
        if c360 is not None:
            profiles.append(c360)

    # Prefer HIGH lifetime value, then sort by engagement
    profiles.sort(
        key=lambda c: (
            c.lifetime_value_indicator == LifetimeValue.HIGH,
            c.engagement_score,
        ),
        reverse=True,
    )
    return profiles[:limit]


async def get_at_risk_customers(db: AsyncSession) -> list[Customer360]:
    """Return all customers that have at least one risk indicator."""
    result = await db.execute(select(Customer))
    customers = list(result.scalars().all())

    at_risk: list[Customer360] = []
    for cust in customers:
        c360 = await build_customer_360(db, cust.id)
        if c360 is not None and c360.risk_indicators:
            at_risk.append(c360)

    # Most risks first
    at_risk.sort(key=lambda c: len(c.risk_indicators), reverse=True)
    return at_risk
