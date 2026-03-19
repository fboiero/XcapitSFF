"""API endpoints for the visual workflow builder engine."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from xcapitsff.core.workflows import (
    ActionType,
    StepType,
    TriggerType,
    Workflow,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStep,
    WORKFLOW_TEMPLATES,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])

# Shared engine instance --------------------------------------------------
engine = WorkflowEngine()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class StepPayload(BaseModel):
    step_id: str
    type: StepType
    action_type: ActionType | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    next_steps: list[str] = Field(default_factory=list)
    condition_true_step: str | None = None
    condition_false_step: str | None = None


class CreateWorkflowRequest(BaseModel):
    name: str
    tenant_id: str
    trigger: TriggerType
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepPayload]
    description: str = ""


class ExecuteWorkflowRequest(BaseModel):
    trigger_data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _step_dict(s: WorkflowStep) -> dict[str, Any]:
    return {
        "step_id": s.step_id,
        "type": s.type.value,
        "action_type": s.action_type.value if s.action_type else None,
        "config": s.config,
        "next_steps": s.next_steps,
        "condition_true_step": s.condition_true_step,
        "condition_false_step": s.condition_false_step,
    }


def _workflow_dict(w: Workflow) -> dict[str, Any]:
    return {
        "workflow_id": w.workflow_id,
        "name": w.name,
        "description": w.description,
        "tenant_id": w.tenant_id,
        "trigger": w.trigger.value,
        "trigger_config": w.trigger_config,
        "steps": [_step_dict(s) for s in w.steps],
        "is_active": w.is_active,
        "version": w.version,
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
        "execution_count": w.execution_count,
        "last_executed": w.last_executed.isoformat() if w.last_executed else None,
    }


def _execution_dict(e: WorkflowExecution) -> dict[str, Any]:
    return {
        "execution_id": e.execution_id,
        "workflow_id": e.workflow_id,
        "trigger_data": e.trigger_data,
        "status": e.status,
        "started_at": e.started_at.isoformat(),
        "completed_at": e.completed_at.isoformat() if e.completed_at else None,
        "steps_executed": e.steps_executed,
        "current_step": e.current_step,
        "error": e.error,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def create_workflow(body: CreateWorkflowRequest) -> dict[str, Any]:
    """Create a new workflow definition."""
    steps = [
        WorkflowStep(
            step_id=s.step_id,
            type=s.type,
            action_type=s.action_type,
            config=s.config,
            next_steps=s.next_steps,
            condition_true_step=s.condition_true_step,
            condition_false_step=s.condition_false_step,
        )
        for s in body.steps
    ]
    wf = engine.create_workflow(
        name=body.name,
        tenant_id=body.tenant_id,
        trigger=body.trigger,
        steps=steps,
        trigger_config=body.trigger_config,
        description=body.description,
    )
    return _workflow_dict(wf)


@router.get("")
async def list_workflows(tenant_id: str | None = None) -> list[dict[str, Any]]:
    """List workflows, optionally filtered by tenant."""
    return [_workflow_dict(w) for w in engine.list_workflows(tenant_id)]


@router.get("/templates")
async def list_templates() -> dict[str, Any]:
    """Return all pre-built workflow templates."""
    result: dict[str, Any] = {}
    for tid, tpl in WORKFLOW_TEMPLATES.items():
        result[tid] = {
            "name": tpl["name"],
            "description": tpl["description"],
            "trigger": tpl["trigger"].value,
            "trigger_config": tpl["trigger_config"],
            "steps": [_step_dict(s) for s in tpl["steps"]],
        }
    return result


@router.post("/from-template/{template_id}", status_code=201)
async def create_from_template(template_id: str, tenant_id: str = "default") -> dict[str, Any]:
    """Create a new workflow from a pre-built template."""
    tpl = WORKFLOW_TEMPLATES.get(template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    # Deep-copy steps so each workflow gets its own instances
    steps = [
        WorkflowStep(
            step_id=s.step_id,
            type=s.type,
            action_type=s.action_type,
            config=dict(s.config),
            next_steps=list(s.next_steps),
            condition_true_step=s.condition_true_step,
            condition_false_step=s.condition_false_step,
        )
        for s in tpl["steps"]
    ]

    wf = engine.create_workflow(
        name=tpl["name"],
        tenant_id=tenant_id,
        trigger=tpl["trigger"],
        steps=steps,
        trigger_config=dict(tpl["trigger_config"]),
        description=tpl["description"],
    )
    return _workflow_dict(wf)


@router.get("/stats")
async def workflow_stats() -> dict[str, Any]:
    """Return global workflow execution statistics."""
    return engine.get_stats()


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str) -> dict[str, Any]:
    """Get a single workflow by id."""
    wf = engine.get_workflow(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _workflow_dict(wf)


@router.patch("/{workflow_id}/toggle")
async def toggle_workflow(workflow_id: str) -> dict[str, Any]:
    """Toggle the active state of a workflow."""
    try:
        new_state = engine.toggle_workflow(workflow_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"workflow_id": workflow_id, "is_active": new_state}


@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, body: ExecuteWorkflowRequest | None = None) -> dict[str, Any]:
    """Manually trigger a workflow execution."""
    trigger_data = body.trigger_data if body else {}
    try:
        execution = engine.execute_workflow(workflow_id, trigger_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _execution_dict(execution)


@router.get("/{workflow_id}/executions")
async def get_executions(workflow_id: str) -> list[dict[str, Any]]:
    """Return execution history for a workflow."""
    return [_execution_dict(e) for e in engine.get_executions(workflow_id)]
