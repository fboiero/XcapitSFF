"""Execution Engine API — trigger execution ticks and inspect running tasks."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from xcapitsff.agents.execution_engine import execution_engine

router = APIRouter(prefix="/execution", tags=["Execution Engine"])


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


def _check_engine():
    """Return the engine or raise 503 if not initialized."""
    # Re-import to get the current module-level value
    from xcapitsff.agents.execution_engine import execution_engine as _engine
    if _engine is None:
        raise HTTPException(
            status_code=503,
            detail="Execution engine not initialized",
        )
    return _engine


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/tick")
def trigger_tick():
    """Manually trigger one execution tick."""
    engine = _check_engine()
    processed = engine.tick()
    return {"processed_task_ids": processed}


@router.post("/tasks/{task_id}/execute")
def execute_task(task_id: str):
    """Manually execute a specific task."""
    engine = _check_engine()
    record = engine.execute_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Task not found or no agent available")
    return _serialize(record)


@router.get("/running")
def get_running():
    """Get currently running tasks."""
    engine = _check_engine()
    running = engine.get_running_tasks()
    return {k: _serialize(v) for k, v in running.items()}


@router.get("/history")
def get_history(workspace_id: Optional[str] = None, limit: int = 50):
    """Get execution history."""
    engine = _check_engine()
    records = engine.get_execution_history(workspace_id=workspace_id, limit=limit)
    return [_serialize(r) for r in records]


@router.get("/stats")
def execution_stats():
    """Get execution engine statistics."""
    engine = _check_engine()
    return engine.get_stats()
