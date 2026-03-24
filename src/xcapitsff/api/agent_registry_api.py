"""Agent Registry API — manage agent profiles, capabilities, and pool stats."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.agents.agent_registry import (
    AgentCapability,
    AgentProfile,
    AgentStatus,
    ModelTier,
    agent_registry,
)

router = APIRouter(prefix="/agent-registry", tags=["Agent Registry"])


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

def _serialize(obj):
    """Convert dataclass instances to JSON-safe dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        d = {}
        for f in obj.__dataclass_fields__:
            v = getattr(obj, f)
            if isinstance(v, datetime):
                d[f] = v.isoformat() if v else None
            elif isinstance(v, list):
                d[f] = [_serialize(i) if hasattr(i, "__dataclass_fields__") else
                        (i.value if hasattr(i, "value") else i) for i in v]
            elif hasattr(v, "value"):  # enum
                d[f] = v.value
            else:
                d[f] = v
        return d
    return obj


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class RegisterAgentBody(BaseModel):
    name: str
    role: str
    capabilities: list[str]
    model_tier: str = "sonnet"
    system_prompt: str = ""


class UpdateStatusBody(BaseModel):
    status: str
    task_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
def list_agents(status: Optional[str] = None):
    """List all agents, optionally filtered by status."""
    st = AgentStatus(status) if status else None
    agents = agent_registry.list_agents(status=st)
    return [_serialize(a) for a in agents]


@router.get("/stats")
def pool_stats():
    """Return aggregate pool statistics."""
    return agent_registry.get_pool_stats()


@router.get("/capable/{capability}")
def get_capable_agents(capability: str):
    """Get agents with a specific capability."""
    try:
        cap = AgentCapability(capability)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown capability: {capability}")
    agents = agent_registry.get_available(cap)
    return [_serialize(a) for a in agents]


@router.get("/{agent_id}")
def get_agent(agent_id: str):
    """Get agent profile and stats."""
    agent = agent_registry.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "profile": _serialize(agent),
        "stats": agent_registry.get_agent_stats(agent_id),
    }


@router.post("/")
def register_agent(body: RegisterAgentBody):
    """Register a custom agent."""
    import random
    import string

    agent_id = "custom_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    try:
        caps = [AgentCapability(c) for c in body.capabilities]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        tier = ModelTier(body.model_tier)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown model tier: {body.model_tier}")

    profile = AgentProfile(
        id=agent_id,
        name=body.name,
        role=body.role,
        description=f"Custom agent: {body.name}",
        capabilities=caps,
        model_tier=tier,
        system_prompt=body.system_prompt,
        tools=[],
    )
    agent_registry.register(profile)
    return _serialize(profile)


@router.patch("/{agent_id}/status")
def update_agent_status(agent_id: str, body: UpdateStatusBody):
    """Update an agent's status."""
    agent = agent_registry.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    try:
        status = AgentStatus(body.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown status: {body.status}")

    agent_registry.update_status(agent_id, status, task_id=body.task_id)
    return {"agent_id": agent_id, "status": status.value, "task_id": body.task_id}


@router.delete("/{agent_id}")
def unregister_agent(agent_id: str):
    """Unregister an agent."""
    removed = agent_registry.unregister(agent_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"removed": agent_id}
