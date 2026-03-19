"""API endpoints for invoking agents and managing conversations."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.agents.conversation import conversation_memory
from xcapitsff.agents.runner import agent_runner
from xcapitsff.core.database import get_db

router = APIRouter(prefix="/agent-runner", tags=["Agent Runner"])


class RunAgentRequest(BaseModel):
    agent_name: str
    action: str
    context: str
    context_type: str = "general"
    context_id: str | None = None


class QualifyLeadRequest(BaseModel):
    lead_id: int


class DraftOutreachRequest(BaseModel):
    lead_id: int
    channel: str = "email"


class HandleTicketRequest(BaseModel):
    ticket_id: int


@router.post("/run")
async def api_run_agent(req: RunAgentRequest):
    """Run an agent with custom context."""
    result = agent_runner.run_agent(
        agent_name=req.agent_name,
        action=req.action,
        context=req.context,
        context_type=req.context_type,
        context_id=req.context_id,
    )
    return {
        "success": result.success,
        "agent_name": result.agent_name,
        "action": result.action,
        "response": result.response,
        "conversation_id": result.conversation_id,
        "tokens_used": result.tokens_used,
        "error": result.error,
    }


@router.post("/qualify-lead")
async def api_qualify_lead(req: QualifyLeadRequest, db: AsyncSession = Depends(get_db)):
    """Invoke sales qualifier on a specific lead."""
    from xcapitsff.sales.pipeline import get_lead
    lead = await get_lead(db, req.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = {
        "id": lead.id,
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "region": lead.region if isinstance(lead.region, str) else lead.region.value,
        "c_level": lead.c_level,
        "score_icp": lead.score_icp,
        "afinidad": lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
    }
    result = agent_runner.qualify_lead(lead_data)
    return {
        "lead_id": req.lead_id,
        "success": result.success,
        "response": result.response,
        "conversation_id": result.conversation_id,
    }


@router.post("/draft-outreach")
async def api_draft_outreach(req: DraftOutreachRequest, db: AsyncSession = Depends(get_db)):
    """Invoke outreach composer on a specific lead."""
    from xcapitsff.sales.pipeline import get_lead
    lead = await get_lead(db, req.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = {
        "id": lead.id,
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "region": lead.region if isinstance(lead.region, str) else lead.region.value,
        "c_level": lead.c_level,
        "score_icp": lead.score_icp,
        "afinidad": lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
    }
    result = agent_runner.draft_outreach(lead_data, channel=req.channel)
    return {
        "lead_id": req.lead_id,
        "channel": req.channel,
        "success": result.success,
        "response": result.response,
        "conversation_id": result.conversation_id,
    }


@router.post("/handle-ticket")
async def api_handle_ticket(req: HandleTicketRequest, db: AsyncSession = Depends(get_db)):
    """Invoke support responder on a specific ticket."""
    from xcapitsff.support.tickets import get_ticket
    ticket = await get_ticket(db, req.ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket_data = {
        "id": ticket.id,
        "subject": ticket.subject,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
    }
    result = agent_runner.handle_ticket(ticket_data)
    return {
        "ticket_id": req.ticket_id,
        "success": result.success,
        "response": result.response,
        "conversation_id": result.conversation_id,
    }


# --- Conversation Management ---

@router.get("/conversations")
async def api_list_conversations(
    agent_name: str | None = None,
    context_type: str | None = None,
    limit: int = Query(default=50, le=200),
):
    """List all agent conversations."""
    convs = conversation_memory.list_conversations(agent_name, context_type, limit)
    return {
        "count": len(convs),
        "conversations": [
            {
                "id": c.conversation_id,
                "agent": c.agent_name,
                "context_type": c.context_type,
                "context_id": c.context_id,
                "messages": c.message_count,
                "last_active": c.last_active.isoformat(),
            }
            for c in convs
        ],
    }


@router.get("/conversations/{conversation_id}")
async def api_get_conversation(conversation_id: str):
    """Get a specific conversation with full message history."""
    conv = conversation_memory.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {
        "id": conv.conversation_id,
        "agent": conv.agent_name,
        "context_type": conv.context_type,
        "context_id": conv.context_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in conv.messages
        ],
        "message_count": conv.message_count,
        "duration_minutes": round(conv.duration_minutes, 1),
    }


@router.get("/conversations/stats")
async def api_conversation_stats():
    """Get conversation memory statistics."""
    return conversation_memory.get_stats()
