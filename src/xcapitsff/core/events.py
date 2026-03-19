"""Event bus — internal pub/sub for decoupling modules.

Events flow: Module emits event → handlers process it → side effects.
This enables the agent orchestrator to react to business events automatically.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    # Lead events
    LEAD_CREATED = "lead.created"
    LEAD_UPDATED = "lead.updated"
    LEAD_QUALIFIED = "lead.qualified"
    LEAD_STAGE_CHANGED = "lead.stage_changed"
    LEAD_SCORED = "lead.scored"
    LEADS_IMPORTED = "leads.imported"

    # Ticket events
    TICKET_CREATED = "ticket.created"
    TICKET_UPDATED = "ticket.updated"
    TICKET_ESCALATED = "ticket.escalated"
    TICKET_RESOLVED = "ticket.resolved"
    TICKET_SLA_BREACHED = "ticket.sla_breached"
    TICKET_MESSAGE_ADDED = "ticket.message_added"

    # Customer events
    CUSTOMER_CREATED = "customer.created"

    # Outreach events
    OUTREACH_SENT = "outreach.sent"
    OUTREACH_REPLIED = "outreach.replied"

    # Agent events
    AGENT_TASK_STARTED = "agent.task_started"
    AGENT_TASK_COMPLETED = "agent.task_completed"
    AGENT_TASK_FAILED = "agent.task_failed"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            import uuid
            self.event_id = str(uuid.uuid4())[:8]


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Simple async event bus for internal module communication."""

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
        self._event_log: list[Event] = []
        self._max_log_size = 1000

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Handler subscribed to {event_type.value}")

    def subscribe_all(self, handler: EventHandler) -> None:
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h != handler
            ]

    async def emit(self, event: Event) -> None:
        self._log_event(event)
        logger.info(f"Event emitted: {event.type.value} [{event.event_id}]")

        handlers = list(self._global_handlers)
        handlers.extend(self._handlers.get(event.type, []))

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Handler error for {event.type.value}: {e}",
                    exc_info=True,
                )

    async def emit_nowait(self, event: Event) -> None:
        """Emit event without waiting for handlers to complete."""
        self._log_event(event)
        logger.info(f"Event emitted (async): {event.type.value} [{event.event_id}]")

        handlers = list(self._global_handlers)
        handlers.extend(self._handlers.get(event.type, []))

        for handler in handlers:
            asyncio.create_task(self._safe_handle(handler, event))

    async def _safe_handle(self, handler: EventHandler, event: Event) -> None:
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Async handler error for {event.type.value}: {e}")

    def _log_event(self, event: Event) -> None:
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

    def get_recent_events(self, limit: int = 50, event_type: EventType | None = None) -> list[Event]:
        events = self._event_log
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def get_event_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in self._event_log:
            key = event.type.value
            counts[key] = counts.get(key, 0) + 1
        return counts


# Singleton event bus
event_bus = EventBus()
