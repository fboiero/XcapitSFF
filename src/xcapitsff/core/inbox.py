"""Smart Inbox — unified view of all pending actions for each user/tenant.

Scans all modules (leads, tickets, outreach, SLA) and generates prioritised
action items so the user always knows what needs attention right now.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import (
    Lead,
    LeadStage,
    OutreachMessage,
    Ticket,
    TicketPriority,
    TicketStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InboxItemType(str, Enum):
    """Types of actionable inbox items."""

    LEAD_HOT = "lead_hot"
    LEAD_STALE = "lead_stale"
    TICKET_URGENT = "ticket_urgent"
    TICKET_SLA_WARNING = "ticket_sla_warning"
    TICKET_UNASSIGNED = "ticket_unassigned"
    OUTREACH_PENDING = "outreach_pending"
    OUTREACH_REPLIED = "outreach_replied"
    APPROVAL_NEEDED = "approval_needed"
    TASK_DUE = "task_due"
    SYSTEM_ALERT = "system_alert"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class InboxItem:
    """A single actionable item in the Smart Inbox."""

    item_id: str
    type: InboxItemType
    title: str
    subtitle: str
    entity_type: str  # "lead", "ticket", "customer"
    entity_id: int
    priority: int  # 1 (highest) to 5 (lowest)
    action_url: str  # API endpoint to act on the item
    created_at: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    is_acted_on: bool = False


# ---------------------------------------------------------------------------
# Priority helpers
# ---------------------------------------------------------------------------

_TYPE_BASE_PRIORITY: dict[InboxItemType, int] = {
    InboxItemType.TICKET_URGENT: 1,
    InboxItemType.TICKET_SLA_WARNING: 1,
    InboxItemType.SYSTEM_ALERT: 1,
    InboxItemType.LEAD_HOT: 2,
    InboxItemType.OUTREACH_REPLIED: 2,
    InboxItemType.TICKET_UNASSIGNED: 2,
    InboxItemType.APPROVAL_NEEDED: 3,
    InboxItemType.OUTREACH_PENDING: 3,
    InboxItemType.TASK_DUE: 3,
    InboxItemType.LEAD_STALE: 4,
}


def _make_id() -> str:
    return str(uuid.uuid4())[:12]


# ---------------------------------------------------------------------------
# InboxManager
# ---------------------------------------------------------------------------


class InboxManager:
    """Generates and manages the Smart Inbox for a user / tenant."""

    def __init__(self) -> None:
        self._items: dict[str, InboxItem] = {}

    # -- Generation ---------------------------------------------------------

    async def generate_inbox(self, db: AsyncSession) -> list[InboxItem]:
        """Scan all modules and generate action items.

        Returns the full list sorted by priority (ascending = most urgent first).
        """
        self._items.clear()

        await self._scan_hot_leads(db)
        await self._scan_stale_leads(db)
        await self._scan_urgent_tickets(db)
        await self._scan_sla_warning_tickets(db)
        await self._scan_unassigned_tickets(db)
        await self._scan_outreach_pending(db)
        await self._scan_outreach_replied(db)
        await self._scan_sla_breaches(db)

        items = sorted(self._items.values(), key=lambda i: (i.priority, i.created_at))
        return items

    # -- Mutators -----------------------------------------------------------

    def mark_read(self, item_id: str) -> bool:
        """Mark an inbox item as read. Returns True if found."""
        item = self._items.get(item_id)
        if item is None:
            return False
        item.is_read = True
        return True

    def mark_acted(self, item_id: str) -> bool:
        """Mark an inbox item as acted upon. Returns True if found."""
        item = self._items.get(item_id)
        if item is None:
            return False
        item.is_acted_on = True
        item.is_read = True
        return True

    # -- Queries ------------------------------------------------------------

    def get_count_by_type(self) -> dict[str, int]:
        """Return count of inbox items grouped by type."""
        counts: dict[str, int] = {}
        for item in self._items.values():
            key = item.type.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def get_priority_items(self, max_items: int = 10) -> list[InboxItem]:
        """Return the top priority items (unacted), limited to *max_items*."""
        active = [i for i in self._items.values() if not i.is_acted_on]
        active.sort(key=lambda i: (i.priority, i.created_at))
        return active[:max_items]

    def get_items(self) -> list[InboxItem]:
        """Return all items sorted by priority."""
        return sorted(self._items.values(), key=lambda i: (i.priority, i.created_at))

    def get_item(self, item_id: str) -> InboxItem | None:
        return self._items.get(item_id)

    # -- Internal scanners --------------------------------------------------

    async def _scan_hot_leads(self, db: AsyncSession) -> None:
        """Hot leads not contacted in 7+ days."""
        cutoff = datetime.now(tz=None) - timedelta(days=7)
        result = await db.execute(
            select(Lead).where(
                Lead.score_icp >= 60,
                Lead.stage.in_([LeadStage.RAW.value, LeadStage.QUALIFIED.value]),
                Lead.updated_at < cutoff,
            )
        )
        for lead in result.scalars().all():
            item_id = _make_id()
            self._items[item_id] = InboxItem(
                item_id=item_id,
                type=InboxItemType.LEAD_HOT,
                title=f"Lead caliente sin contactar: {lead.company_name or 'Sin nombre'}",
                subtitle=f"Score {lead.score_icp} — sin actividad hace 7+ dias",
                entity_type="lead",
                entity_id=lead.id,
                priority=_TYPE_BASE_PRIORITY[InboxItemType.LEAD_HOT],
                action_url=f"/api/v1/leads/{lead.id}",
                created_at=lead.updated_at or datetime.now(),
            )

    async def _scan_stale_leads(self, db: AsyncSession) -> None:
        """Leads with no activity in 30+ days (not won/lost)."""
        cutoff = datetime.now(tz=None) - timedelta(days=30)
        result = await db.execute(
            select(Lead).where(
                Lead.updated_at < cutoff,
                Lead.stage.notin_([LeadStage.WON.value, LeadStage.LOST.value]),
            )
        )
        for lead in result.scalars().all():
            item_id = _make_id()
            self._items[item_id] = InboxItem(
                item_id=item_id,
                type=InboxItemType.LEAD_STALE,
                title=f"Lead inactivo: {lead.company_name or 'Sin nombre'}",
                subtitle=f"Sin actividad hace 30+ dias — etapa: {lead.stage.value if hasattr(lead.stage, 'value') else lead.stage}",
                entity_type="lead",
                entity_id=lead.id,
                priority=_TYPE_BASE_PRIORITY[InboxItemType.LEAD_STALE],
                action_url=f"/api/v1/leads/{lead.id}",
                created_at=lead.updated_at or datetime.now(),
            )

    async def _scan_urgent_tickets(self, db: AsyncSession) -> None:
        """Open tickets with urgent priority."""
        open_statuses = [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]
        result = await db.execute(
            select(Ticket).where(
                Ticket.status.in_(open_statuses),
                Ticket.priority == TicketPriority.URGENT.value,
            )
        )
        for ticket in result.scalars().all():
            item_id = _make_id()
            self._items[item_id] = InboxItem(
                item_id=item_id,
                type=InboxItemType.TICKET_URGENT,
                title=f"Ticket urgente: {ticket.subject}",
                subtitle=f"Prioridad URGENTE — estado: {ticket.status.value if hasattr(ticket.status, 'value') else ticket.status}",
                entity_type="ticket",
                entity_id=ticket.id,
                priority=_TYPE_BASE_PRIORITY[InboxItemType.TICKET_URGENT],
                action_url=f"/api/v1/tickets/{ticket.id}",
                created_at=ticket.created_at,
            )

    async def _scan_sla_warning_tickets(self, db: AsyncSession) -> None:
        """Tickets approaching SLA breach (80%+ of SLA time consumed)."""
        now = datetime.now(tz=None)
        open_statuses = [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]
        result = await db.execute(
            select(Ticket).where(
                Ticket.status.in_(open_statuses),
                Ticket.sla_deadline.isnot(None),
            )
        )
        for ticket in result.scalars().all():
            if not ticket.sla_deadline:
                continue
            total_sla_seconds = (ticket.sla_deadline - ticket.created_at).total_seconds()
            if total_sla_seconds <= 0:
                continue
            elapsed = (now - ticket.created_at).total_seconds()
            pct_consumed = elapsed / total_sla_seconds

            if pct_consumed >= 0.8 and now < ticket.sla_deadline:
                remaining_hours = (ticket.sla_deadline - now).total_seconds() / 3600
                item_id = _make_id()
                self._items[item_id] = InboxItem(
                    item_id=item_id,
                    type=InboxItemType.TICKET_SLA_WARNING,
                    title=f"SLA en riesgo: {ticket.subject}",
                    subtitle=f"{pct_consumed * 100:.0f}% del SLA consumido — quedan {remaining_hours:.1f}h",
                    entity_type="ticket",
                    entity_id=ticket.id,
                    priority=_TYPE_BASE_PRIORITY[InboxItemType.TICKET_SLA_WARNING],
                    action_url=f"/api/v1/tickets/{ticket.id}",
                    created_at=ticket.created_at,
                )

    async def _scan_unassigned_tickets(self, db: AsyncSession) -> None:
        """Open tickets with no assigned agent."""
        open_statuses = [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]
        result = await db.execute(
            select(Ticket).where(
                Ticket.status.in_(open_statuses),
                (Ticket.assigned_agent.is_(None)) | (Ticket.assigned_agent == ""),
            )
        )
        for ticket in result.scalars().all():
            item_id = _make_id()
            self._items[item_id] = InboxItem(
                item_id=item_id,
                type=InboxItemType.TICKET_UNASSIGNED,
                title=f"Ticket sin asignar: {ticket.subject}",
                subtitle=f"Prioridad: {ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority}",
                entity_type="ticket",
                entity_id=ticket.id,
                priority=_TYPE_BASE_PRIORITY[InboxItemType.TICKET_UNASSIGNED],
                action_url=f"/api/v1/tickets/{ticket.id}",
                created_at=ticket.created_at,
            )

    async def _scan_outreach_pending(self, db: AsyncSession) -> None:
        """Outreach messages in draft status (pending send)."""
        result = await db.execute(
            select(OutreachMessage).where(OutreachMessage.status == "draft")
        )
        for msg in result.scalars().all():
            item_id = _make_id()
            self._items[item_id] = InboxItem(
                item_id=item_id,
                type=InboxItemType.OUTREACH_PENDING,
                title=f"Outreach pendiente: {msg.subject or msg.channel}",
                subtitle=f"Canal: {msg.channel} — lead #{msg.lead_id}",
                entity_type="lead",
                entity_id=msg.lead_id,
                priority=_TYPE_BASE_PRIORITY[InboxItemType.OUTREACH_PENDING],
                action_url=f"/api/v1/leads/{msg.lead_id}",
                created_at=msg.created_at,
            )

    async def _scan_outreach_replied(self, db: AsyncSession) -> None:
        """Outreach messages that received a reply (need follow-up)."""
        result = await db.execute(
            select(OutreachMessage).where(OutreachMessage.status == "replied")
        )
        for msg in result.scalars().all():
            item_id = _make_id()
            self._items[item_id] = InboxItem(
                item_id=item_id,
                type=InboxItemType.OUTREACH_REPLIED,
                title=f"Respuesta recibida: {msg.subject or msg.channel}",
                subtitle=f"Lead #{msg.lead_id} respondio — requiere follow-up",
                entity_type="lead",
                entity_id=msg.lead_id,
                priority=_TYPE_BASE_PRIORITY[InboxItemType.OUTREACH_REPLIED],
                action_url=f"/api/v1/leads/{msg.lead_id}",
                created_at=msg.created_at,
            )

    async def _scan_sla_breaches(self, db: AsyncSession) -> None:
        """Tickets that have already breached their SLA (system alerts)."""
        now = datetime.now(tz=None)
        open_statuses = [TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value]
        result = await db.execute(
            select(Ticket).where(
                Ticket.status.in_(open_statuses),
                Ticket.sla_deadline.isnot(None),
                Ticket.sla_deadline < now,
            )
        )
        for ticket in result.scalars().all():
            overdue_hours = (now - ticket.sla_deadline).total_seconds() / 3600
            item_id = _make_id()
            self._items[item_id] = InboxItem(
                item_id=item_id,
                type=InboxItemType.SYSTEM_ALERT,
                title=f"SLA incumplido: {ticket.subject}",
                subtitle=f"Vencido hace {overdue_hours:.1f}h",
                entity_type="ticket",
                entity_id=ticket.id,
                priority=_TYPE_BASE_PRIORITY[InboxItemType.SYSTEM_ALERT],
                action_url=f"/api/v1/tickets/{ticket.id}",
                created_at=ticket.created_at,
            )
