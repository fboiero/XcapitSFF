"""API endpoints for Outreach management — compose, send, track."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.events import Event, EventType, event_bus
from xcapitsff.core.models import Lead, OutreachMessage
from xcapitsff.sales.outreach import (
    Channel,
    compose_batch,
    compose_message,
    generate_ab_variants,
    get_followup_sequence,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/outreach", tags=["Outreach"])


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "contact_name": lead.contact_name,
        "company_name": lead.company_name,
        "contact_email": lead.contact_email,
        "region": lead.region if isinstance(lead.region, str) else lead.region.value,
        "c_level": lead.c_level,
        "score_icp": lead.score_icp,
        "afinidad": lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
    }


@router.post("/compose/{lead_id}")
async def api_compose_outreach(
    lead_id: int,
    channel: str = Query(default="email"),
    db: AsyncSession = Depends(get_db),
):
    """Compose an outreach message for a specific lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = _lead_to_dict(lead)
    draft = compose_message(lead_data, channel)

    return {
        "lead_id": lead_id,
        "channel": draft.channel.value,
        "subject": draft.subject,
        "body": draft.body,
        "template_used": draft.template_used,
        "personalization_score": draft.personalization_score,
    }


@router.post("/ab-test/{lead_id}")
async def api_ab_variants(
    lead_id: int,
    channel: str = Query(default="email"),
    db: AsyncSession = Depends(get_db),
):
    """Generate A/B test variants for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = _lead_to_dict(lead)
    variant_a, variant_b = generate_ab_variants(lead_data, channel)

    return {
        "lead_id": lead_id,
        "variant_a": {
            "subject": variant_a.subject,
            "body": variant_a.body,
            "template": variant_a.template_used,
        },
        "variant_b": {
            "subject": variant_b.subject,
            "body": variant_b.body,
            "template": variant_b.template_used,
        },
    }


@router.post("/followup/{lead_id}")
async def api_followup(
    lead_id: int,
    attempt: int = Query(ge=1, le=3),
    channel: str = Query(default="email"),
    db: AsyncSession = Depends(get_db),
):
    """Get a follow-up message for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = _lead_to_dict(lead)
    draft = get_followup_sequence(lead_data, channel, attempt)

    return {
        "lead_id": lead_id,
        "attempt": attempt,
        "channel": draft.channel.value,
        "subject": draft.subject,
        "body": draft.body,
    }


@router.post("/send/{lead_id}")
async def api_send_outreach(
    lead_id: int,
    channel: str = Query(default="email"),
    subject: str | None = None,
    body: str = Query(min_length=10),
    db: AsyncSession = Depends(get_db),
):
    """Save an outreach message and mark it as sent."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    msg = OutreachMessage(
        lead_id=lead_id,
        channel=channel,
        subject=subject,
        body=body,
        status="sent",
        generated_by="outreach_api",
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)

    await event_bus.emit(Event(
        type=EventType.OUTREACH_SENT,
        data={"lead_id": lead_id, "channel": channel, "message_id": msg.id},
        source="outreach_api",
    ))

    logger.info(f"Outreach sent: lead={lead_id} channel={channel} msg={msg.id}")
    return {"status": "sent", "message_id": msg.id}


@router.get("/history/{lead_id}")
async def api_outreach_history(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get outreach history for a lead."""
    result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.lead_id == lead_id)
        .order_by(OutreachMessage.created_at.desc())
    )
    messages = list(result.scalars().all())

    return {
        "lead_id": lead_id,
        "count": len(messages),
        "messages": [
            {
                "id": m.id,
                "channel": m.channel,
                "subject": m.subject,
                "body": m.body[:200] + "..." if len(m.body) > 200 else m.body,
                "status": m.status,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.post("/batch")
async def api_batch_compose(
    lead_ids: list[int],
    channel: str = Query(default="email"),
    db: AsyncSession = Depends(get_db),
):
    """Compose outreach messages for multiple leads at once."""
    result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    leads = list(result.scalars().all())

    if not leads:
        raise HTTPException(status_code=404, detail="No leads found")

    leads_data = [_lead_to_dict(l) for l in leads]
    drafts = compose_batch(leads_data, channel)

    return {
        "count": len(drafts),
        "drafts": [
            {
                "lead_id": leads[i].id if i < len(leads) else None,
                "channel": d.channel.value,
                "subject": d.subject,
                "body": d.body,
                "personalization_score": d.personalization_score,
            }
            for i, d in enumerate(drafts)
        ],
    }
