"""API endpoints for Smart Inbox and Activity Feed."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.activity import activity_feed
from xcapitsff.core.database import get_db
from xcapitsff.core.inbox import InboxItemType, InboxManager

router = APIRouter(tags=["Inbox & Activity"])

# Module-level inbox manager (reset per request via generate)
_inbox_manager = InboxManager()


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class InboxItemResponse(BaseModel):
    item_id: str
    type: str
    title: str
    subtitle: str
    entity_type: str
    entity_id: int
    priority: int
    action_url: str
    created_at: str
    is_read: bool
    is_acted_on: bool


class InboxCountResponse(BaseModel):
    counts: dict[str, int]
    total: int


class ActivityEntryResponse(BaseModel):
    entry_id: str
    actor: str
    action: str
    entity_type: str
    entity_id: int | str
    entity_name: str
    description: str
    timestamp: str
    metadata: dict


class TodaySummaryResponse(BaseModel):
    date: str
    total_activities: int
    by_action: dict[str, int]
    by_entity_type: dict[str, int]
    active_actors: list[str]


# ---------------------------------------------------------------------------
# Inbox endpoints
# ---------------------------------------------------------------------------


@router.get("/inbox", response_model=list[InboxItemResponse])
async def api_get_inbox(
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get inbox items sorted by priority (most urgent first)."""
    items = await _inbox_manager.generate_inbox(db)
    result = []
    for item in items[:limit]:
        result.append(
            InboxItemResponse(
                item_id=item.item_id,
                type=item.type.value,
                title=item.title,
                subtitle=item.subtitle,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                priority=item.priority,
                action_url=item.action_url,
                created_at=item.created_at.isoformat(),
                is_read=item.is_read,
                is_acted_on=item.is_acted_on,
            )
        )
    return result


@router.get("/inbox/count", response_model=InboxCountResponse)
async def api_inbox_count(db: AsyncSession = Depends(get_db)):
    """Get count of inbox items grouped by type."""
    await _inbox_manager.generate_inbox(db)
    counts = _inbox_manager.get_count_by_type()
    total = sum(counts.values())
    return InboxCountResponse(counts=counts, total=total)


@router.post("/inbox/{item_id}/read")
async def api_mark_read(item_id: str):
    """Mark an inbox item as read."""
    found = _inbox_manager.mark_read(item_id)
    if not found:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    return {"status": "ok", "item_id": item_id, "is_read": True}


@router.post("/inbox/{item_id}/acted")
async def api_mark_acted(item_id: str):
    """Mark an inbox item as acted upon."""
    found = _inbox_manager.mark_acted(item_id)
    if not found:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    return {"status": "ok", "item_id": item_id, "is_acted_on": True}


# ---------------------------------------------------------------------------
# Activity Feed endpoints
# ---------------------------------------------------------------------------


@router.get("/activity", response_model=list[ActivityEntryResponse])
async def api_get_activity(
    limit: int = Query(default=50, le=200),
    entity_type: str | None = None,
    actor: str | None = None,
):
    """Get the activity feed, optionally filtered by entity_type or actor."""
    entries = activity_feed.get_feed(
        limit=limit,
        entity_type=entity_type,
        actor=actor,
    )
    return [
        ActivityEntryResponse(
            entry_id=e.entry_id,
            actor=e.actor,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            entity_name=e.entity_name,
            description=e.description,
            timestamp=e.timestamp.isoformat(),
            metadata=e.metadata,
        )
        for e in entries
    ]


@router.get("/activity/today", response_model=TodaySummaryResponse)
async def api_today_summary():
    """Get a summary of today's activity."""
    summary = activity_feed.get_today_summary()
    return TodaySummaryResponse(**summary)


@router.get("/activity/{entity_type}/{entity_id}", response_model=list[ActivityEntryResponse])
async def api_entity_activity(entity_type: str, entity_id: str):
    """Get all activity for a specific entity."""
    # Try parsing entity_id as int, fall back to string
    try:
        eid: int | str = int(entity_id)
    except ValueError:
        eid = entity_id

    entries = activity_feed.get_entity_feed(entity_type, eid)
    return [
        ActivityEntryResponse(
            entry_id=e.entry_id,
            actor=e.actor,
            action=e.action,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            entity_name=e.entity_name,
            description=e.description,
            timestamp=e.timestamp.isoformat(),
            metadata=e.metadata,
        )
        for e in entries
    ]
