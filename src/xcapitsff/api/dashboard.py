"""Dashboard API — consolidated real-time view of the entire system."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.api.agents_api import orchestrator
from xcapitsff.core.database import get_db
from xcapitsff.core.events import event_bus
from xcapitsff.core.notifications import notification_manager
from xcapitsff.sales.pipeline import get_hot_leads, get_pipeline_funnel, get_pipeline_stats
from xcapitsff.support.sla_monitor import get_sla_dashboard
from xcapitsff.support.tickets import get_overdue_tickets, get_support_stats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
async def full_dashboard(db: AsyncSession = Depends(get_db)):
    """Complete system dashboard — single endpoint for all KPIs."""
    sales_stats = await get_pipeline_stats(db)
    support_stats = await get_support_stats(db)
    funnel = await get_pipeline_funnel(db)
    hot_leads = await get_hot_leads(db, limit=10)
    sla = await get_sla_dashboard(db)
    agent_stats = orchestrator.get_stats()
    event_counts = event_bus.get_event_counts()
    notif_counts = notification_manager.get_counts()

    return {
        "sales": {
            "total_leads": sales_stats.total_leads,
            "avg_score_icp": sales_stats.avg_score_icp,
            "c_level_count": sales_stats.c_level_count,
            "conversion_rate": sales_stats.conversion_rate,
            "by_region": sales_stats.by_region,
            "by_afinidad": sales_stats.by_afinidad,
            "funnel": funnel,
            "hot_leads": [
                {
                    "id": l.id,
                    "company": l.company_name,
                    "score": l.score_icp,
                    "region": l.region if isinstance(l.region, str) else l.region.value,
                    "c_level": l.c_level,
                }
                for l in hot_leads
            ],
        },
        "support": {
            "total_tickets": support_stats.total_tickets,
            "open_tickets": support_stats.open_tickets,
            "avg_resolution_hours": support_stats.avg_resolution_hours,
            "by_priority": support_stats.by_priority,
            "by_category": support_stats.by_category,
            "sla": sla["summary"],
        },
        "agents": agent_stats,
        "events": {
            "recent_count": len(event_bus.get_recent_events(50)),
            "by_type": event_counts,
        },
        "notifications": notif_counts,
    }


@router.get("/sales")
async def sales_dashboard(db: AsyncSession = Depends(get_db)):
    """Sales-focused dashboard."""
    stats = await get_pipeline_stats(db)
    funnel = await get_pipeline_funnel(db)
    hot = await get_hot_leads(db, limit=20)

    return {
        "stats": {
            "total_leads": stats.total_leads,
            "avg_score_icp": stats.avg_score_icp,
            "c_level_count": stats.c_level_count,
            "conversion_rate": stats.conversion_rate,
        },
        "by_region": stats.by_region,
        "by_afinidad": stats.by_afinidad,
        "pipeline": stats.by_stage,
        "funnel": funnel,
        "hot_leads": [
            {
                "id": l.id,
                "company": l.company_name,
                "score": l.score_icp,
                "c_level": l.c_level,
                "stage": l.stage if isinstance(l.stage, str) else l.stage.value,
            }
            for l in hot
        ],
    }


@router.get("/support")
async def support_dashboard(db: AsyncSession = Depends(get_db)):
    """Support-focused dashboard with SLA status."""
    stats = await get_support_stats(db)
    sla = await get_sla_dashboard(db)
    overdue = await get_overdue_tickets(db)

    return {
        "stats": {
            "total_tickets": stats.total_tickets,
            "open_tickets": stats.open_tickets,
            "avg_resolution_hours": stats.avg_resolution_hours,
        },
        "by_priority": stats.by_priority,
        "by_status": stats.by_status,
        "by_category": stats.by_category,
        "sla": sla,
        "overdue_tickets": [
            {
                "id": t.id,
                "subject": t.subject,
                "priority": t.priority,
                "sla_deadline": str(t.sla_deadline),
            }
            for t in overdue[:10]
        ],
    }
