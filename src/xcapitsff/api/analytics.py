"""API endpoints for Analytics — sales and support dashboards.

This module serves both the original legacy endpoints and the new comprehensive
analytics reports from ``sales.analytics`` and ``support.analytics``.
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.sales.analytics import (
    generate_lead_health_report,
    generate_outreach_effectiveness,
    generate_sales_report,
)
from xcapitsff.sales.pipeline import get_hot_leads, get_pipeline_funnel, get_pipeline_stats
from xcapitsff.support.analytics import (
    generate_agent_performance,
    generate_sla_compliance_report,
    generate_support_report,
)
from xcapitsff.support.tickets import get_overdue_tickets, get_support_stats

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Legacy endpoints (kept for backward compatibility)
# ---------------------------------------------------------------------------


@router.get("/sales/stats")
async def api_sales_stats(db: AsyncSession = Depends(get_db)):
    stats = await get_pipeline_stats(db)
    return stats


@router.get("/sales/funnel")
async def api_sales_funnel(db: AsyncSession = Depends(get_db)):
    funnel = await get_pipeline_funnel(db)
    return {"funnel": funnel}


@router.get("/sales/hot-leads")
async def api_hot_leads(db: AsyncSession = Depends(get_db)):
    leads = await get_hot_leads(db)
    return {
        "count": len(leads),
        "leads": [
            {
                "id": l.id,
                "company": l.company_name,
                "score": l.score_icp,
                "region": l.region,
                "c_level": l.c_level,
                "stage": l.stage,
            }
            for l in leads
        ],
    }


@router.get("/support/stats")
async def api_support_stats(db: AsyncSession = Depends(get_db)):
    return await get_support_stats(db)


@router.get("/support/overdue")
async def api_overdue_tickets(db: AsyncSession = Depends(get_db)):
    tickets = await get_overdue_tickets(db)
    return {
        "count": len(tickets),
        "tickets": [
            {
                "id": t.id,
                "subject": t.subject,
                "priority": t.priority,
                "sla_deadline": str(t.sla_deadline),
                "assigned_agent": t.assigned_agent,
            }
            for t in tickets
        ],
    }


# ---------------------------------------------------------------------------
# New comprehensive analytics endpoints
# ---------------------------------------------------------------------------


@router.get("/sales/report")
async def api_sales_report(
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Full sales report with funnel, scores, distribution, and top leads."""
    report = await generate_sales_report(db, period_days=period_days)
    return asdict(report)


@router.get("/sales/health")
async def api_lead_health(db: AsyncSession = Depends(get_db)):
    """Lead health report: identifies leads with data quality or pipeline issues."""
    report = await generate_lead_health_report(db)
    return asdict(report)


@router.get("/sales/outreach")
async def api_outreach_effectiveness(db: AsyncSession = Depends(get_db)):
    """Outreach effectiveness report: messages sent/replied by channel."""
    report = await generate_outreach_effectiveness(db)
    return asdict(report)


@router.get("/support/report")
async def api_support_report(
    period_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Full support report with resolution rates, SLA, agent performance."""
    report = await generate_support_report(db, period_days=period_days)
    return asdict(report)


@router.get("/support/sla")
async def api_sla_compliance(db: AsyncSession = Depends(get_db)):
    """SLA compliance report: breached vs met by category and priority."""
    report = await generate_sla_compliance_report(db)
    return asdict(report)


@router.get("/support/agents")
async def api_agent_performance(db: AsyncSession = Depends(get_db)):
    """Per-agent performance: tickets handled, resolution time, SLA compliance."""
    agents = await generate_agent_performance(db)
    return {
        "agents": [asdict(a) for a in agents],
        "count": len(agents),
    }


@router.get("/executive")
async def api_executive_summary(db: AsyncSession = Depends(get_db)):
    """Executive dashboard combining sales and support analytics."""
    sales_stats = await get_pipeline_stats(db)
    support_stats = await get_support_stats(db)
    hot_leads = await get_hot_leads(db, limit=5)
    overdue = await get_overdue_tickets(db)

    # Enrich with new analytics
    sales_report = await generate_sales_report(db, period_days=30)
    support_report = await generate_support_report(db, period_days=30)

    return {
        "sales": {
            "total_leads": sales_stats.total_leads,
            "avg_score": sales_stats.avg_score_icp,
            "conversion_rate": sales_stats.conversion_rate,
            "c_level_leads": sales_stats.c_level_count,
            "hot_leads_needing_action": len(hot_leads),
            "pipeline": sales_stats.by_stage,
            "new_leads_30d": sales_report.new_leads,
            "qualified_leads": sales_report.qualified_leads,
            "stale_leads": sales_report.stale_leads_count,
            "c_level_ratio": sales_report.c_level_ratio,
        },
        "support": {
            "total_tickets": support_stats.total_tickets,
            "open_tickets": support_stats.open_tickets,
            "avg_resolution_hours": support_stats.avg_resolution_hours,
            "overdue_tickets": len(overdue),
            "resolution_rate_30d": support_report.resolution_rate,
            "sla_compliance_rate_30d": support_report.sla_compliance_rate,
            "escalation_count_30d": support_report.escalation_count,
        },
        "alerts": _generate_alerts(sales_stats, support_stats, hot_leads, overdue),
    }


def _generate_alerts(sales_stats, support_stats, hot_leads, overdue) -> list[str]:
    alerts = []
    if len(hot_leads) > 0:
        alerts.append(f"{len(hot_leads)} hot leads need immediate outreach")
    if len(overdue) > 0:
        alerts.append(f"{len(overdue)} tickets exceeded SLA — escalation needed")
    if support_stats.open_tickets > 50:
        alerts.append(f"High ticket volume: {support_stats.open_tickets} open tickets")
    if sales_stats.conversion_rate is not None and sales_stats.conversion_rate < 5:
        alerts.append("Low conversion rate — review pipeline strategy")
    return alerts
