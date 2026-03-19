"""Audit log — tracks all state changes for compliance and debugging.

Every significant action (lead created, ticket resolved, stage changed, etc.)
is recorded with who did it, when, and what changed.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    STAGE_CHANGE = "stage_change"
    QUALIFY = "qualify"
    SCORE = "score"
    ASSIGN = "assign"
    RESOLVE = "resolve"
    ESCALATE = "escalate"
    IMPORT = "import"
    OUTREACH_SENT = "outreach_sent"
    WEBHOOK_RECEIVED = "webhook_received"


@dataclass
class AuditEntry:
    action: AuditAction
    entity_type: str  # lead, ticket, customer, outreach
    entity_id: int | str
    actor: str  # user, agent name, system
    changes: dict = field(default_factory=dict)  # {"field": {"old": x, "new": y}}
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return (
            f"[{self.timestamp.isoformat()}] {self.action.value} "
            f"{self.entity_type}#{self.entity_id} by {self.actor}"
        )


class AuditLog:
    """In-memory audit log with query capabilities.

    In production, this would write to a database table or external
    audit service. For now, it's in-memory with query support.
    """

    def __init__(self, max_entries: int = 10000):
        self._entries: list[AuditEntry] = []
        self._max_entries = max_entries

    def record(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: int | str,
        actor: str = "system",
        changes: dict | None = None,
        metadata: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            changes=changes or {},
            metadata=metadata or {},
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        logger.info(str(entry))
        return entry

    def query(
        self,
        entity_type: str | None = None,
        entity_id: int | str | None = None,
        action: AuditAction | None = None,
        actor: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results = list(self._entries)

        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        if entity_id is not None:
            results = [e for e in results if e.entity_id == entity_id]
        if action:
            results = [e for e in results if e.action == action]
        if actor:
            results = [e for e in results if e.actor == actor]

        return results[-limit:]

    def get_entity_history(self, entity_type: str, entity_id: int | str) -> list[AuditEntry]:
        return [
            e for e in self._entries
            if e.entity_type == entity_type and e.entity_id == entity_id
        ]

    def get_stats(self) -> dict:
        by_action: dict[str, int] = {}
        by_entity: dict[str, int] = {}
        by_actor: dict[str, int] = {}

        for entry in self._entries:
            by_action[entry.action.value] = by_action.get(entry.action.value, 0) + 1
            by_entity[entry.entity_type] = by_entity.get(entry.entity_type, 0) + 1
            by_actor[entry.actor] = by_actor.get(entry.actor, 0) + 1

        return {
            "total_entries": len(self._entries),
            "by_action": by_action,
            "by_entity_type": by_entity,
            "by_actor": by_actor,
        }

    @property
    def count(self) -> int:
        return len(self._entries)


# Singleton
audit_log = AuditLog()
