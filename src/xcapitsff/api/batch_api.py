"""Batch operations API — execute multiple operations in a single request."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.schemas import LeadCreate, TicketCreate
from xcapitsff.sales.pipeline import create_lead, bulk_qualify, bulk_rescore
from xcapitsff.support.tickets import create_ticket

router = APIRouter(prefix="/batch", tags=["Batch Operations"])


class BatchLeadsRequest(BaseModel):
    leads: list[LeadCreate]


class BatchTicketsRequest(BaseModel):
    tickets: list[TicketCreate]


class BatchActionRequest(BaseModel):
    actions: list[dict]  # [{"action": "qualify", "params": {...}}, ...]


@router.post("/leads")
async def batch_create_leads(
    req: BatchLeadsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple leads in a single request."""
    results = []
    errors = []

    for i, lead_data in enumerate(req.leads):
        try:
            lead = await create_lead(db, lead_data)
            results.append({
                "index": i,
                "status": "created",
                "lead_id": lead.id,
                "score_icp": lead.score_icp,
            })
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    return {
        "created": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


@router.post("/tickets")
async def batch_create_tickets(
    req: BatchTicketsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple tickets in a single request."""
    from xcapitsff.support.router import full_route

    results = []
    errors = []

    for i, ticket_data in enumerate(req.tickets):
        try:
            routing = full_route(ticket_data.subject, ticket_data.description)
            if not ticket_data.category:
                ticket_data.category = routing.category

            ticket = await create_ticket(db, ticket_data)
            ticket.assigned_agent = routing.assigned_agent
            await db.flush()

            results.append({
                "index": i,
                "status": "created",
                "ticket_id": ticket.id,
                "category": routing.category,
                "assigned_agent": routing.assigned_agent,
            })
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    return {
        "created": len(results),
        "errors": len(errors),
        "results": results,
        "error_details": errors,
    }


@router.post("/actions")
async def batch_actions(
    req: BatchActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute multiple pipeline actions in sequence."""
    results = []

    for i, action_spec in enumerate(req.actions):
        action = action_spec.get("action", "")
        params = action_spec.get("params", {})

        try:
            if action == "bulk_qualify":
                threshold = params.get("score_threshold", 60.0)
                result = await bulk_qualify(db, score_threshold=threshold)
                results.append({
                    "index": i,
                    "action": action,
                    "status": "completed",
                    "result": {"processed": result.processed, "updated": result.updated},
                })
            elif action == "bulk_rescore":
                result = await bulk_rescore(db)
                results.append({
                    "index": i,
                    "action": action,
                    "status": "completed",
                    "result": {"processed": result.processed, "updated": result.updated},
                })
            else:
                results.append({
                    "index": i,
                    "action": action,
                    "status": "error",
                    "error": f"Unknown action: {action}",
                })
        except Exception as e:
            results.append({
                "index": i,
                "action": action,
                "status": "error",
                "error": str(e),
            })

    return {"total": len(results), "results": results}
