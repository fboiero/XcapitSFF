"""API endpoints for Lead Lifecycle Tracking.

Provides endpoints to view timelines, conversion probabilities,
leads needing attention, pipeline velocity, and note management.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.models import Lead
from xcapitsff.sales.lifecycle import (
    LeadEventType,
    calculate_conversion_probability,
    get_leads_needing_attention,
    get_timeline,
    get_velocity_metrics,
    record_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lifecycle", tags=["Lifecycle"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class NoteRequest(BaseModel):
    """Request body for adding a note to a lead's timeline."""

    actor: str = "user"
    notes: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/{lead_id}/timeline")
async def api_get_timeline(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the full lifecycle timeline for a lead."""
    # Verify the lead exists
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    timeline = get_timeline(lead_id)

    return {
        "lead_id": timeline.lead_id,
        "current_stage": timeline.current_stage,
        "days_in_pipeline": timeline.days_in_pipeline,
        "days_in_current_stage": timeline.days_in_current_stage,
        "conversion_probability": timeline.conversion_probability,
        "event_count": len(timeline.events),
        "events": [
            {
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "actor": event.actor,
                "data": event.data,
                "notes": event.notes,
            }
            for event in timeline.events
        ],
    }


@router.get("/{lead_id}/probability")
async def api_get_probability(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the conversion probability for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Build the lead dict for the probability calculation
    stage_val = lead.stage if isinstance(lead.stage, str) else lead.stage.value
    afinidad_val = lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value

    # Get timeline for interaction count and pipeline days
    timeline = get_timeline(lead_id)

    lead_data = {
        "stage": stage_val,
        "score_icp": lead.score_icp,
        "c_level": lead.c_level,
        "afinidad": afinidad_val,
        "num_interactions": len([
            e for e in timeline.events
            if e.event_type in {
                LeadEventType.CONTACTED,
                LeadEventType.MEETING_SCHEDULED,
                LeadEventType.OUTREACH_SENT,
                LeadEventType.OUTREACH_REPLIED,
            }
        ]),
        "days_in_pipeline": timeline.days_in_pipeline,
    }

    probability = calculate_conversion_probability(lead_data)

    return {
        "lead_id": lead_id,
        "conversion_probability": probability,
        "current_stage": stage_val,
        "score_icp": lead.score_icp,
        "factors": {
            "stage": stage_val,
            "c_level": lead.c_level,
            "afinidad": afinidad_val,
            "days_in_pipeline": timeline.days_in_pipeline,
            "interactions": lead_data["num_interactions"],
        },
    }


@router.get("/attention")
async def api_leads_needing_attention(
    db: AsyncSession = Depends(get_db),
):
    """Get leads that need human intervention."""
    leads = await get_leads_needing_attention(db)
    return {
        "count": len(leads),
        "leads": leads,
    }


@router.get("/velocity")
async def api_velocity_metrics(
    db: AsyncSession = Depends(get_db),
):
    """Get pipeline velocity metrics."""
    metrics = await get_velocity_metrics(db)
    return metrics


@router.post("/{lead_id}/note")
async def api_add_note(
    lead_id: int,
    body: NoteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a note to a lead's timeline."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    event = record_event(
        lead_id=lead_id,
        event_type=LeadEventType.NOTE_ADDED,
        actor=body.actor,
        notes=body.notes,
    )

    return {
        "status": "ok",
        "lead_id": lead_id,
        "event_type": event.event_type.value,
        "timestamp": event.timestamp.isoformat(),
        "actor": event.actor,
        "notes": event.notes,
    }
