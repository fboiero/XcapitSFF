"""API endpoints for Quotes & Proposals management."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from xcapitsff.core.quotes import QuoteStatus, quote_manager

router = APIRouter(prefix="/quotes", tags=["Quotes"])


# --- Request models ---


class LineItemInput(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float
    discount_percent: float = 0
    tax_percent: float = 0


class CreateQuoteRequest(BaseModel):
    tenant_id: str
    deal_id: str
    title: str
    client_name: str
    client_email: str
    line_items: list[LineItemInput]
    valid_days: int = 30
    notes: str = ""
    terms: str = ""
    created_by: str = ""
    currency: str = "USD"


class UpdateQuoteRequest(BaseModel):
    title: str | None = None
    client_name: str | None = None
    client_email: str | None = None
    notes: str | None = None
    terms: str | None = None
    currency: str | None = None


class AddLineItemRequest(BaseModel):
    description: str
    quantity: float = 1
    unit_price: float
    discount_percent: float = 0
    tax_percent: float = 0


# --- Helpers ---


def _line_item_to_dict(item) -> dict:
    return {
        "id": item.id,
        "description": item.description,
        "quantity": item.quantity,
        "unit_price": item.unit_price,
        "discount_percent": item.discount_percent,
        "tax_percent": item.tax_percent,
        "total": item.total,
    }


def _quote_to_dict(quote) -> dict:
    return {
        "id": quote.id,
        "tenant_id": quote.tenant_id,
        "deal_id": quote.deal_id,
        "quote_number": quote.quote_number,
        "title": quote.title,
        "client_name": quote.client_name,
        "client_email": quote.client_email,
        "line_items": [_line_item_to_dict(li) for li in quote.line_items],
        "subtotal": quote.subtotal,
        "discount_total": quote.discount_total,
        "tax_total": quote.tax_total,
        "total": quote.total,
        "currency": quote.currency,
        "status": quote.status.value,
        "valid_until": quote.valid_until,
        "notes": quote.notes,
        "terms": quote.terms,
        "created_by": quote.created_by,
        "created_at": quote.created_at,
        "sent_at": quote.sent_at,
        "viewed_at": quote.viewed_at,
        "accepted_at": quote.accepted_at,
    }


# --- Endpoints ---


@router.post("/", status_code=201)
async def create_quote(req: CreateQuoteRequest):
    items = [li.model_dump() for li in req.line_items]
    quote = quote_manager.create(
        tenant_id=req.tenant_id,
        deal_id=req.deal_id,
        title=req.title,
        client_name=req.client_name,
        client_email=req.client_email,
        line_items=items,
        valid_days=req.valid_days,
        notes=req.notes,
        terms=req.terms,
        created_by=req.created_by,
        currency=req.currency,
    )
    return _quote_to_dict(quote)


@router.get("/")
async def list_quotes(
    tenant_id: str = Query(...),
    deal_id: str | None = None,
    status: str | None = None,
):
    status_enum = QuoteStatus(status) if status else None
    quotes = quote_manager.list_quotes(
        tenant_id=tenant_id, deal_id=deal_id, status=status_enum,
    )
    return {"count": len(quotes), "quotes": [_quote_to_dict(q) for q in quotes]}


@router.get("/stats")
async def quote_stats(tenant_id: str = Query(...)):
    return quote_manager.get_quote_stats(tenant_id)


@router.get("/{quote_id}")
async def get_quote(quote_id: str):
    try:
        quote = quote_manager.get(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)


@router.put("/{quote_id}")
async def update_quote(quote_id: str, req: UpdateQuoteRequest):
    try:
        kwargs = req.model_dump(exclude_unset=True)
        quote = quote_manager.update(quote_id, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)


@router.delete("/{quote_id}")
async def delete_quote(quote_id: str):
    deleted = quote_manager.delete(quote_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Quote not found")
    return {"deleted": True, "quote_id": quote_id}


@router.post("/{quote_id}/send")
async def send_quote(quote_id: str):
    try:
        quote = quote_manager.send(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)


@router.post("/{quote_id}/accept")
async def accept_quote(quote_id: str):
    try:
        quote = quote_manager.accept(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)


@router.post("/{quote_id}/reject")
async def reject_quote(quote_id: str):
    try:
        quote = quote_manager.reject(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)


@router.post("/{quote_id}/duplicate", status_code=201)
async def duplicate_quote(quote_id: str):
    try:
        quote = quote_manager.duplicate(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)


@router.get("/{quote_id}/export")
async def export_quote(quote_id: str):
    try:
        md = quote_manager.export_markdown(quote_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return PlainTextResponse(md, media_type="text/markdown")


@router.post("/{quote_id}/line-items", status_code=201)
async def add_line_item(quote_id: str, req: AddLineItemRequest):
    try:
        quote = quote_manager.add_line_item(
            quote_id=quote_id,
            description=req.description,
            quantity=req.quantity,
            unit_price=req.unit_price,
            discount_percent=req.discount_percent,
            tax_percent=req.tax_percent,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)


@router.delete("/{quote_id}/line-items/{item_id}")
async def remove_line_item(quote_id: str, item_id: str):
    try:
        quote = quote_manager.remove_line_item(quote_id, item_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quote_to_dict(quote)
