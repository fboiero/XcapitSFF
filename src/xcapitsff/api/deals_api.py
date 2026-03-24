"""API endpoints for Deals pipeline management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.deals import DealPriority, DealStage, deal_manager

router = APIRouter(prefix="/deals", tags=["Deals"])


# --- Request models ---


class CreateDealRequest(BaseModel):
    tenant_id: str
    name: str
    amount: float
    stage: str = "prospecting"
    priority: str = "medium"
    currency: str = "USD"
    probability: float | None = None
    expected_close_date: str = ""
    owner_id: str = ""
    company_id: str | None = None
    contact_id: str | None = None
    lead_id: str | None = None
    tags: list[str] = []
    custom_fields: dict = {}


class UpdateDealRequest(BaseModel):
    name: str | None = None
    amount: float | None = None
    priority: str | None = None
    currency: str | None = None
    probability: float | None = None
    expected_close_date: str | None = None
    owner_id: str | None = None
    company_id: str | None = None
    contact_id: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None


class MoveStageRequest(BaseModel):
    new_stage: str
    lost_reason: str | None = None


class ConvertLeadRequest(BaseModel):
    tenant_id: str
    lead_id: str
    name: str
    amount: float


class ConvertLeadSimple(BaseModel):
    tenant_id: str
    lead_id: str
    name: str = ""  # Auto-generated if empty
    amount: float = 0  # Can be 0 initially
    stage: str = "prospecting"


# --- Helpers ---


def _deal_to_dict(deal) -> dict:
    return {
        "id": deal.id,
        "tenant_id": deal.tenant_id,
        "name": deal.name,
        "stage": deal.stage.value,
        "priority": deal.priority.value,
        "amount": deal.amount,
        "currency": deal.currency,
        "probability": deal.probability,
        "expected_close_date": deal.expected_close_date,
        "owner_id": deal.owner_id,
        "company_id": deal.company_id,
        "contact_id": deal.contact_id,
        "lead_id": deal.lead_id,
        "tags": deal.tags,
        "custom_fields": deal.custom_fields,
        "created_at": deal.created_at,
        "updated_at": deal.updated_at,
        "closed_at": deal.closed_at,
        "lost_reason": deal.lost_reason,
    }


# --- Endpoints ---


@router.post("/", status_code=201)
async def create_deal(req: CreateDealRequest):
    try:
        stage = DealStage(req.stage)
        priority = DealPriority(req.priority)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    deal = deal_manager.create(
        tenant_id=req.tenant_id,
        name=req.name,
        amount=req.amount,
        stage=stage,
        priority=priority,
        currency=req.currency,
        probability=req.probability,
        expected_close_date=req.expected_close_date,
        owner_id=req.owner_id,
        company_id=req.company_id,
        contact_id=req.contact_id,
        lead_id=req.lead_id,
        tags=req.tags,
        custom_fields=req.custom_fields,
    )
    return _deal_to_dict(deal)


@router.get("/")
async def list_deals(
    tenant_id: str = Query(...),
    stage: str | None = None,
    owner_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stage_enum = DealStage(stage) if stage else None
    deals = deal_manager.list_deals(
        tenant_id=tenant_id,
        stage=stage_enum,
        owner_id=owner_id,
        limit=limit,
        offset=offset,
    )
    return {"count": len(deals), "deals": [_deal_to_dict(d) for d in deals]}


@router.get("/pipeline")
async def pipeline_summary(tenant_id: str = Query(...)):
    return deal_manager.get_pipeline_summary(tenant_id)


@router.get("/forecast")
async def revenue_forecast(tenant_id: str = Query(...), months: int = Query(3, ge=1, le=12)):
    return deal_manager.get_forecast(tenant_id, months=months)


@router.get("/{deal_id}")
async def get_deal(deal_id: str):
    try:
        deal = deal_manager.get(deal_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _deal_to_dict(deal)


@router.put("/{deal_id}")
async def update_deal(deal_id: str, req: UpdateDealRequest):
    try:
        kwargs = req.model_dump(exclude_unset=True)
        if "priority" in kwargs and kwargs["priority"] is not None:
            kwargs["priority"] = DealPriority(kwargs["priority"])
        deal = deal_manager.update(deal_id, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="Deal not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _deal_to_dict(deal)


@router.delete("/{deal_id}")
async def delete_deal(deal_id: str):
    deleted = deal_manager.delete(deal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Deal not found")
    return {"deleted": True, "deal_id": deal_id}


@router.post("/{deal_id}/stage")
async def move_stage(deal_id: str, req: MoveStageRequest):
    try:
        new_stage = DealStage(req.new_stage)
        deal = deal_manager.move_stage(deal_id, new_stage, lost_reason=req.lost_reason)
    except KeyError:
        raise HTTPException(status_code=404, detail="Deal not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _deal_to_dict(deal)


@router.post("/convert-lead", status_code=201)
async def convert_lead(req: ConvertLeadRequest | ConvertLeadSimple):
    # Auto-fill from lead data when fields are empty
    name = req.name if req.name else f"Deal from lead {req.lead_id}"
    amount = req.amount if req.amount > 0 else 0.0
    stage_str = req.stage if hasattr(req, 'stage') else "prospecting"

    try:
        stage = DealStage(stage_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {stage_str}")

    deal = deal_manager.convert_from_lead(
        tenant_id=req.tenant_id,
        lead_id=req.lead_id,
        name=name,
        amount=amount,
        stage=stage,
    )
    return _deal_to_dict(deal)
