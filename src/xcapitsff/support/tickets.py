"""Ticket management — CRUD, routing, SLA tracking, escalation."""

import logging
from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import (
    Customer,
    Ticket,
    TicketMessage,
    TicketPriority,
    TicketStatus,
)
from xcapitsff.core.schemas import (
    SupportStats,
    TicketCreate,
    TicketMessageCreate,
    TicketUpdate,
)

logger = logging.getLogger(__name__)

# SLA deadlines by priority (in hours)
SLA_HOURS: dict[str, int] = {
    "urgent": 4,
    "high": 8,
    "medium": 24,
    "low": 72,
}

# VIP discount
VIP_SLA_MULTIPLIER = 0.5


def get_sla_hours(priority: str, is_vip: bool = False) -> int:
    base = SLA_HOURS.get(priority, 24)
    if is_vip:
        return max(int(base * VIP_SLA_MULTIPLIER), 1)
    return base


async def create_ticket(db: AsyncSession, data: TicketCreate) -> Ticket:
    priority_val = data.priority.value
    sla_hours = get_sla_hours(priority_val)
    sla_deadline = datetime.now(tz=None) + timedelta(hours=sla_hours)

    ticket = Ticket(
        customer_id=data.customer_id,
        subject=data.subject,
        description=data.description,
        priority=priority_val,
        category=data.category,
        sla_deadline=sla_deadline,
    )
    db.add(ticket)
    await db.flush()
    await db.refresh(ticket)
    logger.info(f"Ticket created: id={ticket.id} priority={priority_val} sla={sla_hours}h")
    return ticket


async def get_tickets(
    db: AsyncSession,
    status: str | None = None,
    priority: str | None = None,
    customer_id: int | None = None,
    assigned_agent: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Ticket]:
    query = select(Ticket)

    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)
    if customer_id:
        query = query.where(Ticket.customer_id == customer_id)
    if assigned_agent:
        query = query.where(Ticket.assigned_agent == assigned_agent)

    query = query.order_by(Ticket.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_ticket(db: AsyncSession, ticket_id: int) -> Ticket | None:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    return result.scalar_one_or_none()


async def update_ticket(db: AsyncSession, ticket_id: int, data: TicketUpdate) -> Ticket | None:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    update_data = data.model_dump(exclude_unset=True)

    if "status" in update_data:
        new_status = update_data["status"]
        if new_status in (TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value):
            ticket.resolved_at = datetime.now(tz=None)
            logger.info(f"Ticket {ticket_id} resolved")

    for field, value in update_data.items():
        setattr(ticket, field, value)

    await db.flush()
    await db.refresh(ticket)
    return ticket


async def add_message(
    db: AsyncSession,
    ticket_id: int,
    data: TicketMessageCreate,
    generated_by: str | None = None,
) -> TicketMessage:
    msg = TicketMessage(
        ticket_id=ticket_id,
        sender=data.sender,
        content=data.content,
        generated_by=generated_by,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)

    # Auto-update ticket status if agent responds
    if data.sender == "agent":
        ticket = await get_ticket(db, ticket_id)
        if ticket and ticket.status == TicketStatus.OPEN.value:
            ticket.status = TicketStatus.IN_PROGRESS.value
            await db.flush()

    return msg


async def get_ticket_messages(db: AsyncSession, ticket_id: int) -> list[TicketMessage]:
    result = await db.execute(
        select(TicketMessage)
        .where(TicketMessage.ticket_id == ticket_id)
        .order_by(TicketMessage.created_at)
    )
    return list(result.scalars().all())


async def get_overdue_tickets(db: AsyncSession) -> list[Ticket]:
    """Get tickets that have exceeded their SLA deadline."""
    now = datetime.now(tz=None)
    result = await db.execute(
        select(Ticket)
        .where(
            Ticket.sla_deadline < now,
            Ticket.resolved_at.is_(None),
            Ticket.status.notin_([TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value]),
        )
        .order_by(Ticket.sla_deadline.asc())
    )
    return list(result.scalars().all())


async def get_tickets_needing_escalation(
    db: AsyncSession, max_messages_without_resolution: int = 3
) -> list[Ticket]:
    """Get tickets that need escalation based on customer message count without resolution."""
    result = await db.execute(
        select(Ticket)
        .where(
            Ticket.status.in_([TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]),
        )
    )
    tickets_to_escalate = []
    for ticket in result.scalars().all():
        msgs = await get_ticket_messages(db, ticket.id)
        customer_msgs = [m for m in msgs if m.sender == "customer"]
        if len(customer_msgs) >= max_messages_without_resolution:
            tickets_to_escalate.append(ticket)
    return tickets_to_escalate


async def create_customer(db: AsyncSession, company_name: str, contact_name: str, contact_email: str, region: str = "LATAM") -> Customer:
    customer = Customer(
        company_name=company_name,
        contact_name=contact_name,
        contact_email=contact_email,
        region=region,
    )
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    return customer


async def get_customer(db: AsyncSession, customer_id: int) -> Customer | None:
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    return result.scalar_one_or_none()


async def get_customers(db: AsyncSession, limit: int = 100, offset: int = 0) -> list[Customer]:
    result = await db.execute(
        select(Customer).order_by(Customer.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def get_support_stats(db: AsyncSession) -> SupportStats:
    total = await db.scalar(select(func.count(Ticket.id))) or 0

    open_count = await db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.status.in_([TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value])
        )
    ) or 0

    # Avg resolution time (SQLite-compatible: use julianday)
    resolved_tickets = await db.execute(
        select(Ticket.created_at, Ticket.resolved_at).where(Ticket.resolved_at.isnot(None))
    )
    resolution_hours = []
    for row in resolved_tickets:
        if row[0] and row[1]:
            delta = row[1] - row[0]
            resolution_hours.append(delta.total_seconds() / 3600)
    avg_hours = sum(resolution_hours) / len(resolution_hours) if resolution_hours else None

    # By priority
    prio_q = await db.execute(
        select(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority)
    )
    by_priority = {str(row[0]): row[1] for row in prio_q}

    # By status
    status_q = await db.execute(
        select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)
    )
    by_status = {str(row[0]): row[1] for row in status_q}

    # By category
    cat_q = await db.execute(
        select(Ticket.category, func.count(Ticket.id))
        .where(Ticket.category.isnot(None))
        .group_by(Ticket.category)
    )
    by_category = {str(row[0]): row[1] for row in cat_q}

    return SupportStats(
        total_tickets=total,
        open_tickets=open_count,
        avg_resolution_hours=round(avg_hours, 1) if avg_hours else None,
        by_priority=by_priority,
        by_status=by_status,
        by_category=by_category,
    )
