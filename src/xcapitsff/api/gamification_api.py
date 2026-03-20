"""API endpoints for Gamification and Usage Insights."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from xcapitsff.selfservice.gamification import GamificationEngine
from xcapitsff.selfservice.usage_insights import UsageInsightsEngine

router = APIRouter(tags=["Gamification"])

# ---------------------------------------------------------------------------
# Shared instances (in production these would be injected via DI)
# ---------------------------------------------------------------------------

_engine = GamificationEngine()
_insights = UsageInsightsEngine()


def get_gamification_engine() -> GamificationEngine:
    return _engine


def get_insights_engine() -> UsageInsightsEngine:
    return _insights


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CheckAchievementsRequest(BaseModel):
    user_id: str
    context: dict


class SetTenantDataRequest(BaseModel):
    tenant_id: str
    data: dict


# ---------------------------------------------------------------------------
# Gamification endpoints
# ---------------------------------------------------------------------------


@router.get("/gamification/achievements")
async def api_all_achievements():
    """Return all available achievements."""
    achievements = _engine.get_all_achievements()
    return [
        {
            "achievement_id": a.achievement_id,
            "name": a.name,
            "description": a.description,
            "icon": a.icon,
            "category": a.category.value,
            "points": a.points,
            "condition_type": a.condition_type,
            "condition_threshold": a.condition_threshold,
        }
        for a in achievements
    ]


@router.get("/gamification/my-achievements")
async def api_my_achievements(user_id: str = Query(..., description="User ID")):
    """Return all achievements (unlocked and in-progress) for a user."""
    user_achievements = _engine.get_user_achievements(user_id)
    return [
        {
            "user_id": ua.user_id,
            "achievement_id": ua.achievement_id,
            "unlocked_at": ua.unlocked_at.isoformat() if ua.unlocked_at else None,
            "progress": ua.progress,
        }
        for ua in user_achievements
    ]


@router.get("/gamification/level")
async def api_user_level(user_id: str = Query(..., description="User ID")):
    """Return the user's current level, points, and progress."""
    return _engine.get_user_level(user_id)


@router.get("/gamification/leaderboard")
async def api_leaderboard(limit: int = Query(10, ge=1, le=100)):
    """Return the top users by points."""
    return _engine.get_leaderboard(limit=limit)


@router.post("/gamification/check")
async def api_check_achievements(req: CheckAchievementsRequest):
    """Check and unlock new achievements based on current context."""
    newly_unlocked = _engine.check_achievements(req.user_id, req.context)
    return {
        "user_id": req.user_id,
        "newly_unlocked": [
            {
                "achievement_id": a.achievement_id,
                "name": a.name,
                "description": a.description,
                "points": a.points,
            }
            for a in newly_unlocked
        ],
        "level": _engine.get_user_level(req.user_id),
    }


# ---------------------------------------------------------------------------
# Usage Insights endpoints
# ---------------------------------------------------------------------------


@router.get("/insights/weekly")
async def api_weekly_insights(tenant_id: str = Query(..., description="Tenant ID")):
    """Return weekly usage insights for a tenant."""
    insights = _insights.generate_weekly_insights(tenant_id)
    return [
        {
            "insight_type": i.insight_type,
            "title": i.title,
            "description": i.description,
            "value": i.value,
            "trend": i.trend,
            "recommendation": i.recommendation,
        }
        for i in insights
    ]


@router.get("/insights/daily")
async def api_daily_digest(tenant_id: str = Query(..., description="Tenant ID")):
    """Return the daily digest for a tenant."""
    return _insights.generate_daily_digest(tenant_id)


@router.get("/insights/adoption")
async def api_feature_adoption(tenant_id: str = Query(..., description="Tenant ID")):
    """Return feature adoption data for a tenant."""
    return _insights.get_feature_adoption(tenant_id)


@router.post("/insights/data")
async def api_set_tenant_data(req: SetTenantDataRequest):
    """Inject tenant metric data (for testing / internal use)."""
    _insights.set_tenant_data(req.tenant_id, req.data)
    return {"status": "ok", "tenant_id": req.tenant_id}
