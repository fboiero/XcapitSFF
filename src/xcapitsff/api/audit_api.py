"""API endpoints for audit log."""

from fastapi import APIRouter, Query

from xcapitsff.core.audit import AuditAction, audit_log

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/")
async def get_audit_entries(
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    actor: str | None = None,
    limit: int = Query(default=100, le=500),
):
    """Query audit log entries with optional filters."""
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            pass

    entries = audit_log.query(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action_enum,
        actor=actor,
        limit=limit,
    )

    return {
        "count": len(entries),
        "entries": [
            {
                "action": e.action.value,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "actor": e.actor,
                "changes": e.changes,
                "metadata": e.metadata,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in reversed(entries)
        ],
    }


@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_history(entity_type: str, entity_id: int):
    """Get full audit history for a specific entity."""
    entries = audit_log.get_entity_history(entity_type, entity_id)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "count": len(entries),
        "history": [
            {
                "action": e.action.value,
                "actor": e.actor,
                "changes": e.changes,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ],
    }


@router.get("/stats")
async def get_audit_stats():
    """Get audit log statistics."""
    return audit_log.get_stats()
