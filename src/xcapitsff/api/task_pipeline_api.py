"""Task Pipeline API — manage tasks, dependencies, and pipeline analytics."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.task_pipeline import (
    PipelineTaskStatus,
    TaskPriority,
    task_pipeline,
)

router = APIRouter(prefix="/pipeline", tags=["Task Pipeline"])


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

class CreateTaskBody(BaseModel):
    workspace_id: str
    title: str
    description: str = ""
    phase: str = "implementation"
    capability_required: Optional[str] = None
    dependencies: list[str] = []
    input_artifacts: list[str] = []
    priority: str = "medium"
    estimated_tokens: int = 0


class AssignTaskBody(BaseModel):
    agent_id: str


class RejectTaskBody(BaseModel):
    feedback: str


class ChangePriorityBody(BaseModel):
    priority: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/tasks")
def create_task(body: CreateTaskBody):
    """Create a new pipeline task."""
    task = task_pipeline.create_task(
        workspace_id=body.workspace_id,
        title=body.title,
        description=body.description,
        phase=body.phase,
        capability_required=body.capability_required,
        dependencies=body.dependencies,
        input_artifacts=body.input_artifacts,
        priority=body.priority,
        estimated_tokens=body.estimated_tokens,
    )
    return _serialize(task)


@router.get("/tasks")
def list_tasks(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
):
    """List tasks with optional filters."""
    st = PipelineTaskStatus(status) if status else None
    tasks = task_pipeline.list_tasks(workspace_id=workspace_id, status=st, phase=phase)
    return [_serialize(t) for t in tasks]


@router.get("/tasks/ready")
def get_ready_tasks(workspace_id: Optional[str] = None):
    """Get tasks ready for execution (dependencies met)."""
    tasks = task_pipeline.get_ready_tasks(workspace_id=workspace_id)
    return [_serialize(t) for t in tasks]


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get task detail."""
    task = task_pipeline.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)


@router.post("/tasks/{task_id}/assign")
def assign_task(task_id: str, body: AssignTaskBody):
    """Assign a task to an agent."""
    task = task_pipeline.assign_task(task_id, body.agent_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel a task."""
    task = task_pipeline.cancel_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)


@router.post("/tasks/{task_id}/review")
def send_to_review(task_id: str):
    """Send a task to review."""
    task = task_pipeline.send_to_review(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)


@router.post("/tasks/{task_id}/approve")
def approve_task(task_id: str):
    """Approve a task."""
    task = task_pipeline.approve_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)


@router.post("/tasks/{task_id}/reject")
def reject_task(task_id: str, body: RejectTaskBody):
    """Reject a task with feedback."""
    task = task_pipeline.reject_task(task_id, body.feedback)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize(task)


@router.patch("/tasks/{task_id}/priority")
def change_priority(task_id: str, body: ChangePriorityBody):
    """Change task priority."""
    task = task_pipeline.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        task.priority = TaskPriority(body.priority)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown priority: {body.priority}")

    return _serialize(task)


@router.get("/view/{workspace_id}")
def pipeline_view(workspace_id: str):
    """Get pipeline view grouped by status."""
    return task_pipeline.get_pipeline_view(workspace_id)


@router.get("/graph/{workspace_id}")
def dependency_graph(workspace_id: str):
    """Get dependency graph for a workspace."""
    return task_pipeline.get_dependency_graph(workspace_id)


@router.get("/stats")
def pipeline_stats(workspace_id: Optional[str] = None):
    """Get pipeline statistics."""
    return task_pipeline.get_stats(workspace_id=workspace_id)
