"""API endpoints for Goals & OKR tracking."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.goals import (
    GoalManager,
    GoalPeriod,
    GoalStatus,
    GoalType,
    goal_manager,
)

router = APIRouter(prefix="/goals", tags=["Goals & OKR"])


# --- Request / Response Models ---


class GoalCreateRequest(BaseModel):
    tenant_id: str
    title: str
    type: str  # GoalType value
    target_value: float
    unit: str
    period: str  # GoalPeriod value
    period_start: str
    period_end: str
    user_id: str | None = None
    parent_goal_id: str | None = None


class GoalUpdateRequest(BaseModel):
    title: str | None = None
    target_value: float | None = None
    unit: str | None = None
    period: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    user_id: str | None = None


class ProgressRequest(BaseModel):
    value: float
    mode: str = "set"  # "set" or "increment"


class KeyResultCreateRequest(BaseModel):
    title: str
    target_value: float
    unit: str
    weight: float = 1.0


class KeyResultUpdateRequest(BaseModel):
    current_value: float


# --- Helpers ---


def _serialize_goal(goal) -> dict:
    return {
        "id": goal.id,
        "tenant_id": goal.tenant_id,
        "user_id": goal.user_id,
        "title": goal.title,
        "type": goal.type.value,
        "target_value": goal.target_value,
        "current_value": goal.current_value,
        "unit": goal.unit,
        "period": goal.period.value,
        "period_start": goal.period_start,
        "period_end": goal.period_end,
        "progress_pct": goal.progress_pct,
        "status": goal.status.value,
        "parent_goal_id": goal.parent_goal_id,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
    }


def _serialize_kr(kr) -> dict:
    return {
        "id": kr.id,
        "goal_id": kr.goal_id,
        "title": kr.title,
        "target_value": kr.target_value,
        "current_value": kr.current_value,
        "unit": kr.unit,
        "weight": kr.weight,
        "progress_pct": round(kr.current_value / kr.target_value * 100, 2) if kr.target_value > 0 else 0.0,
        "created_at": kr.created_at,
        "updated_at": kr.updated_at,
    }


# --- Endpoints ---


@router.post("/", status_code=201)
async def create_goal(req: GoalCreateRequest):
    """Create a new goal."""
    try:
        goal = goal_manager.create(
            tenant_id=req.tenant_id,
            title=req.title,
            type=req.type,
            target_value=req.target_value,
            unit=req.unit,
            period=req.period,
            period_start=req.period_start,
            period_end=req.period_end,
            user_id=req.user_id,
            parent_goal_id=req.parent_goal_id,
        )
        return _serialize_goal(goal)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/")
async def list_goals(
    tenant_id: str = Query(...),
    user_id: str | None = None,
    period: str | None = None,
    type: str | None = None,
    limit: int = Query(default=50, le=200),
):
    """List goals with optional filters."""
    try:
        goals = goal_manager.list_goals(
            tenant_id=tenant_id,
            user_id=user_id,
            period=period,
            type=type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    goals = goals[:limit]
    return {"count": len(goals), "goals": [_serialize_goal(g) for g in goals]}


@router.get("/scorecard")
async def team_scorecard(
    tenant_id: str = Query(...),
    period: str | None = None,
):
    """Get the team scorecard with OKR scores grouped by user."""
    try:
        scorecard = goal_manager.get_team_scorecard(tenant_id, period=period)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"scorecard": scorecard}


@router.get("/trending")
async def trending_goals(tenant_id: str = Query(...)):
    """Get goals that are at risk or behind schedule."""
    goals = goal_manager.get_trending(tenant_id)
    return {"count": len(goals), "goals": [_serialize_goal(g) for g in goals]}


@router.get("/{goal_id}")
async def get_goal(goal_id: str):
    """Get a single goal by ID."""
    goal = goal_manager.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _serialize_goal(goal)


@router.put("/{goal_id}")
async def update_goal(goal_id: str, req: GoalUpdateRequest):
    """Update goal fields."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        goal = goal_manager.update(goal_id, **updates)
        return _serialize_goal(goal)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{goal_id}")
async def delete_goal(goal_id: str):
    """Delete a goal and its key results."""
    deleted = goal_manager.delete(goal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"deleted": True, "goal_id": goal_id}


@router.post("/{goal_id}/progress")
async def update_progress(goal_id: str, req: ProgressRequest):
    """Update or increment goal progress."""
    try:
        if req.mode == "increment":
            goal = goal_manager.increment_progress(goal_id, req.value)
        else:
            goal = goal_manager.update_progress(goal_id, req.value)
        return _serialize_goal(goal)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{goal_id}/key-results", status_code=201)
async def add_key_result(goal_id: str, req: KeyResultCreateRequest):
    """Add a key result to a goal."""
    try:
        kr = goal_manager.add_key_result(
            goal_id=goal_id,
            title=req.title,
            target_value=req.target_value,
            unit=req.unit,
            weight=req.weight,
        )
        return _serialize_kr(kr)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/key-results/{kr_id}")
async def update_key_result(kr_id: str, req: KeyResultUpdateRequest):
    """Update a key result's current value."""
    try:
        kr = goal_manager.update_key_result(kr_id, req.current_value)
        return _serialize_kr(kr)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{goal_id}/okr-score")
async def get_okr_score(goal_id: str):
    """Get the weighted OKR score for a goal."""
    try:
        score = goal_manager.get_okr_score(goal_id)
        return {"goal_id": goal_id, "okr_score": score}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{goal_id}/tree")
async def get_goal_tree(goal_id: str):
    """Get the goal tree: parent, self, and children."""
    try:
        tree = goal_manager.get_goal_tree(goal_id)
        return tree
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
