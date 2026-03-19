"""Activity Feed — records and queries all business activity for the tenant.

Automatically subscribes to the EventBus to capture activities from events
emitted across the system (lead creation, ticket resolution, outreach, etc.).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any

from xcapitsff.core.events import Event, EventBus, EventType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ActivityEntry:
    """A single activity record in the feed."""

    entry_id: str
    actor: str  # user or agent name
    action: str  # verb — e.g. "created", "resolved", "sent"
    entity_type: str  # "lead", "ticket", "customer", "outreach"
    entity_id: int | str
    entity_name: str  # human-readable name of the entity
    description: str  # full description of what happened
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ActivityFeed
# ---------------------------------------------------------------------------


class ActivityFeed:
    """Records and queries activity for a tenant / user session."""

    def __init__(self) -> None:
        self._entries: list[ActivityEntry] = []
        self._max_entries = 5000

    # -- Recording ----------------------------------------------------------

    def record(
        self,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: int | str,
        entity_name: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> ActivityEntry:
        """Log an activity entry and return it."""
        entry = ActivityEntry(
            entry_id=str(uuid.uuid4())[:12],
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            timestamp=datetime.now(),
            metadata=metadata or {},
        )
        self._entries.append(entry)

        # Cap in-memory storage
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        logger.debug(
            "Activity recorded: [%s] %s %s %s/%s",
            entry.entry_id,
            actor,
            action,
            entity_type,
            entity_id,
        )
        return entry

    # -- Queries ------------------------------------------------------------

    def get_feed(
        self,
        limit: int = 50,
        entity_type: str | None = None,
        actor: str | None = None,
    ) -> list[ActivityEntry]:
        """Return recent activity entries, optionally filtered."""
        entries = self._entries
        if entity_type:
            entries = [e for e in entries if e.entity_type == entity_type]
        if actor:
            entries = [e for e in entries if e.actor == actor]
        # Most recent first
        return list(reversed(entries[-limit:]))

    def get_entity_feed(
        self,
        entity_type: str,
        entity_id: int | str,
    ) -> list[ActivityEntry]:
        """Return all activity for a specific entity, most recent first."""
        entries = [
            e
            for e in self._entries
            if e.entity_type == entity_type and e.entity_id == entity_id
        ]
        return list(reversed(entries))

    def get_today_summary(self) -> dict[str, Any]:
        """Return a summary of today's activity grouped by action type."""
        today = date.today()
        today_entries = [
            e for e in self._entries if e.timestamp.date() == today
        ]

        by_action: dict[str, int] = {}
        by_entity_type: dict[str, int] = {}
        actors: set[str] = set()

        for entry in today_entries:
            by_action[entry.action] = by_action.get(entry.action, 0) + 1
            by_entity_type[entry.entity_type] = (
                by_entity_type.get(entry.entity_type, 0) + 1
            )
            actors.add(entry.actor)

        return {
            "date": today.isoformat(),
            "total_activities": len(today_entries),
            "by_action": by_action,
            "by_entity_type": by_entity_type,
            "active_actors": sorted(actors),
        }

    @property
    def total_entries(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# EventBus auto-recording
# ---------------------------------------------------------------------------

# Mapping from EventType to (action_verb, description_template, entity_type_key)
_EVENT_DESCRIPTORS: dict[EventType, tuple[str, str, str]] = {
    EventType.LEAD_CREATED: (
        "created",
        "Lead creado: {company}",
        "lead",
    ),
    EventType.LEAD_QUALIFIED: (
        "qualified",
        "Lead calificado: {company} (score: {score})",
        "lead",
    ),
    EventType.LEAD_UPDATED: (
        "updated",
        "Lead actualizado: {company}",
        "lead",
    ),
    EventType.LEAD_STAGE_CHANGED: (
        "stage_changed",
        "Lead cambio de etapa: {company} -> {stage}",
        "lead",
    ),
    EventType.LEAD_SCORED: (
        "scored",
        "Lead puntuado: {company} (score: {score})",
        "lead",
    ),
    EventType.LEADS_IMPORTED: (
        "imported",
        "Leads importados: {count} registros",
        "lead",
    ),
    EventType.TICKET_CREATED: (
        "created",
        "Ticket creado: {subject}",
        "ticket",
    ),
    EventType.TICKET_UPDATED: (
        "updated",
        "Ticket actualizado: {subject}",
        "ticket",
    ),
    EventType.TICKET_ESCALATED: (
        "escalated",
        "Ticket escalado: {subject}",
        "ticket",
    ),
    EventType.TICKET_RESOLVED: (
        "resolved",
        "Ticket resuelto: {subject}",
        "ticket",
    ),
    EventType.TICKET_SLA_BREACHED: (
        "sla_breached",
        "SLA incumplido en ticket: {subject}",
        "ticket",
    ),
    EventType.TICKET_MESSAGE_ADDED: (
        "message_added",
        "Mensaje agregado al ticket: {subject}",
        "ticket",
    ),
    EventType.CUSTOMER_CREATED: (
        "created",
        "Cliente creado: {company}",
        "customer",
    ),
    EventType.OUTREACH_SENT: (
        "sent",
        "Outreach enviado a {lead}",
        "outreach",
    ),
    EventType.OUTREACH_REPLIED: (
        "replied",
        "Respuesta de outreach: {lead}",
        "outreach",
    ),
    EventType.AGENT_TASK_STARTED: (
        "task_started",
        "Tarea de agente iniciada: {task}",
        "agent",
    ),
    EventType.AGENT_TASK_COMPLETED: (
        "task_completed",
        "Tarea de agente completada: {task}",
        "agent",
    ),
    EventType.AGENT_TASK_FAILED: (
        "task_failed",
        "Tarea de agente fallida: {task}",
        "agent",
    ),
}


def _extract_description(template: str, data: dict[str, Any]) -> str:
    """Safely render a description template with event data."""
    safe_data = {
        "company": data.get("company_name", data.get("company", "N/A")),
        "score": data.get("score", data.get("score_icp", "N/A")),
        "stage": data.get("stage", "N/A"),
        "count": data.get("count", data.get("imported", "N/A")),
        "subject": data.get("subject", "N/A"),
        "lead": data.get("lead", data.get("lead_name", data.get("company_name", "N/A"))),
        "task": data.get("task", data.get("task_name", "N/A")),
    }
    try:
        return template.format(**safe_data)
    except (KeyError, ValueError, IndexError):
        return template


def _extract_entity_name(entity_type: str, data: dict[str, Any]) -> str:
    """Extract a human-readable entity name from event data."""
    if entity_type == "lead":
        return data.get("company_name", data.get("company", "Lead"))
    if entity_type == "ticket":
        return data.get("subject", "Ticket")
    if entity_type == "customer":
        return data.get("company_name", data.get("company", "Customer"))
    if entity_type == "outreach":
        return data.get("lead", data.get("lead_name", "Outreach"))
    if entity_type == "agent":
        return data.get("task", data.get("task_name", "Agent task"))
    return "Unknown"


def _extract_entity_id(data: dict[str, Any]) -> int | str:
    """Extract entity ID from event data, trying common key names."""
    for key in ("lead_id", "ticket_id", "customer_id", "entity_id", "id"):
        val = data.get(key)
        if val is not None:
            return val
    return 0


def setup_activity_feed(event_bus: EventBus, feed: ActivityFeed) -> None:
    """Subscribe the activity feed to all relevant events on the bus.

    Call this once during application startup (lifespan).
    """

    async def _handle_event(event: Event) -> None:
        descriptor = _EVENT_DESCRIPTORS.get(event.type)
        if descriptor is None:
            return

        action, desc_template, entity_type = descriptor
        description = _extract_description(desc_template, event.data)
        entity_name = _extract_entity_name(entity_type, event.data)
        entity_id = _extract_entity_id(event.data)

        feed.record(
            actor=event.source,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            metadata=dict(event.data),
        )

    event_bus.subscribe_all(_handle_event)
    logger.info("Activity feed subscribed to EventBus")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

activity_feed = ActivityFeed()
