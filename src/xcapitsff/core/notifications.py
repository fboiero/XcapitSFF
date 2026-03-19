"""Notification system — alert routing for business events.

Notifications are triggered by the EventBus and can be sent via:
- Internal log (always)
- Webhook callback (for Slack, Teams, etc.)
- Email (via SMTP, placeholder for now)
- In-app notification queue

This module provides the notification handlers that subscribe to events.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from xcapitsff.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"
    IN_APP = "in_app"


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    title: str
    body: str
    channel: NotificationChannel
    priority: NotificationPriority
    event_type: str
    data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    sent: bool = False


class NotificationManager:
    """Manages notification routing and delivery."""

    def __init__(self):
        self.notifications: list[Notification] = []
        self.rules: list[dict] = []
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Default notification rules mapping events to notifications."""
        self.rules = [
            {
                "event": EventType.TICKET_SLA_BREACHED,
                "title": "SLA Breach: Ticket #{ticket_id}",
                "body": "Ticket #{ticket_id} has breached its SLA by {overdue_hours}h. Immediate attention required.",
                "channel": NotificationChannel.IN_APP,
                "priority": NotificationPriority.CRITICAL,
            },
            {
                "event": EventType.TICKET_ESCALATED,
                "title": "Escalation: Ticket #{ticket_id}",
                "body": "Ticket #{ticket_id} has been escalated. Reason: {reason}",
                "channel": NotificationChannel.IN_APP,
                "priority": NotificationPriority.HIGH,
            },
            {
                "event": EventType.LEAD_QUALIFIED,
                "title": "New Qualified Lead #{lead_id}",
                "body": "Lead #{lead_id} has been qualified with score {score}. Ready for outreach.",
                "channel": NotificationChannel.IN_APP,
                "priority": NotificationPriority.MEDIUM,
            },
            {
                "event": EventType.LEADS_IMPORTED,
                "title": "Leads Import Complete",
                "body": "{count} leads imported successfully.",
                "channel": NotificationChannel.IN_APP,
                "priority": NotificationPriority.LOW,
            },
            {
                "event": EventType.AGENT_TASK_FAILED,
                "title": "Agent Task Failed",
                "body": "Agent {agent_name} failed on task {task_id}: {error}",
                "channel": NotificationChannel.IN_APP,
                "priority": NotificationPriority.HIGH,
            },
        ]

    def _format_template(self, template: str, data: dict) -> str:
        """Safe format with fallback for missing keys."""
        try:
            return template.format(**data)
        except KeyError:
            return template.format_map(
                {k: data.get(k, f"<{k}>") for k in data}
            )

    async def handle_event(self, event: Event) -> None:
        """Process an event and create notifications based on rules."""
        for rule in self.rules:
            if rule["event"] != event.type:
                continue

            # Merge event data for template formatting
            template_data = {**event.data}
            template_data.setdefault("ticket_id", "?")
            template_data.setdefault("lead_id", "?")
            template_data.setdefault("reason", "unknown")
            template_data.setdefault("overdue_hours", "?")
            template_data.setdefault("count", 0)
            template_data.setdefault("score", "?")
            template_data.setdefault("agent_name", "?")
            template_data.setdefault("task_id", "?")
            template_data.setdefault("error", "?")

            notification = Notification(
                title=self._format_template(rule["title"], template_data),
                body=self._format_template(rule["body"], template_data),
                channel=rule["channel"],
                priority=rule["priority"],
                event_type=event.type.value,
                data=event.data,
            )

            self.notifications.append(notification)
            await self._deliver(notification)

    async def _deliver(self, notification: Notification) -> None:
        """Deliver a notification via the appropriate channel."""
        if notification.channel == NotificationChannel.LOG:
            logger.info(f"[NOTIFICATION] {notification.title}: {notification.body}")
        elif notification.channel == NotificationChannel.IN_APP:
            logger.info(f"[IN-APP] {notification.priority.value.upper()}: {notification.title}")
        elif notification.channel == NotificationChannel.WEBHOOK:
            # In production, this would POST to a webhook URL
            logger.info(f"[WEBHOOK] {notification.title}")
        elif notification.channel == NotificationChannel.EMAIL:
            # In production, this would send an email
            logger.info(f"[EMAIL] {notification.title}")

        notification.sent = True

    def get_notifications(
        self,
        limit: int = 50,
        priority: NotificationPriority | None = None,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Get recent notifications with optional filtering."""
        result = list(self.notifications)
        if priority:
            result = [n for n in result if n.priority == priority]
        if unread_only:
            result = [n for n in result if not n.sent]
        return result[-limit:]

    def get_counts(self) -> dict[str, int]:
        """Get notification counts by priority."""
        counts: dict[str, int] = {"total": len(self.notifications)}
        for p in NotificationPriority:
            counts[p.value] = len([n for n in self.notifications if n.priority == p])
        return counts


# Singleton
notification_manager = NotificationManager()


def setup_notifications() -> None:
    """Subscribe the notification manager to the event bus."""
    event_bus.subscribe_all(notification_manager.handle_event)
    logger.info("Notification manager subscribed to event bus")
