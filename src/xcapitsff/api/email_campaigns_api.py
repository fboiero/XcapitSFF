"""API endpoints for Email Campaign management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.email_campaigns import (
    CampaignStatus,
    CampaignType,
    EmailCampaignManager,
    email_campaign_manager,
)

router = APIRouter(prefix="/email-campaigns", tags=["Email Campaigns"])


# --- Request models ---


class CampaignCreateRequest(BaseModel):
    tenant_id: str
    name: str
    campaign_type: str
    template_id: str
    created_by: str | None = None


class CampaignUpdateRequest(BaseModel):
    name: str | None = None
    template_id: str | None = None
    subject_override: str | None = None
    tags: list[str] | None = None


class RecipientsRequest(BaseModel):
    recipients: list[dict]


class ScheduleRequest(BaseModel):
    scheduled_at: str


class TrackingRequest(BaseModel):
    email: str


# --- Endpoints ---


@router.post("/", status_code=201)
async def create_campaign(req: CampaignCreateRequest):
    campaign = email_campaign_manager.create(
        tenant_id=req.tenant_id,
        name=req.name,
        campaign_type=req.campaign_type,
        template_id=req.template_id,
        created_by=req.created_by,
    )
    return _serialize(campaign)


@router.get("/")
async def list_campaigns(
    tenant_id: str = Query(...),
    status: str | None = None,
):
    campaigns = email_campaign_manager.list_campaigns(
        tenant_id=tenant_id, status=status
    )
    return {"count": len(campaigns), "campaigns": [_serialize(c) for c in campaigns]}


@router.get("/performance")
async def campaign_performance(
    tenant_id: str = Query(...),
    days: int = Query(default=30, ge=1, le=365),
):
    return email_campaign_manager.get_campaign_performance(
        tenant_id=tenant_id, days=days
    )


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    campaign = email_campaign_manager.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    return _serialize(campaign)


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, req: CampaignUpdateRequest):
    try:
        kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
        campaign = email_campaign_manager.update(campaign_id, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    return _serialize(campaign)


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: str):
    if not email_campaign_manager.delete(campaign_id):
        raise HTTPException(status_code=404, detail="Email campaign not found")
    return {"deleted": True}


@router.post("/{campaign_id}/recipients")
async def add_recipients(campaign_id: str, req: RecipientsRequest):
    try:
        campaign = email_campaign_manager.add_recipients(
            campaign_id, req.recipients
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    return _serialize(campaign)


@router.delete("/{campaign_id}/recipients/{email}")
async def remove_recipient(campaign_id: str, email: str):
    try:
        removed = email_campaign_manager.remove_recipient(campaign_id, email)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    return {"removed": removed}


@router.post("/{campaign_id}/schedule")
async def schedule_campaign(campaign_id: str, req: ScheduleRequest):
    try:
        campaign = email_campaign_manager.schedule(campaign_id, req.scheduled_at)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize(campaign)


@router.post("/{campaign_id}/send")
async def send_campaign(campaign_id: str):
    try:
        campaign = email_campaign_manager.send(campaign_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize(campaign)


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    try:
        campaign = email_campaign_manager.pause(campaign_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize(campaign)


@router.post("/{campaign_id}/cancel")
async def cancel_campaign(campaign_id: str):
    try:
        campaign = email_campaign_manager.cancel(campaign_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize(campaign)


@router.get("/{campaign_id}/stats")
async def get_campaign_stats(campaign_id: str):
    try:
        stats = email_campaign_manager.get_stats(campaign_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email campaign not found")
    return {
        "total_recipients": stats.total_recipients,
        "sent": stats.sent,
        "delivered": stats.delivered,
        "opened": stats.opened,
        "clicked": stats.clicked,
        "bounced": stats.bounced,
        "unsubscribed": stats.unsubscribed,
        "open_rate": stats.open_rate,
        "click_rate": stats.click_rate,
        "bounce_rate": stats.bounce_rate,
    }


# --- Serialiser ---


def _serialize(c) -> dict:
    return {
        "id": c.id,
        "tenant_id": c.tenant_id,
        "name": c.name,
        "type": c.type.value,
        "status": c.status.value,
        "template_id": c.template_id,
        "subject_override": c.subject_override,
        "recipients_count": len(c.recipients),
        "scheduled_at": c.scheduled_at,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        "created_by": c.created_by,
        "created_at": c.created_at.isoformat(),
        "ab_variant_id": c.ab_variant_id,
        "tags": c.tags,
    }
