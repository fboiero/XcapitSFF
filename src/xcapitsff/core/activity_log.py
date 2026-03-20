"""Enhanced activity log — tracks user actions with rich context.

Complements the existing audit module by adding tenant-awareness, user-agent
tracking, time-based analytics, and compliance-ready export.
"""

import logging
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ActivityEntry:
    id: str
    tenant_id: str
    user_id: str
    action: str
    entity_type: str
    entity_id: str | int
    description: str
    changes: dict = field(default_factory=dict)  # {"field": {"before": x, "after": y}}
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


class ActivityLog:
    """In-memory activity log with analytics and export capabilities."""

    def __init__(self) -> None:
        self._entries: list[ActivityEntry] = []

    def log(
        self,
        tenant_id: str,
        user_id: str,
        action: str,
        entity_type: str,
        entity_id: str | int,
        description: str,
        changes: dict | None = None,
        ip: str | None = None,
        ua: str | None = None,
    ) -> ActivityEntry:
        """Record an activity entry."""
        entry = ActivityEntry(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            changes=changes or {},
            ip_address=ip,
            user_agent=ua,
        )
        self._entries.append(entry)
        logger.info(
            "Activity: [%s] %s %s#%s by %s",
            tenant_id,
            action,
            entity_type,
            entity_id,
            user_id,
        )
        return entry

    def get_entries(
        self,
        tenant_id: str,
        entity_type: str | None = None,
        entity_id: str | int | None = None,
        user_id: str | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ActivityEntry]:
        """Get activity entries with optional filters, newest first."""
        result = [e for e in self._entries if e.tenant_id == tenant_id]

        if entity_type is not None:
            result = [e for e in result if e.entity_type == entity_type]
        if entity_id is not None:
            result = [e for e in result if str(e.entity_id) == str(entity_id)]
        if user_id is not None:
            result = [e for e in result if e.user_id == user_id]
        if action is not None:
            result = [e for e in result if e.action == action]

        result = list(reversed(result))
        return result[offset : offset + limit]

    def get_entity_history(
        self,
        entity_type: str,
        entity_id: str | int,
    ) -> list[ActivityEntry]:
        """Full history for a single entity across all tenants."""
        return [
            e
            for e in self._entries
            if e.entity_type == entity_type and str(e.entity_id) == str(entity_id)
        ]

    def get_user_activity(
        self,
        tenant_id: str,
        user_id: str,
        days: int = 30,
    ) -> list[ActivityEntry]:
        """Get recent activity for a specific user."""
        cutoff = datetime.now() - timedelta(days=days)
        return [
            e
            for e in self._entries
            if e.tenant_id == tenant_id
            and e.user_id == user_id
            and e.created_at >= cutoff
        ]

    def get_activity_summary(
        self,
        tenant_id: str,
        days: int = 7,
    ) -> dict:
        """Summarise activity over the last *days*.

        Returns total_actions, by_user, by_action, by_entity_type,
        and most_active_hour (0-23).
        """
        cutoff = datetime.now() - timedelta(days=days)
        entries = [
            e
            for e in self._entries
            if e.tenant_id == tenant_id and e.created_at >= cutoff
        ]

        by_user: dict[str, int] = Counter(e.user_id for e in entries)
        by_action: dict[str, int] = Counter(e.action for e in entries)
        by_entity_type: dict[str, int] = Counter(e.entity_type for e in entries)

        hour_counts: Counter[int] = Counter(e.created_at.hour for e in entries)
        most_active_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0

        return {
            "total_actions": len(entries),
            "by_user": dict(by_user),
            "by_action": dict(by_action),
            "by_entity_type": dict(by_entity_type),
            "most_active_hour": most_active_hour,
        }

    def export_audit_trail(
        self,
        tenant_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict]:
        """Export entries as plain dicts for compliance / external systems."""
        entries = [
            e
            for e in self._entries
            if e.tenant_id == tenant_id
            and start_date <= e.created_at <= end_date
        ]
        return [
            {
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
            for e in entries
        ]


# Singleton
activity_log = ActivityLog()
