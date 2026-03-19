"""Advanced support analytics — reports, agent performance, and SLA compliance."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Ticket, TicketMessage, TicketPriority, TicketStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AgentStats:
    """Performance statistics for a single agent."""

    tickets_handled: int = 0
    tickets_resolved: int = 0
    avg_resolution_hours: float | None = None
    sla_met: int = 0
    sla_breached: int = 0
    sla_compliance: float = 0.0


@dataclass
class SupportReport:
    """Comprehensive support report for a given period."""

    period: str
    total_tickets: int = 0
    resolution_rate: float = 0.0
    avg_resolution_hours: float | None = None
    sla_compliance_rate: float = 0.0
    tickets_by_category: dict[str, int] = field(default_factory=dict)
    tickets_by_priority: dict[str, int] = field(default_factory=dict)
    busiest_hours: dict[int, int] = field(default_factory=dict)
    escalation_count: int = 0
    agent_performance: dict[str, AgentStats] = field(default_factory=dict)


@dataclass
class AgentPerformance:
    """Detailed per-agent performance summary."""

    agent: str
    tickets_handled: int = 0
    avg_resolution_time: float | None = None
    sla_compliance: float = 0.0
    tickets_resolved: int = 0
    sla_met: int = 0
    sla_breached: int = 0


@dataclass
class SLACategoryBreakdown:
    """SLA compliance breakdown for a single category or priority."""

    label: str
    total: int = 0
    met: int = 0
    breached: int = 0
    compliance_rate: float = 0.0


@dataclass
class SLAReport:
    """SLA compliance report with breakdowns by category and priority."""

    total_tickets: int = 0
    total_met: int = 0
    total_breached: int = 0
    overall_compliance_rate: float = 0.0
    by_category: list[SLACategoryBreakdown] = field(default_factory=list)
    by_priority: list[SLACategoryBreakdown] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _compute_resolution_hours(created_at: datetime, resolved_at: datetime) -> float:
    """Compute resolution time in hours between two datetime values."""
    delta = resolved_at - created_at
    return delta.total_seconds() / 3600


def _sla_is_met(ticket_created: datetime, ticket_resolved: datetime | None, sla_deadline: datetime | None) -> bool | None:
    """Determine if SLA was met for a ticket.

    Returns True if met, False if breached, None if not applicable (no deadline or unresolved).
    """
    if sla_deadline is None:
        return None
    if ticket_resolved is not None:
        return ticket_resolved <= sla_deadline
    # Not resolved yet -- check if deadline has passed
    now = datetime.now(tz=None)
    if now > sla_deadline:
        return False
    return None  # Still within SLA, not yet resolved


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------


async def generate_support_report(
    db: AsyncSession, period_days: int = 30
) -> SupportReport:
    """Generate a comprehensive support report for the given period.

    Args:
        db: Async database session.
        period_days: Number of days to look back.

    Returns:
        A fully populated ``SupportReport``.
    """
    cutoff = datetime.now(tz=None) - timedelta(days=period_days)
    period_label = f"last_{period_days}_days"

    # Total tickets in period
    total_tickets = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.created_at >= cutoff)
    ) or 0

    # Resolved tickets in period
    resolved_count = await db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.created_at >= cutoff,
            Ticket.resolved_at.isnot(None),
        )
    ) or 0

    resolution_rate = (resolved_count / total_tickets * 100) if total_tickets > 0 else 0.0

    # Avg resolution time for tickets in period
    resolved_q = await db.execute(
        select(Ticket.created_at, Ticket.resolved_at).where(
            Ticket.created_at >= cutoff,
            Ticket.resolved_at.isnot(None),
        )
    )
    resolution_hours_list: list[float] = []
    for row in resolved_q:
        if row[0] and row[1]:
            hours = _compute_resolution_hours(row[0], row[1])
            resolution_hours_list.append(hours)
    avg_resolution_hours = (
        round(sum(resolution_hours_list) / len(resolution_hours_list), 1)
        if resolution_hours_list
        else None
    )

    # SLA compliance for tickets in period
    sla_q = await db.execute(
        select(Ticket).where(
            Ticket.created_at >= cutoff,
            Ticket.sla_deadline.isnot(None),
        )
    )
    sla_met = 0
    sla_total = 0
    for ticket in sla_q.scalars().all():
        result = _sla_is_met(ticket.created_at, ticket.resolved_at, ticket.sla_deadline)
        if result is not None:
            sla_total += 1
            if result:
                sla_met += 1
    sla_compliance_rate = (sla_met / sla_total * 100) if sla_total > 0 else 0.0

    # Tickets by category
    cat_q = await db.execute(
        select(Ticket.category, func.count(Ticket.id))
        .where(Ticket.created_at >= cutoff, Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    tickets_by_category = {str(row[0]): row[1] for row in cat_q}

    # Tickets by priority
    prio_q = await db.execute(
        select(Ticket.priority, func.count(Ticket.id))
        .where(Ticket.created_at >= cutoff)
        .group_by(Ticket.priority)
    )
    tickets_by_priority: dict[str, int] = {}
    for row in prio_q:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        tickets_by_priority[key] = row[1]

    # Busiest hours (based on created_at hour)
    all_tickets_q = await db.execute(
        select(Ticket.created_at).where(Ticket.created_at >= cutoff)
    )
    hour_counts: dict[int, int] = defaultdict(int)
    for row in all_tickets_q:
        if row[0]:
            hour_counts[row[0].hour] += 1
    busiest_hours = dict(sorted(hour_counts.items()))

    # Escalation count: tickets with >= 3 customer messages without resolution
    open_tickets_q = await db.execute(
        select(Ticket).where(
            Ticket.created_at >= cutoff,
            Ticket.status.in_([TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]),
        )
    )
    escalation_count = 0
    for ticket in open_tickets_q.scalars().all():
        msg_count = await db.scalar(
            select(func.count(TicketMessage.id)).where(
                TicketMessage.ticket_id == ticket.id,
                TicketMessage.sender == "customer",
            )
        ) or 0
        if msg_count >= 3:
            escalation_count += 1

    # Agent performance
    agent_q = await db.execute(
        select(Ticket).where(
            Ticket.created_at >= cutoff,
            Ticket.assigned_agent.isnot(None),
        )
    )
    agent_data: dict[str, dict] = {}
    for ticket in agent_q.scalars().all():
        agent = str(ticket.assigned_agent)
        if agent not in agent_data:
            agent_data[agent] = {
                "tickets_handled": 0,
                "tickets_resolved": 0,
                "resolution_hours": [],
                "sla_met": 0,
                "sla_breached": 0,
            }
        agent_data[agent]["tickets_handled"] += 1
        if ticket.resolved_at is not None:
            agent_data[agent]["tickets_resolved"] += 1
            hours = _compute_resolution_hours(ticket.created_at, ticket.resolved_at)
            agent_data[agent]["resolution_hours"].append(hours)
        if ticket.sla_deadline is not None:
            sla_result = _sla_is_met(ticket.created_at, ticket.resolved_at, ticket.sla_deadline)
            if sla_result is True:
                agent_data[agent]["sla_met"] += 1
            elif sla_result is False:
                agent_data[agent]["sla_breached"] += 1

    agent_performance: dict[str, AgentStats] = {}
    for agent, data in agent_data.items():
        hours_list = data["resolution_hours"]
        avg_hours = round(sum(hours_list) / len(hours_list), 1) if hours_list else None
        total_sla = data["sla_met"] + data["sla_breached"]
        compliance = (data["sla_met"] / total_sla * 100) if total_sla > 0 else 0.0
        agent_performance[agent] = AgentStats(
            tickets_handled=data["tickets_handled"],
            tickets_resolved=data["tickets_resolved"],
            avg_resolution_hours=avg_hours,
            sla_met=data["sla_met"],
            sla_breached=data["sla_breached"],
            sla_compliance=round(compliance, 1),
        )

    return SupportReport(
        period=period_label,
        total_tickets=total_tickets,
        resolution_rate=round(resolution_rate, 1),
        avg_resolution_hours=avg_resolution_hours,
        sla_compliance_rate=round(sla_compliance_rate, 1),
        tickets_by_category=tickets_by_category,
        tickets_by_priority=tickets_by_priority,
        busiest_hours=busiest_hours,
        escalation_count=escalation_count,
        agent_performance=agent_performance,
    )


async def generate_agent_performance(db: AsyncSession) -> list[AgentPerformance]:
    """Generate per-agent performance summaries across all tickets.

    Args:
        db: Async database session.

    Returns:
        A list of ``AgentPerformance`` entries, one per agent.
    """
    agent_q = await db.execute(
        select(Ticket).where(Ticket.assigned_agent.isnot(None))
    )

    agent_data: dict[str, dict] = {}
    for ticket in agent_q.scalars().all():
        agent = str(ticket.assigned_agent)
        if agent not in agent_data:
            agent_data[agent] = {
                "tickets_handled": 0,
                "tickets_resolved": 0,
                "resolution_hours": [],
                "sla_met": 0,
                "sla_breached": 0,
            }
        agent_data[agent]["tickets_handled"] += 1
        if ticket.resolved_at is not None:
            agent_data[agent]["tickets_resolved"] += 1
            hours = _compute_resolution_hours(ticket.created_at, ticket.resolved_at)
            agent_data[agent]["resolution_hours"].append(hours)
        if ticket.sla_deadline is not None:
            sla_result = _sla_is_met(ticket.created_at, ticket.resolved_at, ticket.sla_deadline)
            if sla_result is True:
                agent_data[agent]["sla_met"] += 1
            elif sla_result is False:
                agent_data[agent]["sla_breached"] += 1

    results: list[AgentPerformance] = []
    for agent, data in sorted(agent_data.items()):
        hours_list = data["resolution_hours"]
        avg_time = round(sum(hours_list) / len(hours_list), 1) if hours_list else None
        total_sla = data["sla_met"] + data["sla_breached"]
        compliance = (data["sla_met"] / total_sla * 100) if total_sla > 0 else 0.0
        results.append(
            AgentPerformance(
                agent=agent,
                tickets_handled=data["tickets_handled"],
                avg_resolution_time=avg_time,
                sla_compliance=round(compliance, 1),
                tickets_resolved=data["tickets_resolved"],
                sla_met=data["sla_met"],
                sla_breached=data["sla_breached"],
            )
        )

    return results


async def generate_sla_compliance_report(db: AsyncSession) -> SLAReport:
    """Generate an SLA compliance report with breakdowns by category and priority.

    Args:
        db: Async database session.

    Returns:
        An ``SLAReport`` with overall and per-category/priority compliance.
    """
    # Fetch all tickets with SLA deadlines
    tickets_q = await db.execute(
        select(Ticket).where(Ticket.sla_deadline.isnot(None))
    )

    total_met = 0
    total_breached = 0
    total_assessed = 0

    category_data: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "met": 0, "breached": 0})
    priority_data: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "met": 0, "breached": 0})

    for ticket in tickets_q.scalars().all():
        sla_result = _sla_is_met(ticket.created_at, ticket.resolved_at, ticket.sla_deadline)
        if sla_result is None:
            continue

        total_assessed += 1
        is_met = sla_result is True

        if is_met:
            total_met += 1
        else:
            total_breached += 1

        # Category breakdown
        cat_key = str(ticket.category) if ticket.category else "uncategorized"
        category_data[cat_key]["total"] += 1
        if is_met:
            category_data[cat_key]["met"] += 1
        else:
            category_data[cat_key]["breached"] += 1

        # Priority breakdown
        prio_key = ticket.priority.value if hasattr(ticket.priority, "value") else str(ticket.priority)
        priority_data[prio_key]["total"] += 1
        if is_met:
            priority_data[prio_key]["met"] += 1
        else:
            priority_data[prio_key]["breached"] += 1

    overall_compliance = (total_met / total_assessed * 100) if total_assessed > 0 else 0.0

    by_category = [
        SLACategoryBreakdown(
            label=cat,
            total=data["total"],
            met=data["met"],
            breached=data["breached"],
            compliance_rate=round(data["met"] / data["total"] * 100, 1) if data["total"] > 0 else 0.0,
        )
        for cat, data in sorted(category_data.items())
    ]

    by_priority = [
        SLACategoryBreakdown(
            label=prio,
            total=data["total"],
            met=data["met"],
            breached=data["breached"],
            compliance_rate=round(data["met"] / data["total"] * 100, 1) if data["total"] > 0 else 0.0,
        )
        for prio, data in sorted(priority_data.items())
    ]

    return SLAReport(
        total_tickets=total_assessed,
        total_met=total_met,
        total_breached=total_breached,
        overall_compliance_rate=round(overall_compliance, 1),
        by_category=by_category,
        by_priority=by_priority,
    )
