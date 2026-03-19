"""SLA Monitor — periodic check for breached SLAs and escalation triggers.

This module provides functions to scan tickets for SLA breaches and
generate escalation actions. In production, this would be called by
a periodic task (cron, celery beat, or similar).
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.events import Event, EventType, event_bus
from xcapitsff.core.models import Ticket, TicketStatus
from xcapitsff.support.router import should_escalate
from xcapitsff.support.tickets import get_ticket_messages

logger = logging.getLogger(__name__)


@dataclass
class SLACheckResult:
    checked_at: datetime = field(default_factory=datetime.now)
    total_open: int = 0
    breached: int = 0
    approaching_breach: int = 0
    escalated: int = 0
    details: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"SLA Check at {self.checked_at.isoformat()}: "
            f"{self.total_open} open, {self.breached} breached, "
            f"{self.approaching_breach} approaching, {self.escalated} escalated"
        )


async def check_sla_compliance(db: AsyncSession) -> SLACheckResult:
    """Scan all open tickets and check SLA compliance.

    Returns a SLACheckResult with counts and details of problematic tickets.
    Emits events for breached and escalated tickets.
    """
    result = SLACheckResult()
    now = datetime.now(tz=None)

    open_statuses = [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]
    query = select(Ticket).where(Ticket.status.in_(open_statuses))
    tickets_result = await db.execute(query)
    open_tickets = list(tickets_result.scalars().all())
    result.total_open = len(open_tickets)

    for ticket in open_tickets:
        if not ticket.sla_deadline:
            continue

        age_hours = (now - ticket.created_at).total_seconds() / 3600
        sla_hours = (ticket.sla_deadline - ticket.created_at).total_seconds() / 3600

        # Get message count for escalation check
        messages = await get_ticket_messages(db, ticket.id)
        customer_msgs = len([m for m in messages if m.sender == "customer"])

        priority_str = ticket.priority if isinstance(ticket.priority, str) else ticket.priority.value
        from xcapitsff.core.schemas import TicketPriorityEnum
        priority_map = {
            "low": TicketPriorityEnum.LOW,
            "medium": TicketPriorityEnum.MEDIUM,
            "high": TicketPriorityEnum.HIGH,
            "urgent": TicketPriorityEnum.URGENT,
        }
        priority_enum = priority_map.get(priority_str, TicketPriorityEnum.MEDIUM)

        # Check if breached
        if now > ticket.sla_deadline:
            result.breached += 1
            result.details.append({
                "ticket_id": ticket.id,
                "status": "breached",
                "priority": priority_str,
                "age_hours": round(age_hours, 1),
                "sla_hours": round(sla_hours, 1),
                "overdue_hours": round(age_hours - sla_hours, 1),
            })
            await event_bus.emit(Event(
                type=EventType.TICKET_SLA_BREACHED,
                data={"ticket_id": ticket.id, "overdue_hours": round(age_hours - sla_hours, 1)},
                source="sla_monitor",
            ))

        # Check if approaching breach (>80% of SLA consumed)
        elif age_hours >= sla_hours * 0.8:
            result.approaching_breach += 1
            result.details.append({
                "ticket_id": ticket.id,
                "status": "approaching",
                "priority": priority_str,
                "age_hours": round(age_hours, 1),
                "sla_hours": round(sla_hours, 1),
                "remaining_hours": round(sla_hours - age_hours, 1),
            })

        # Check if needs escalation
        if should_escalate(age_hours, priority_enum, sla_hours, customer_msgs):
            result.escalated += 1
            await event_bus.emit(Event(
                type=EventType.TICKET_ESCALATED,
                data={
                    "ticket_id": ticket.id,
                    "reason": "sla_monitor_escalation",
                    "age_hours": round(age_hours, 1),
                    "customer_messages": customer_msgs,
                },
                source="sla_monitor",
            ))

    logger.info(result.summary())
    return result


async def get_sla_dashboard(db: AsyncSession) -> dict:
    """Get a dashboard view of current SLA status."""
    check = await check_sla_compliance(db)

    return {
        "checked_at": check.checked_at.isoformat(),
        "summary": {
            "total_open": check.total_open,
            "breached": check.breached,
            "approaching_breach": check.approaching_breach,
            "escalated": check.escalated,
            "compliance_rate": round(
                (1 - check.breached / check.total_open) * 100, 1
            ) if check.total_open > 0 else 100.0,
        },
        "breached_tickets": [
            d for d in check.details if d["status"] == "breached"
        ],
        "approaching_tickets": [
            d for d in check.details if d["status"] == "approaching"
        ],
    }
