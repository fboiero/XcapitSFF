"""API endpoints for Campaign management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.sales.campaigns import (
    CampaignManager,
    CampaignStatus,
    CampaignTarget,
    CampaignType,
    campaign_manager,
)

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


class CampaignCreateRequest(BaseModel):
    name: str
    campaign_type: str  # outreach, nurturing, reactivation, upsell, event
    channel: str = "email"
    notes: str = ""
    regions: list[str] | None = None
    score_min: float | None = None
    score_max: float | None = None
    c_level_only: bool = False
    stages: list[str] | None = None
    template_ids: list[str] | None = None
    followup_days: list[int] | None = None


@router.post("/", status_code=201)
async def create_campaign(req: CampaignCreateRequest):
    target = CampaignTarget(
        regions=req.regions,
        score_min=req.score_min,
        score_max=req.score_max,
        c_level_only=req.c_level_only,
        stages=req.stages,
    )
    campaign = campaign_manager.create(
        name=req.name,
        campaign_type=req.campaign_type,
        channel=req.channel,
        target=target,
        template_ids=req.template_ids,
        followup_days=req.followup_days,
        notes=req.notes,
    )
    return _serialize(campaign)


@router.get("/")
async def list_campaigns(
    status: str | None = None,
    limit: int = Query(default=50, le=200),
):
    status_enum = CampaignStatus(status) if status else None
    campaigns = campaign_manager.list_campaigns(status=status_enum, limit=limit)
    return {"count": len(campaigns), "campaigns": [_serialize(c) for c in campaigns]}


@router.get("/stats")
async def campaign_stats():
    return campaign_manager.get_stats()


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    campaign = campaign_manager.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _serialize(campaign)


@router.post("/{campaign_id}/start")
async def start_campaign(campaign_id: str):
    campaign = campaign_manager.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        campaign.start()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize(campaign)


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    campaign = campaign_manager.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        campaign.pause()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _serialize(campaign)


@router.post("/{campaign_id}/complete")
async def complete_campaign(campaign_id: str):
    campaign = campaign_manager.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.complete()
    return _serialize(campaign)


def _serialize(c) -> dict:
    return {
        "campaign_id": c.campaign_id,
        "name": c.name,
        "type": c.campaign_type.value,
        "status": c.status.value,
        "channel": c.channel,
        "target": {
            "regions": c.target.regions,
            "score_min": c.target.score_min,
            "score_max": c.target.score_max,
            "c_level_only": c.target.c_level_only,
            "stages": c.target.stages,
        },
        "metrics": {
            "total_targeted": c.metrics.total_targeted,
            "messages_sent": c.metrics.messages_sent,
            "replies_received": c.metrics.replies_received,
            "reply_rate": c.metrics.reply_rate,
            "conversions": c.metrics.conversions,
            "conversion_rate": c.metrics.conversion_rate,
        },
        "created_at": c.created_at.isoformat(),
        "started_at": c.started_at.isoformat() if c.started_at else None,
    }
