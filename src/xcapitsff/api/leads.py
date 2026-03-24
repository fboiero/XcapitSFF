"""API endpoints for Lead management."""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.schemas import (
    AfinidadEnum,
    LeadCreate,
    LeadFilter,
    LeadResponse,
    LeadStageEnum,
    LeadUpdate,
    RegionEnum,
    SalesPipelineStats,
)
from xcapitsff.sales.importer import import_leads_bulk, parse_leads_tsv
from xcapitsff.sales.pipeline import (
    bulk_qualify,
    bulk_rescore,
    create_lead,
    delete_lead,
    get_hot_leads,
    get_lead,
    get_leads,
    get_pipeline_stats,
    get_stale_leads,
    update_lead,
)

router = APIRouter(prefix="/leads", tags=["Sales"])


class LeadTransitionRequest(BaseModel):
    new_stage: LeadStageEnum
    reason: str = ""


@router.post("/", response_model=LeadResponse, status_code=201)
async def api_create_lead(data: LeadCreate, db: AsyncSession = Depends(get_db)):
    lead = await create_lead(db, data)
    return lead


@router.get("/", response_model=list[LeadResponse])
async def api_list_leads(
    region: RegionEnum | None = None,
    c_level: bool | None = None,
    afinidad: AfinidadEnum | None = None,
    stage: LeadStageEnum | None = None,
    score_min: float | None = None,
    score_max: float | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    filters = LeadFilter(
        region=region,
        c_level=c_level,
        afinidad=afinidad,
        stage=stage,
        score_min=score_min,
        score_max=score_max,
    )
    return await get_leads(db, filters, limit, offset)


@router.get("/stats", response_model=SalesPipelineStats)
async def api_pipeline_stats(db: AsyncSession = Depends(get_db)):
    return await get_pipeline_stats(db)


@router.get("/hot", response_model=list[LeadResponse])
async def api_hot_leads(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Shortcut endpoint to get hot leads (high score, early stage)."""
    leads = await get_hot_leads(db, limit=limit)
    return leads


@router.get("/stale", response_model=list[LeadResponse])
async def api_stale_leads(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get leads that have not been updated in the specified number of days."""
    leads = await get_stale_leads(db, days=days)
    return leads


@router.post("/bulk-qualify")
async def api_bulk_qualify(
    score_threshold: float = Query(default=60.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Trigger bulk qualification: auto-qualify all RAW leads above the score threshold."""
    result = await bulk_qualify(db, score_threshold=score_threshold)
    return {
        "processed": result.processed,
        "updated": result.updated,
        "skipped": result.skipped,
    }


@router.post("/bulk-rescore")
async def api_bulk_rescore(db: AsyncSession = Depends(get_db)):
    """Trigger bulk rescoring: recalculate ICP scores for all leads."""
    result = await bulk_rescore(db)
    return {
        "processed": result.processed,
        "updated": result.updated,
        "skipped": result.skipped,
    }


@router.get("/{lead_id}", response_model=LeadResponse)
async def api_get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
async def api_update_lead(lead_id: int, data: LeadUpdate, db: AsyncSession = Depends(get_db)):
    try:
        lead = await update_lead(db, lead_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.delete("/{lead_id}", status_code=204)
async def api_delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a lead by ID."""
    deleted = await delete_lead(db, lead_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found")
    return None


@router.post("/{lead_id}/transition", response_model=LeadResponse)
async def api_transition_lead(
    lead_id: int,
    req: LeadTransitionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Transition a lead to a new stage with validation."""
    lead = await get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Valid transitions
    VALID_TRANSITIONS = {
        "raw": ["contacted", "qualified", "disqualified"],
        "contacted": ["qualified", "proposal", "disqualified"],
        "qualified": ["proposal", "negotiation", "disqualified"],
        "proposal": ["negotiation", "won", "lost"],
        "negotiation": ["won", "lost"],
        "won": [],
        "lost": ["raw"],  # Can recycle
        "disqualified": ["raw"],  # Can recycle
    }

    current = lead.stage.value if hasattr(lead.stage, 'value') else str(lead.stage)
    target = req.new_stage.value if hasattr(req.new_stage, 'value') else str(req.new_stage)

    valid_targets = VALID_TRANSITIONS.get(current, [])
    if target not in valid_targets:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition: {current} → {target}. Valid: {valid_targets}"
        )

    data = LeadUpdate(stage=req.new_stage)
    updated = await update_lead(db, lead_id, data)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update lead")
    return updated


@router.post("/import", status_code=201)
async def api_import_leads(file: UploadFile, db: AsyncSession = Depends(get_db)):
    content = await file.read()
    text = content.decode("utf-8")
    leads_data = parse_leads_tsv(text)
    result = await import_leads_bulk(db, leads_data)
    return {
        "imported": result.imported,
        "skipped_duplicate": result.skipped_duplicate,
        "errors": len(result.errors),
    }
