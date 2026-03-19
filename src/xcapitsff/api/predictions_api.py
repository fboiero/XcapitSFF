"""API endpoints for Predictive Analytics — forecasting, churn, win/loss."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.sales.predictions import (
    analyze_score_trends,
    analyze_win_loss,
    forecast_pipeline,
    predict_churn,
)

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/pipeline-forecast")
async def api_pipeline_forecast(
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Forecast pipeline conversions and expected revenue index.

    Uses rule-based conversion probabilities considering stage position,
    ICP score, C-level status, afinidad, time decay, and engagement.
    """
    forecast = await forecast_pipeline(db, period_days=period_days)
    return asdict(forecast)


@router.get("/score-trends")
async def api_score_trends(
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Analyze lead score trends to identify engagement patterns.

    Returns leads with their score trajectory (up/down/stable) and
    velocity (score change per week).
    """
    trends = await analyze_score_trends(db, period_days=period_days)
    return {
        "period_days": period_days,
        "total_leads": len(trends),
        "trending_up": sum(1 for t in trends if t.trend == "up"),
        "trending_down": sum(1 for t in trends if t.trend == "down"),
        "stable": sum(1 for t in trends if t.trend == "stable"),
        "leads": [asdict(t) for t in trends],
    }


@router.get("/churn-risk")
async def api_churn_risk(
    db: AsyncSession = Depends(get_db),
):
    """Predict customer churn risk based on support signals.

    Evaluates ticket frequency, resolution times, SLA breaches,
    interaction recency, escalations, and plan type.
    """
    risks = await predict_churn(db)
    return {
        "total_customers": len(risks),
        "high_risk": sum(1 for r in risks if r.risk_level == "high"),
        "medium_risk": sum(1 for r in risks if r.risk_level == "medium"),
        "low_risk": sum(1 for r in risks if r.risk_level == "low"),
        "customers": [asdict(r) for r in risks],
    }


@router.get("/win-loss")
async def api_win_loss(
    db: AsyncSession = Depends(get_db),
):
    """Analyze win/loss patterns to identify success and failure drivers.

    Examines correlations between lead attributes (region, afinidad,
    C-level status, ICP score) and outcomes.
    """
    analysis = await analyze_win_loss(db)
    return asdict(analysis)
