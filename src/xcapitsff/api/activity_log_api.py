"""API endpoints for the enhanced activity log."""

from datetime import datetime

from fastapi import APIRouter, Query

from xcapitsff.core.activity_log import activity_log

router = APIRouter(prefix="/activity", tags=["Activity Log"])


def _serialize(e) -> dict:
    return {
        "id": e.id,
        "tenant_id": e.tenant_id,
        "user_id": e.user_id,
        "action": e.action,
        "entity_type": e.entity_type,
        "entity_id": e.entity_id,
        "description": e.description,
        "changes": e.changes,
        "ip_address": e.ip_address,
        "user_agent": e.user_agent,
        "created_at": e.created_at.isoformat(),
    }


@router.get("/")
async def get_activity_entries(
    tenant_id: str = Query(default="default"),
    entity_type: str | None = None,
    entity_id: str | None = None,
    user_id: str | None = None,
    action: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Get activity entries with optional filters."""
    entries = activity_log.get_entries(
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(entries),
        "entries": [_serialize(e) for e in entries],
    }


@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_history(entity_type: str, entity_id: str):
    """Get full activity history for a specific entity."""
    entries = activity_log.get_entity_history(entity_type, entity_id)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "count": len(entries),
        "history": [_serialize(e) for e in entries],
    }


@router.get("/summary")
async def get_activity_summary(
    tenant_id: str = Query(default="default"),
    days: int = Query(default=7, ge=1, le=365),
):
    """Get activity summary for the last N days."""
    return activity_log.get_activity_summary(tenant_id, days=days)


@router.get("/export")
async def export_audit_trail(
    tenant_id: str = Query(default="default"),
    start_date: str = Query(..., description="ISO date, e.g. 2026-01-01"),
    end_date: str = Query(..., description="ISO date, e.g. 2026-12-31"),
):
    """Export activity entries for compliance / external audit."""
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    records = activity_log.export_audit_trail(tenant_id, start, end)
    return {
        "count": len(records),
        "records": records,
    }
