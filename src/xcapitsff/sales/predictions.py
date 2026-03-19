"""Predictive Analytics — pipeline forecasting, churn prediction, win/loss analysis.

ML-lite predictive models that operate on database data without requiring
external ML libraries (no sklearn needed).  All scoring uses transparent,
rule-based heuristics that are easy to audit and explain.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import (
    Customer,
    Lead,
    LeadStage,
    OutreachMessage,
    Ticket,
    TicketPriority,
    TicketStatus,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage conversion base probabilities
# ---------------------------------------------------------------------------

STAGE_BASE_PROBABILITY: dict[str, float] = {
    "raw": 0.05,
    "qualified": 0.15,
    "contacted": 0.25,
    "meeting": 0.40,
    "proposal": 0.60,
    "negotiation": 0.80,
}

# Expected days per stage before a lead is considered stale
STAGE_EXPECTED_DAYS: dict[str, int] = {
    "raw": 14,
    "qualified": 10,
    "contacted": 7,
    "meeting": 7,
    "proposal": 14,
    "negotiation": 10,
}

AFINIDAD_MODIFIER: dict[str, float] = {
    "HIGH": 0.15,
    "MEDIUM": 0.0,
    "LOW": -0.15,
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PipelineForecast:
    """Forecast of pipeline conversion over a future period."""

    period_days: int
    expected_conversions: float
    expected_revenue_index: float
    confidence: float
    by_stage: dict[str, float]
    methodology: str


@dataclass
class LeadScoreHistory:
    """Score trend tracking for a single lead."""

    lead_id: int
    scores: list[tuple[str, float]]
    trend: str  # "up", "down", "stable"
    velocity: float  # score change per week


@dataclass
class ChurnRisk:
    """Churn risk assessment for a single customer."""

    customer_id: int
    risk_score: float  # 0-100
    risk_level: str  # "high", "medium", "low"
    factors: list[str]
    recommended_actions: list[str]


@dataclass
class WinLossAnalysis:
    """Aggregate win/loss pattern analysis."""

    total_won: int
    total_lost: int
    win_rate: float
    avg_days_to_win: float | None
    avg_days_to_loss: float | None
    top_win_factors: list[str]
    top_loss_factors: list[str]
    by_region: dict[str, dict[str, int]]
    by_afinidad: dict[str, dict[str, int]]


# ---------------------------------------------------------------------------
# Conversion probability calculator (pure function, easy to test)
# ---------------------------------------------------------------------------


def calculate_conversion_probability(
    *,
    stage: str,
    score_icp: float | None,
    c_level: bool,
    afinidad: str,
    days_in_stage: int,
    has_replied_outreach: bool,
) -> float:
    """Calculate the conversion probability for a single lead.

    Args:
        stage: Current pipeline stage value.
        score_icp: ICP score (0-100) or None.
        c_level: Whether the contact is C-level.
        afinidad: Affinity level ("HIGH", "MEDIUM", "LOW").
        days_in_stage: Calendar days the lead has been in the current stage.
        has_replied_outreach: Whether any outreach message was replied.

    Returns:
        A probability between 0.0 and 1.0.
    """
    base = STAGE_BASE_PROBABILITY.get(stage, 0.0)
    if base == 0.0:
        return 0.0

    probability = base

    # ICP score modifier: (score/100) * 1.5 as multiplier
    if score_icp is not None and score_icp > 0:
        icp_multiplier = (score_icp / 100.0) * 1.5
        probability *= icp_multiplier

    # C-level modifier: +20%
    if c_level:
        probability += 0.20

    # Afinidad modifier
    afinidad_upper = afinidad.strip().upper() if afinidad else "MEDIUM"
    probability += AFINIDAD_MODIFIER.get(afinidad_upper, 0.0)

    # Time decay: -1% per day beyond expected
    expected_days = STAGE_EXPECTED_DAYS.get(stage, 14)
    if days_in_stage > expected_days:
        overdue_days = days_in_stage - expected_days
        probability -= 0.01 * overdue_days

    # Engagement boost: +5% if outreach was replied
    if has_replied_outreach:
        probability += 0.05

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, probability))


# ---------------------------------------------------------------------------
# Pipeline forecast
# ---------------------------------------------------------------------------


async def forecast_pipeline(
    db: AsyncSession, period_days: int = 30
) -> PipelineForecast:
    """Forecast pipeline conversions over the given period.

    For each active lead (not won/lost), calculates conversion probability
    and aggregates into a forecast with stage-level breakdown.
    """
    # Fetch active leads (exclude won and lost)
    active_stages = [
        LeadStage.RAW.value,
        LeadStage.QUALIFIED.value,
        LeadStage.CONTACTED.value,
        LeadStage.MEETING.value,
        LeadStage.PROPOSAL.value,
        LeadStage.NEGOTIATION.value,
    ]
    result = await db.execute(
        select(Lead).where(Lead.stage.in_(active_stages))
    )
    leads = list(result.scalars().all())

    now = datetime.now(tz=None)
    by_stage: dict[str, float] = {}
    total_probability = 0.0
    total_revenue_index = 0.0
    lead_count = 0

    for lead in leads:
        stage_val = lead.stage if isinstance(lead.stage, str) else lead.stage.value
        days_in_stage = (now - lead.updated_at).days if lead.updated_at else 0

        # Check if any outreach was replied
        outreach_result = await db.execute(
            select(OutreachMessage).where(
                OutreachMessage.lead_id == lead.id,
                OutreachMessage.status == "replied",
            )
        )
        has_replied = outreach_result.scalars().first() is not None

        afinidad_val = lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value

        prob = calculate_conversion_probability(
            stage=stage_val,
            score_icp=lead.score_icp,
            c_level=lead.c_level,
            afinidad=afinidad_val,
            days_in_stage=days_in_stage,
            has_replied_outreach=has_replied,
        )

        total_probability += prob
        # Revenue index: probability weighted by ICP score (proxy for deal value)
        score = lead.score_icp if lead.score_icp is not None else 50.0
        total_revenue_index += prob * (score / 100.0)

        by_stage[stage_val] = by_stage.get(stage_val, 0.0) + prob
        lead_count += 1

    # Confidence: based on number of active leads and data completeness
    if lead_count == 0:
        confidence = 0.0
    elif lead_count < 5:
        confidence = 0.3
    elif lead_count < 20:
        confidence = 0.6
    else:
        confidence = 0.85

    # Round values for clean output
    by_stage = {k: round(v, 3) for k, v in by_stage.items()}

    forecast = PipelineForecast(
        period_days=period_days,
        expected_conversions=round(total_probability, 2),
        expected_revenue_index=round(total_revenue_index, 3),
        confidence=confidence,
        by_stage=by_stage,
        methodology=(
            "Rule-based conversion probability using stage position, ICP score, "
            "C-level status, afinidad, time decay, and engagement signals."
        ),
    )

    logger.info(
        "Pipeline forecast: period=%dd expected_conversions=%.2f confidence=%.2f",
        period_days,
        forecast.expected_conversions,
        forecast.confidence,
    )
    return forecast


# ---------------------------------------------------------------------------
# Lead score trend analysis
# ---------------------------------------------------------------------------


async def analyze_score_trends(
    db: AsyncSession, period_days: int = 30
) -> list[LeadScoreHistory]:
    """Analyze lead score trends over the given period.

    Uses created_at and current score to infer trajectory.  Leads created
    more recently with higher scores are trending up; those with stale dates
    and low scores are trending down.
    """
    cutoff = datetime.now(tz=None) - timedelta(days=period_days)
    result = await db.execute(
        select(Lead)
        .where(Lead.created_at >= cutoff)
        .order_by(Lead.created_at.desc())
    )
    leads = list(result.scalars().all())

    histories: list[LeadScoreHistory] = []

    for lead in leads:
        current_score = lead.score_icp if lead.score_icp is not None else 0.0
        created_date = lead.created_at.strftime("%Y-%m-%d") if lead.created_at else ""
        updated_date = lead.updated_at.strftime("%Y-%m-%d") if lead.updated_at else created_date

        # Build a simplified score history using creation and current state
        scores: list[tuple[str, float]] = []
        # Initial score estimate: lower for raw leads
        stage_val = lead.stage if isinstance(lead.stage, str) else lead.stage.value
        initial_score = current_score * STAGE_BASE_PROBABILITY.get(stage_val, 0.1) * 10
        initial_score = min(max(initial_score, 0.0), 100.0)

        scores.append((created_date, round(initial_score, 1)))
        if updated_date != created_date:
            scores.append((updated_date, round(current_score, 1)))
        else:
            scores.append((created_date, round(current_score, 1)))

        # Calculate trend
        if len(scores) >= 2:
            score_diff = scores[-1][1] - scores[0][1]
        else:
            score_diff = 0.0

        if score_diff > 5:
            trend = "up"
        elif score_diff < -5:
            trend = "down"
        else:
            trend = "stable"

        # Velocity: score change per week
        days_elapsed = (lead.updated_at - lead.created_at).days if lead.updated_at and lead.created_at else 1
        weeks = max(days_elapsed / 7.0, 1 / 7.0)  # avoid division by zero
        velocity = round(score_diff / weeks, 2)

        histories.append(
            LeadScoreHistory(
                lead_id=lead.id,
                scores=scores,
                trend=trend,
                velocity=velocity,
            )
        )

    logger.info("Score trends analyzed: %d leads in %d-day window", len(histories), period_days)
    return histories


# ---------------------------------------------------------------------------
# Churn risk prediction
# ---------------------------------------------------------------------------


def _calculate_churn_risk_score(
    *,
    ticket_count: int,
    complaint_ticket_count: int,
    avg_resolution_hours: float | None,
    sla_breach_count: int,
    days_since_last_interaction: int,
    escalation_count: int,
    plan: str | None,
) -> tuple[float, list[str], list[str]]:
    """Calculate a churn risk score (0-100) with explanatory factors and actions.

    This is a pure function to make testing straightforward.

    Returns:
        A tuple of (risk_score, factors, recommended_actions).
    """
    risk = 0.0
    factors: list[str] = []
    actions: list[str] = []

    # Ticket frequency — high complaint tickets = frustrated
    if complaint_ticket_count >= 3:
        risk += 20
        factors.append(f"High complaint ticket volume ({complaint_ticket_count} complaints)")
        actions.append("Schedule proactive check-in to address recurring complaints")
    elif ticket_count >= 5:
        risk += 10
        factors.append(f"High ticket volume ({ticket_count} total tickets)")
        actions.append("Review ticket themes and assign dedicated support agent")

    # Resolution time trend
    if avg_resolution_hours is not None:
        if avg_resolution_hours > 72:
            risk += 20
            factors.append(f"Slow resolution times (avg {avg_resolution_hours:.0f}h)")
            actions.append("Escalate to senior support to improve resolution times")
        elif avg_resolution_hours > 48:
            risk += 10
            factors.append(f"Above-average resolution times (avg {avg_resolution_hours:.0f}h)")
            actions.append("Monitor resolution time trend")

    # SLA breaches
    if sla_breach_count > 0:
        risk += min(sla_breach_count * 10, 25)
        factors.append(f"{sla_breach_count} SLA breach(es)")
        actions.append("Review SLA compliance and consider dedicated support agent")

    # Days since last interaction
    if days_since_last_interaction > 90:
        risk += 20
        factors.append(f"No interaction in {days_since_last_interaction} days")
        actions.append("Launch re-engagement campaign immediately")
    elif days_since_last_interaction > 60:
        risk += 10
        factors.append(f"No interaction in {days_since_last_interaction} days")
        actions.append("Send check-in email and schedule follow-up call")

    # Escalation count
    if escalation_count >= 3:
        risk += 15
        factors.append(f"Multiple escalations ({escalation_count})")
        actions.append("Assign customer success manager to prevent further escalations")
    elif escalation_count >= 1:
        risk += 5
        factors.append(f"{escalation_count} escalation(s)")

    # Plan type: free = higher churn risk
    plan_lower = (plan or "").strip().lower()
    if plan_lower in ("free", "") or plan is None:
        risk += 15
        factors.append("Free or no plan — lower switching cost")
        actions.append("Present upgrade offer with clear value proposition")

    risk = max(0.0, min(100.0, risk))
    return round(risk, 1), factors, actions


async def predict_churn(db: AsyncSession) -> list[ChurnRisk]:
    """Predict churn risk for all customers.

    Evaluates each customer against multiple signals including ticket
    frequency, resolution times, SLA breaches, interaction recency,
    escalations, and plan type.

    Returns:
        List of ChurnRisk sorted by risk_score descending.
    """
    result = await db.execute(select(Customer))
    customers = list(result.scalars().all())

    now = datetime.now(tz=None)
    churn_risks: list[ChurnRisk] = []

    for customer in customers:
        # Fetch tickets
        tickets_result = await db.execute(
            select(Ticket).where(Ticket.customer_id == customer.id)
        )
        tickets = list(tickets_result.scalars().all())

        ticket_count = len(tickets)

        # Complaint tickets: those with category containing "complaint" or "bug"
        complaint_count = sum(
            1 for t in tickets
            if t.category and any(
                kw in t.category.lower() for kw in ("complaint", "bug", "issue", "error")
            )
        )

        # Average resolution hours
        resolution_hours: list[float] = []
        for t in tickets:
            if t.resolved_at and t.created_at:
                delta = t.resolved_at - t.created_at
                resolution_hours.append(delta.total_seconds() / 3600)
        avg_res_hours = (
            sum(resolution_hours) / len(resolution_hours)
            if resolution_hours
            else None
        )

        # SLA breaches
        sla_breach_count = sum(
            1 for t in tickets
            if t.sla_deadline and t.resolved_at and t.resolved_at > t.sla_deadline
        )
        # Also count unresolved tickets past SLA
        sla_breach_count += sum(
            1 for t in tickets
            if (
                t.sla_deadline
                and t.resolved_at is None
                and t.sla_deadline < now
                and (t.status if isinstance(t.status, str) else t.status.value)
                not in ("resolved", "closed")
            )
        )

        # Days since last interaction
        if tickets:
            last_ticket_date = max(t.created_at for t in tickets if t.created_at)
            days_since = (now - last_ticket_date).days
        else:
            days_since = (now - customer.created_at).days if customer.created_at else 365

        # Escalation count (high/urgent tickets as proxy)
        escalation_count = sum(
            1 for t in tickets
            if (t.priority if isinstance(t.priority, str) else t.priority.value)
            in ("high", "urgent")
        )

        risk_score, factors, actions = _calculate_churn_risk_score(
            ticket_count=ticket_count,
            complaint_ticket_count=complaint_count,
            avg_resolution_hours=avg_res_hours,
            sla_breach_count=sla_breach_count,
            days_since_last_interaction=days_since,
            escalation_count=escalation_count,
            plan=customer.plan,
        )

        if risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        churn_risks.append(
            ChurnRisk(
                customer_id=customer.id,
                risk_score=risk_score,
                risk_level=risk_level,
                factors=factors,
                recommended_actions=actions,
            )
        )

    # Sort by risk score descending
    churn_risks.sort(key=lambda c: c.risk_score, reverse=True)

    logger.info(
        "Churn prediction: %d customers analyzed, %d high-risk",
        len(churn_risks),
        sum(1 for c in churn_risks if c.risk_level == "high"),
    )
    return churn_risks


# ---------------------------------------------------------------------------
# Win/loss analysis
# ---------------------------------------------------------------------------


async def analyze_win_loss(db: AsyncSession) -> WinLossAnalysis:
    """Analyze won vs lost leads to identify success and failure patterns.

    Calculates win rate, average time to close, and correlations between
    lead attributes (region, afinidad, c-level status) and outcomes.
    """
    # Fetch won leads
    won_result = await db.execute(
        select(Lead).where(Lead.stage == LeadStage.WON.value)
    )
    won_leads = list(won_result.scalars().all())

    # Fetch lost leads
    lost_result = await db.execute(
        select(Lead).where(Lead.stage == LeadStage.LOST.value)
    )
    lost_leads = list(lost_result.scalars().all())

    total_won = len(won_leads)
    total_lost = len(lost_leads)
    total = total_won + total_lost
    win_rate = (total_won / total * 100) if total > 0 else 0.0

    # Average days to win / loss
    def _avg_days(leads: list) -> float | None:
        days_list: list[float] = []
        for lead in leads:
            if lead.updated_at and lead.created_at:
                delta = lead.updated_at - lead.created_at
                days_list.append(delta.total_seconds() / 86400)
        if not days_list:
            return None
        return round(sum(days_list) / len(days_list), 1)

    avg_days_to_win = _avg_days(won_leads)
    avg_days_to_loss = _avg_days(lost_leads)

    # By region breakdown
    by_region: dict[str, dict[str, int]] = {}
    for lead in won_leads + lost_leads:
        region_val = lead.region if isinstance(lead.region, str) else lead.region.value
        if region_val not in by_region:
            by_region[region_val] = {"won": 0, "lost": 0}
        stage_val = lead.stage if isinstance(lead.stage, str) else lead.stage.value
        if stage_val == "won":
            by_region[region_val]["won"] += 1
        else:
            by_region[region_val]["lost"] += 1

    # By afinidad breakdown
    by_afinidad: dict[str, dict[str, int]] = {}
    for lead in won_leads + lost_leads:
        afin_val = lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value
        if afin_val not in by_afinidad:
            by_afinidad[afin_val] = {"won": 0, "lost": 0}
        stage_val = lead.stage if isinstance(lead.stage, str) else lead.stage.value
        if stage_val == "won":
            by_afinidad[afin_val]["won"] += 1
        else:
            by_afinidad[afin_val]["lost"] += 1

    # Identify top factors
    top_win_factors: list[str] = []
    top_loss_factors: list[str] = []

    # C-level correlation
    won_c_level = sum(1 for l in won_leads if l.c_level)
    lost_c_level = sum(1 for l in lost_leads if l.c_level)
    if total_won > 0 and won_c_level / max(total_won, 1) > 0.5:
        top_win_factors.append(f"C-level contacts ({won_c_level}/{total_won} wins)")
    if total_lost > 0 and lost_c_level / max(total_lost, 1) < 0.2:
        top_loss_factors.append("Non-C-level contacts more likely to churn from pipeline")

    # Afinidad correlation
    for afin, counts in by_afinidad.items():
        afin_total = counts["won"] + counts["lost"]
        if afin_total > 0:
            afin_win_rate = counts["won"] / afin_total
            if afin_win_rate > 0.6:
                top_win_factors.append(f"High win rate for afinidad={afin} ({afin_win_rate:.0%})")
            elif afin_win_rate < 0.3 and afin_total >= 2:
                top_loss_factors.append(f"Low win rate for afinidad={afin} ({afin_win_rate:.0%})")

    # Region correlation
    for region, counts in by_region.items():
        reg_total = counts["won"] + counts["lost"]
        if reg_total > 0:
            reg_win_rate = counts["won"] / reg_total
            if reg_win_rate > 0.6:
                top_win_factors.append(f"Strong performance in {region} ({reg_win_rate:.0%} win rate)")
            elif reg_win_rate < 0.3 and reg_total >= 2:
                top_loss_factors.append(f"Weak performance in {region} ({reg_win_rate:.0%} win rate)")

    # Score correlation
    won_avg_score = (
        sum(l.score_icp for l in won_leads if l.score_icp is not None)
        / max(sum(1 for l in won_leads if l.score_icp is not None), 1)
    ) if won_leads else 0
    lost_avg_score = (
        sum(l.score_icp for l in lost_leads if l.score_icp is not None)
        / max(sum(1 for l in lost_leads if l.score_icp is not None), 1)
    ) if lost_leads else 0

    if won_avg_score > lost_avg_score + 10:
        top_win_factors.append(f"Higher ICP scores correlate with wins (avg {won_avg_score:.0f} vs {lost_avg_score:.0f})")

    if not top_win_factors:
        top_win_factors.append("Insufficient data to identify win factors")
    if not top_loss_factors:
        top_loss_factors.append("Insufficient data to identify loss factors")

    analysis = WinLossAnalysis(
        total_won=total_won,
        total_lost=total_lost,
        win_rate=round(win_rate, 1),
        avg_days_to_win=avg_days_to_win,
        avg_days_to_loss=avg_days_to_loss,
        top_win_factors=top_win_factors,
        top_loss_factors=top_loss_factors,
        by_region=by_region,
        by_afinidad=by_afinidad,
    )

    logger.info(
        "Win/loss analysis: won=%d lost=%d win_rate=%.1f%%",
        total_won,
        total_lost,
        win_rate,
    )
    return analysis
