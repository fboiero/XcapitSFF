"""Notification center — user-facing notification inbox with read/archive state.

Unlike the existing notifications module (which handles event→alert routing),
this module provides a per-user notification inbox with read/unread tracking,
archival, feed grouping, and multi-tenant isolation.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    MENTION = "mention"
    ASSIGNMENT = "assignment"
    SLA_BREACH = "sla_breach"
    LEAD_HOT = "lead_hot"
    DEAL_WON = "deal_won"
    DEAL_LOST = "deal_lost"
    TICKET_ESCALATED = "ticket_escalated"
    CAMPAIGN_COMPLETED = "campaign_completed"
    SYSTEM = "system"


@dataclass
class Notification:
    id: str
    tenant_id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    link: str | None = None
    read: bool = False
    archived: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    read_at: datetime | None = None
    metadata: dict = field(default_factory=dict)


class NotificationCenter:
    """Per-user notification inbox with multi-tenant isolation."""

    def __init__(self) -> None:
        self._notifications: list[Notification] = []
        # Track known users per tenant for notify_all
        self._tenant_users: dict[str, set[str]] = {}

    def _register_user(self, tenant_id: str, user_id: str) -> None:
        """Track user as belonging to a tenant."""
        if tenant_id not in self._tenant_users:
            self._tenant_users[tenant_id] = set()
        self._tenant_users[tenant_id].add(user_id)

    def notify(
        self,
        tenant_id: str,
        user_id: str,
        type: NotificationType,
        title: str,
        message: str,
        link: str | None = None,
        metadata: dict | None = None,
    ) -> Notification:
        """Create a notification for a specific user."""
        self._register_user(tenant_id, user_id)
        notification = Notification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
            metadata=metadata or {},
        )
        self._notifications.append(notification)
        logger.info(
            "Notification created: [%s] %s for user %s",
            type.value,
            title,
            user_id,
        )
        return notification

    def notify_all(
        self,
        tenant_id: str,
        type: NotificationType,
        title: str,
        message: str,
        link: str | None = None,
        metadata: dict | None = None,
    ) -> list[Notification]:
        """Create a notification for all users in a tenant."""
        users = self._tenant_users.get(tenant_id, set())
        results: list[Notification] = []
        for user_id in users:
            n = self.notify(tenant_id, user_id, type, title, message, link, metadata)
            results.append(n)
        return results

    def get_notifications(
        self,
        tenant_id: str,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get notifications for a user, newest first."""
        result = [
            n
            for n in self._notifications
            if n.tenant_id == tenant_id
            and n.user_id == user_id
            and not n.archived
        ]
        if unread_only:
            result = [n for n in result if not n.read]
        # Newest first
        result = list(reversed(result))
        return result[offset : offset + limit]

    def mark_read(self, notification_id: str) -> bool:
        """Mark a single notification as read."""
        for n in self._notifications:
            if n.id == notification_id:
                if not n.read:
                    n.read = True
                    n.read_at = datetime.now()
                return True
        return False

    def mark_all_read(self, tenant_id: str, user_id: str) -> int:
        """Mark all unread notifications as read for a user. Returns count."""
        count = 0
        now = datetime.now()
        for n in self._notifications:
            if (
                n.tenant_id == tenant_id
                and n.user_id == user_id
                and not n.read
            ):
                n.read = True
                n.read_at = now
                count += 1
        return count

    def archive(self, notification_id: str) -> bool:
        """Archive a notification so it no longer appears in the feed."""
        for n in self._notifications:
            if n.id == notification_id:
                n.archived = True
                return True
        return False

    def get_unread_count(self, tenant_id: str, user_id: str) -> int:
        """Count unread, non-archived notifications."""
        return sum(
            1
            for n in self._notifications
            if n.tenant_id == tenant_id
            and n.user_id == user_id
            and not n.read
            and not n.archived
        )

    def delete_old(self, days: int = 90) -> int:
        """Remove notifications older than *days*. Returns count deleted."""
        cutoff = datetime.now() - timedelta(days=days)
        before = len(self._notifications)
        self._notifications = [
            n for n in self._notifications if n.created_at >= cutoff
        ]
        deleted = before - len(self._notifications)
        if deleted:
            logger.info("Deleted %d old notifications (older than %d days)", deleted, days)
        return deleted

    def get_notification_feed(
        self,
        tenant_id: str,
        user_id: str,
    ) -> dict:
        """Return notifications grouped by date bucket.

        Buckets: today, yesterday, this_week, older.
        """
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=today_start.weekday())

        all_notifs = [
            n
            for n in self._notifications
            if n.tenant_id == tenant_id
            and n.user_id == user_id
            and not n.archived
        ]
        # Newest first
        all_notifs.sort(key=lambda n: n.created_at, reverse=True)

        buckets: dict[str, list[Notification]] = {
            "today": [],
            "yesterday": [],
            "this_week": [],
            "older": [],
        }

        for n in all_notifs:
            if n.created_at >= today_start:
                buckets["today"].append(n)
            elif n.created_at >= yesterday_start:
                buckets["yesterday"].append(n)
            elif n.created_at >= week_start:
                buckets["this_week"].append(n)
            else:
                buckets["older"].append(n)

        return buckets


# Singleton
notification_center = NotificationCenter()
