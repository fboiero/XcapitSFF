"""API endpoints for Lead Leaderboard."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.sales.leaderboard import (
    get_c_level_leaderboard,
    get_ready_for_outreach,
    get_top_leads_leaderboard,
)

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


def _serialize_leaderboard(lb) -> dict:
    return {
        "title": lb.title,
        "generated_at": lb.generated_at.isoformat(),
        "total_leads": lb.total_leads,
        "entries": [
            {
                "rank": e.rank,
                "lead_id": e.lead_id,
                "company_name": e.company_name,
                "contact_name": e.contact_name,
                "region": e.region,
                "score_icp": e.score_icp,
                "c_level": e.c_level,
                "afinidad": e.afinidad,
                "stage": e.stage,
                "outreach_count": e.outreach_count,
                "days_in_pipeline": e.days_in_pipeline,
            }
            for e in lb.entries
        ],
    }


@router.get("/top")
async def api_top_leads(
    limit: int = Query(default=25, le=100),
    region: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    lb = await get_top_leads_leaderboard(db, limit=limit, region=region)
    return _serialize_leaderboard(lb)


@router.get("/c-level")
async def api_c_level_leaderboard(
    limit: int = Query(default=25, le=100),
    db: AsyncSession = Depends(get_db),
):
    lb = await get_c_level_leaderboard(db, limit=limit)
    return _serialize_leaderboard(lb)


@router.get("/ready-for-outreach")
async def api_ready_for_outreach(
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
):
    lb = await get_ready_for_outreach(db, limit=limit)
    return _serialize_leaderboard(lb)
