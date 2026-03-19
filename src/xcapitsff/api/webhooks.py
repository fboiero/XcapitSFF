"""Webhook API — receive external events and emit internal events.

Supports inbound webhooks from:
- CRM systems (new lead, lead updated)
- Support platforms (new ticket via external form)
- Payment processors (subscription events)
- Custom integrations
"""

import hashlib
import hmac
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.config import settings
from xcapitsff.core.database import get_db
from xcapitsff.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookPayload(BaseModel):
    event: str
    data: dict
    timestamp: str | None = None
    source: str = "external"


class LeadWebhook(BaseModel):
    company_name: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    region: str = "LATAM"
    c_level: bool = False
    score_icp: float | None = None
    afinidad: str = "MEDIUM"
    source: str = "webhook"


class TicketWebhook(BaseModel):
    customer_email: str
    subject: str
    description: str
    priority: str = "medium"
    source: str = "webhook"


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 webhook signature."""
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/generic")
async def receive_generic_webhook(
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """Receive a generic webhook and emit the appropriate internal event."""
    event_map = {
        "lead.created": EventType.LEAD_CREATED,
        "lead.updated": EventType.LEAD_UPDATED,
        "ticket.created": EventType.TICKET_CREATED,
        "ticket.resolved": EventType.TICKET_RESOLVED,
        "outreach.replied": EventType.OUTREACH_REPLIED,
        "customer.created": EventType.CUSTOMER_CREATED,
    }

    event_type = event_map.get(payload.event)
    if not event_type:
        raise HTTPException(status_code=400, detail=f"Unknown event type: {payload.event}")

    event = Event(
        type=event_type,
        data=payload.data,
        source=payload.source,
    )
    await event_bus.emit(event)

    return {"status": "accepted", "event_id": event.event_id}


@router.post("/leads")
async def receive_lead_webhook(
    lead: LeadWebhook,
    db: AsyncSession = Depends(get_db),
):
    """Receive a new lead from an external source (website form, CRM, etc.)."""
    from xcapitsff.core.schemas import LeadCreate, RegionEnum, AfinidadEnum
    from xcapitsff.sales.pipeline import create_lead

    region = RegionEnum.LATAM if lead.region.upper() == "LATAM" else RegionEnum.IBERIA
    afinidad_map = {"HIGH": AfinidadEnum.HIGH, "MEDIUM": AfinidadEnum.MEDIUM, "LOW": AfinidadEnum.LOW}
    afinidad = afinidad_map.get(lead.afinidad.upper(), AfinidadEnum.MEDIUM)

    lead_data = LeadCreate(
        company_name=lead.company_name,
        contact_name=lead.contact_name,
        contact_email=lead.contact_email,
        region=region,
        c_level=lead.c_level,
        score_icp=lead.score_icp,
        afinidad=afinidad,
        notes=f"Source: {lead.source}",
    )

    new_lead = await create_lead(db, lead_data)

    await event_bus.emit(Event(
        type=EventType.LEAD_CREATED,
        data={
            "lead_id": new_lead.id,
            "score": new_lead.score_icp,
            "region": lead.region,
            "c_level": lead.c_level,
            "source": lead.source,
        },
        source="webhook",
    ))

    return {
        "status": "created",
        "lead_id": new_lead.id,
        "score_icp": new_lead.score_icp,
    }


@router.post("/tickets")
async def receive_ticket_webhook(
    ticket: TicketWebhook,
    db: AsyncSession = Depends(get_db),
):
    """Receive a new ticket from an external source (support form, email, etc.)."""
    from xcapitsff.core.schemas import TicketCreate, TicketPriorityEnum
    from xcapitsff.support.router import full_route
    from xcapitsff.support.tickets import create_ticket, get_customer

    # Try to find or create customer
    from sqlalchemy import select
    from xcapitsff.core.models import Customer
    result = await db.execute(
        select(Customer).where(Customer.contact_email == ticket.customer_email)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        from xcapitsff.support.tickets import create_customer
        customer = await create_customer(
            db,
            company_name="Unknown",
            contact_name=ticket.customer_email.split("@")[0],
            contact_email=ticket.customer_email,
        )

    # Route the ticket
    routing = full_route(ticket.subject, ticket.description)

    priority_map = {
        "low": TicketPriorityEnum.LOW,
        "medium": TicketPriorityEnum.MEDIUM,
        "high": TicketPriorityEnum.HIGH,
        "urgent": TicketPriorityEnum.URGENT,
    }

    ticket_data = TicketCreate(
        customer_id=customer.id,
        subject=ticket.subject,
        description=ticket.description,
        priority=routing.priority,
        category=routing.category,
    )

    new_ticket = await create_ticket(db, ticket_data)
    new_ticket.assigned_agent = routing.assigned_agent
    await db.flush()

    await event_bus.emit(Event(
        type=EventType.TICKET_CREATED,
        data={
            "ticket_id": new_ticket.id,
            "category": routing.category,
            "priority": routing.priority.value,
            "assigned_agent": routing.assigned_agent,
            "requires_human_review": routing.requires_human_review,
            "flags": routing.flags,
            "source": ticket.source,
        },
        source="webhook",
    ))

    return {
        "status": "created",
        "ticket_id": new_ticket.id,
        "category": routing.category,
        "priority": routing.priority.value,
        "assigned_agent": routing.assigned_agent,
        "sla_hours": routing.sla_hours,
        "flags": routing.flags,
    }


@router.get("/events")
async def get_recent_events(limit: int = 50):
    """Get recent events from the event bus (for debugging/monitoring)."""
    events = event_bus.get_recent_events(limit)
    return {
        "count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "type": e.type.value,
                "source": e.source,
                "timestamp": e.timestamp.isoformat(),
                "data": e.data,
            }
            for e in events
        ],
    }


@router.get("/events/stats")
async def get_event_stats():
    """Get event count statistics."""
    return event_bus.get_event_counts()
