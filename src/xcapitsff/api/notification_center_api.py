"""API endpoints for the notification center."""

from fastapi import APIRouter, Query

from xcapitsff.core.notification_center import notification_center

router = APIRouter(prefix="/notification-center", tags=["Notification Center"])


def _serialize(n) -> dict:
    return {
        "id": n.id,
        "tenant_id": n.tenant_id,
        "user_id": n.user_id,
        "type": n.type.value,
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "read": n.read,
        "archived": n.archived,
        "created_at": n.created_at.isoformat(),
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "metadata": n.metadata,
    }


@router.get("/")
async def get_notification_feed(
    tenant_id: str = Query(default="default"),
    user_id: str = Query(default="current"),
):
    """Get notification feed grouped by date."""
    feed = notification_center.get_notification_feed(tenant_id, user_id)
    return {
        "feed": {
            bucket: [_serialize(n) for n in notifs]
            for bucket, notifs in feed.items()
        },
    }


@router.get("/count")
async def get_unread_count(
    tenant_id: str = Query(default="default"),
    user_id: str = Query(default="current"),
):
    """Get unread notification count."""
    return {"unread_count": notification_center.get_unread_count(tenant_id, user_id)}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str):
    """Mark a single notification as read."""
    ok = notification_center.mark_read(notification_id)
    return {"success": ok}


@router.post("/read-all")
async def mark_all_read(
    tenant_id: str = Query(default="default"),
    user_id: str = Query(default="current"),
):
    """Mark all notifications as read for the current user."""
    count = notification_center.mark_all_read(tenant_id, user_id)
    return {"marked_read": count}


@router.post("/{notification_id}/archive")
async def archive_notification(notification_id: str):
    """Archive a notification."""
    ok = notification_center.archive(notification_id)
    return {"success": ok}
