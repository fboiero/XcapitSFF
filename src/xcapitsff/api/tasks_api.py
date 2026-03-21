"""API endpoints for Tasks & Reminders management.

Provides CRUD for tasks, status transitions (complete / cancel / reassign),
reminder management, and convenience queries (today, upcoming, overdue, stats).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.tasks import task_manager

router = APIRouter(prefix="/tasks", tags=["Tasks & Reminders"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class TaskCreateRequest(BaseModel):
    tenant_id: str
    title: str
    description: str = ""
    type: str = "custom"
    priority: str = "medium"
    status: str = "todo"
    assigned_to: str | None = None
    created_by: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    due_date: str | None = None
    due_time: str | None = None
    tags: list[str] = []
    recurring: bool = False
    recurrence_pattern: str | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    type: str | None = None
    priority: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    due_date: str | None = None
    due_time: str | None = None
    tags: list[str] | None = None
    recurring: bool | None = None
    recurrence_pattern: str | None = None


class ReassignRequest(BaseModel):
    new_assignee: str


class ReminderCreateRequest(BaseModel):
    remind_at: str
    method: str = "in_app"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("")
async def create_task(body: TaskCreateRequest):
    """Create a new task."""
    data = body.model_dump(exclude={"tenant_id", "title"}, exclude_none=True)
    task = task_manager.create(tenant_id=body.tenant_id, title=body.title, **data)
    return {"task": _task_to_dict(task)}


@router.get("")
async def list_tasks(
    tenant_id: str,
    assigned_to: str | None = None,
    status: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    due_date: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List tasks with optional filters."""
    tasks = task_manager.list_tasks(
        tenant_id=tenant_id,
        assigned_to=assigned_to,
        status=status,
        entity_type=entity_type,
        entity_id=entity_id,
        due_date=due_date,
        priority=priority,
        limit=limit,
        offset=offset,
    )
    return {"tasks": [_task_to_dict(t) for t in tasks], "total": len(tasks)}


@router.get("/today")
async def get_today_tasks(tenant_id: str, user_id: str):
    """Get tasks due today for a user."""
    tasks = task_manager.get_today(tenant_id, user_id)
    return {"tasks": [_task_to_dict(t) for t in tasks]}


@router.get("/upcoming")
async def get_upcoming_tasks(tenant_id: str, user_id: str, days: int = 7):
    """Get tasks due within the next N days for a user."""
    tasks = task_manager.get_upcoming(tenant_id, user_id, days=days)
    return {"tasks": [_task_to_dict(t) for t in tasks]}


@router.get("/overdue")
async def get_overdue_tasks(tenant_id: str):
    """Get overdue tasks for a tenant."""
    tasks = task_manager.get_overdue(tenant_id)
    return {"tasks": [_task_to_dict(t) for t in tasks]}


@router.get("/stats")
async def get_task_stats(tenant_id: str, user_id: str | None = None):
    """Get task statistics for a tenant."""
    stats = task_manager.get_task_stats(tenant_id, user_id=user_id)
    return {"stats": stats}


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get a single task by ID."""
    task = task_manager.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": _task_to_dict(task)}


@router.put("/{task_id}")
async def update_task(task_id: str, body: TaskUpdateRequest):
    """Update a task."""
    data = body.model_dump(exclude_none=True)
    task = task_manager.update(task_id, **data)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": _task_to_dict(task)}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    ok = task_manager.delete(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@router.post("/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as done."""
    task = task_manager.complete(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": _task_to_dict(task)}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a task."""
    task = task_manager.cancel(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": _task_to_dict(task)}


@router.post("/{task_id}/reassign")
async def reassign_task(task_id: str, body: ReassignRequest):
    """Reassign a task to another user."""
    task = task_manager.reassign(task_id, body.new_assignee)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task": _task_to_dict(task)}


@router.post("/{task_id}/reminders")
async def add_reminder(task_id: str, body: ReminderCreateRequest):
    """Add a reminder to a task."""
    reminder = task_manager.add_reminder(task_id, body.remind_at, body.method)
    if reminder is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "reminder": {
            "id": reminder.id,
            "task_id": reminder.task_id,
            "remind_at": reminder.remind_at,
            "method": reminder.method,
            "sent": reminder.sent,
        }
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_to_dict(task) -> dict:
    """Convert a Task dataclass to a JSON-friendly dict."""
    return {
        "id": task.id,
        "tenant_id": task.tenant_id,
        "title": task.title,
        "description": task.description,
        "type": task.type.value if hasattr(task.type, "value") else task.type,
        "priority": task.priority.value if hasattr(task.priority, "value") else task.priority,
        "status": task.status.value if hasattr(task.status, "value") else task.status,
        "assigned_to": task.assigned_to,
        "created_by": task.created_by,
        "entity_type": task.entity_type,
        "entity_id": task.entity_id,
        "due_date": task.due_date,
        "due_time": task.due_time,
        "completed_at": task.completed_at,
        "tags": task.tags,
        "recurring": task.recurring,
        "recurrence_pattern": task.recurrence_pattern,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
