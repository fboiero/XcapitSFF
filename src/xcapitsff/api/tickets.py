"""API endpoints for Ticket/Support management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.schemas import (
    SupportStats,
    TicketCreate,
    TicketMessageCreate,
    TicketMessageResponse,
    TicketResponse,
    TicketUpdate,
)
from xcapitsff.support.router import full_route
from xcapitsff.support.tickets import (
    add_message,
    create_ticket,
    get_support_stats,
    get_ticket,
    get_ticket_messages,
    get_tickets,
    update_ticket,
)

router = APIRouter(prefix="/tickets", tags=["Support"])


@router.post("/", response_model=TicketResponse, status_code=201)
async def api_create_ticket(data: TicketCreate, db: AsyncSession = Depends(get_db)):
    # Auto-classify and route using full pipeline
    routing = full_route(data.subject, data.description)
    if not data.category:
        data.category = routing.category

    ticket = await create_ticket(db, data)

    # Auto-assign agent
    ticket.assigned_agent = routing.assigned_agent
    await db.flush()
    await db.refresh(ticket)

    return ticket


@router.get("/", response_model=list[TicketResponse])
async def api_list_tickets(
    status: str | None = None,
    priority: str | None = None,
    customer_id: int | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    return await get_tickets(db, status, priority, customer_id, limit, offset)


@router.get("/stats", response_model=SupportStats)
async def api_support_stats(db: AsyncSession = Depends(get_db)):
    return await get_support_stats(db)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def api_get_ticket(ticket_id: int, db: AsyncSession = Depends(get_db)):
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def api_update_ticket(
    ticket_id: int, data: TicketUpdate, db: AsyncSession = Depends(get_db)
):
    ticket = await update_ticket(db, ticket_id, data)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/{ticket_id}/messages", response_model=list[TicketMessageResponse])
async def api_get_messages(ticket_id: int, db: AsyncSession = Depends(get_db)):
    return await get_ticket_messages(db, ticket_id)


@router.post("/{ticket_id}/messages", response_model=TicketMessageResponse, status_code=201)
async def api_add_message(
    ticket_id: int, data: TicketMessageCreate, db: AsyncSession = Depends(get_db)
):
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return await add_message(db, ticket_id, data)
