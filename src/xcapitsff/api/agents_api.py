"""API endpoints for Agent management and orchestration."""

import logging

from fastapi import APIRouter

from xcapitsff.agents.orchestrator import AgentOrchestrator
from xcapitsff.core.events import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])

# Singleton orchestrator
orchestrator = AgentOrchestrator(event_bus)


@router.get("/status")
async def agent_status():
    """Get orchestrator status and task statistics."""
    return orchestrator.get_stats()


@router.get("/tasks/pending")
async def pending_tasks():
    """Get pending agent tasks."""
    tasks = orchestrator.get_pending_tasks()
    return {
        "count": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "agent": t.agent_name,
                "action": t.action,
                "status": t.status.value,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ],
    }


@router.get("/tasks/history")
async def task_history(limit: int = 50):
    """Get agent task execution history."""
    tasks = orchestrator.get_task_history(limit)
    return {
        "count": len(tasks),
        "tasks": [
            {
                "task_id": t.task_id,
                "agent": t.agent_name,
                "action": t.action,
                "status": t.status.value,
                "result": t.result,
                "error": t.error,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ],
    }


@router.post("/tasks/process")
async def process_task_queue():
    """Manually trigger processing of the task queue."""
    processed = await orchestrator.process_queue()
    return {
        "processed": len(processed),
        "tasks": [
            {
                "task_id": t.task_id,
                "agent": t.agent_name,
                "action": t.action,
                "status": t.status.value,
            }
            for t in processed
        ],
    }


@router.get("/rules")
async def list_rules():
    """List all active event→agent rules."""
    return {
        "count": len(orchestrator.rules),
        "rules": [
            {
                "event": rule["event"].value,
                "agent": rule["agent"],
                "action": rule["action"],
                "description": rule["description"],
            }
            for rule in orchestrator.rules
        ],
    }
