"""System API — configuration, status, and management endpoints."""

import platform
from datetime import datetime

from fastapi import APIRouter

from xcapitsff import __version__
from xcapitsff.api.agents_api import orchestrator
from xcapitsff.config import settings
from xcapitsff.core.events import event_bus
from xcapitsff.core.notifications import notification_manager

router = APIRouter(prefix="/system", tags=["System"])

_startup_time = datetime.now()


@router.get("/info")
async def system_info():
    """System information and version."""
    return {
        "name": "XcapitSFF",
        "version": __version__,
        "description": "Xcapit Software Factory — AI-powered Development, Sales & Support",
        "environment": settings.environment,
        "python_version": platform.python_version(),
        "startup_time": _startup_time.isoformat(),
        "uptime_seconds": (datetime.now() - _startup_time).total_seconds(),
    }


@router.get("/config")
async def system_config():
    """Non-sensitive system configuration."""
    return {
        "environment": settings.environment,
        "log_level": settings.log_level,
        "cors_origins": settings.cors_origin_list,
        "database_type": "postgresql" if "postgresql" in settings.database_url else "sqlite",
        "has_anthropic_key": bool(settings.anthropic_api_key),
    }


@router.get("/status")
async def system_status():
    """Complete system status overview."""
    agent_stats = orchestrator.get_stats()
    event_counts = event_bus.get_event_counts()
    notif_counts = notification_manager.get_counts()

    return {
        "status": "operational",
        "uptime_seconds": (datetime.now() - _startup_time).total_seconds(),
        "agents": {
            "rules_active": agent_stats["rules_count"],
            "tasks_processed": agent_stats["total_tasks_processed"],
            "tasks_pending": agent_stats["pending"],
        },
        "events": {
            "total_emitted": sum(event_counts.values()),
            "by_type": event_counts,
        },
        "notifications": notif_counts,
    }


@router.get("/modules")
async def list_modules():
    """List all available system modules and their status."""
    return {
        "modules": [
            {"name": "sales", "status": "active", "components": ["scoring", "pipeline", "importer", "outreach", "analytics"]},
            {"name": "support", "status": "active", "components": ["tickets", "router", "knowledge", "sla_monitor", "analytics"]},
            {"name": "agents", "status": "active", "components": ["orchestrator", "sales_qualifier", "outreach_composer", "support_responder", "ticket_router"]},
            {"name": "core", "status": "active", "components": ["events", "notifications", "validators", "data_quality"]},
            {"name": "api", "status": "active", "components": ["leads", "tickets", "customers", "knowledge", "analytics", "webhooks", "outreach", "dashboard", "notifications", "agents", "system"]},
        ],
    }
