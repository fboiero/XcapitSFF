"""API endpoints for the task scheduler.

Exposes the scheduler so operators can inspect task status, manually
trigger tasks, and enable/disable individual scheduled jobs.
"""

from fastapi import APIRouter, HTTPException

from xcapitsff.core.scheduler import scheduler

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


@router.get("/status")
async def get_scheduler_status():
    """Return the status of all scheduled tasks."""
    return scheduler.get_status()


@router.post("/run/{task_name}")
async def run_task(task_name: str):
    """Manually trigger a specific task by name."""
    if task_name not in scheduler.list_tasks():
        raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found")

    result = await scheduler.run_once(task_name)
    return result


@router.post("/toggle/{task_name}")
async def toggle_task(task_name: str):
    """Enable or disable a scheduled task.

    Toggles the ``is_active`` flag and returns the new state.
    """
    tasks = scheduler._tasks
    if task_name not in tasks:
        raise HTTPException(status_code=404, detail=f"Task '{task_name}' not found")

    task = tasks[task_name]
    task.is_active = not task.is_active
    return {
        "task": task_name,
        "is_active": task.is_active,
    }
