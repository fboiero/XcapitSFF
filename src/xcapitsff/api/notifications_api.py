"""API endpoints for notifications."""

from fastapi import APIRouter, Query

from xcapitsff.core.notifications import NotificationPriority, notification_manager

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
async def list_notifications(
    limit: int = Query(default=50, le=200),
    priority: str | None = None,
):
    """Get recent notifications."""
    prio = None
    if priority:
        try:
            prio = NotificationPriority(priority)
        except ValueError:
            pass

    notifications = notification_manager.get_notifications(limit=limit, priority=prio)
    return {
        "count": len(notifications),
        "notifications": [
            {
                "title": n.title,
                "body": n.body,
                "channel": n.channel.value,
                "priority": n.priority.value,
                "event_type": n.event_type,
                "created_at": n.created_at.isoformat(),
                "sent": n.sent,
            }
            for n in reversed(notifications)  # newest first
        ],
    }


@router.get("/counts")
async def notification_counts():
    """Get notification counts by priority."""
    return notification_manager.get_counts()
