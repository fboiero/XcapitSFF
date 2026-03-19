"""Notification Preferences — user controls what alerts they receive.

Each user can configure which notifications they want, via which channel,
and at what frequency.
"""

from dataclasses import dataclass, field
from enum import Enum


class NotifChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotifFrequency(str, Enum):
    REALTIME = "realtime"
    HOURLY_DIGEST = "hourly"
    DAILY_DIGEST = "daily"
    WEEKLY_DIGEST = "weekly"
    OFF = "off"


@dataclass
class NotifPreference:
    event_type: str
    label: str
    channel: NotifChannel = NotifChannel.IN_APP
    frequency: NotifFrequency = NotifFrequency.REALTIME
    enabled: bool = True


# Default preferences (users can customize)
DEFAULT_PREFERENCES: list[NotifPreference] = [
    # Sales notifications
    NotifPreference("lead.hot", "Lead caliente detectado", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("lead.qualified", "Lead calificado", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("lead.stale", "Lead estancado", NotifChannel.EMAIL, NotifFrequency.DAILY_DIGEST),
    NotifPreference("outreach.replied", "Respuesta a outreach", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("deal.won", "Deal ganado", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("deal.lost", "Deal perdido", NotifChannel.IN_APP, NotifFrequency.REALTIME),

    # Support notifications
    NotifPreference("ticket.urgent", "Ticket urgente", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("ticket.sla_warning", "SLA por vencer", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("ticket.sla_breach", "SLA vencido", NotifChannel.EMAIL, NotifFrequency.REALTIME),
    NotifPreference("ticket.escalated", "Ticket escalado", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("ticket.resolved", "Ticket resuelto", NotifChannel.IN_APP, NotifFrequency.HOURLY_DIGEST),

    # System notifications
    NotifPreference("system.error", "Error del sistema", NotifChannel.EMAIL, NotifFrequency.REALTIME),
    NotifPreference("system.import_complete", "Importación completada", NotifChannel.IN_APP, NotifFrequency.REALTIME),
    NotifPreference("billing.payment_due", "Pago pendiente", NotifChannel.EMAIL, NotifFrequency.REALTIME),
    NotifPreference("billing.usage_warning", "Límite de uso cercano", NotifChannel.EMAIL, NotifFrequency.DAILY_DIGEST),
]


class NotifPreferencesManager:
    """Manages per-user notification preferences."""

    def __init__(self):
        self._user_prefs: dict[str, list[NotifPreference]] = {}

    def get_preferences(self, user_id: str) -> list[NotifPreference]:
        if user_id not in self._user_prefs:
            # Copy defaults
            self._user_prefs[user_id] = [
                NotifPreference(
                    event_type=p.event_type, label=p.label,
                    channel=p.channel, frequency=p.frequency, enabled=p.enabled,
                )
                for p in DEFAULT_PREFERENCES
            ]
        return self._user_prefs[user_id]

    def update_preference(
        self, user_id: str, event_type: str,
        channel: str | None = None, frequency: str | None = None, enabled: bool | None = None
    ) -> NotifPreference | None:
        prefs = self.get_preferences(user_id)
        for pref in prefs:
            if pref.event_type == event_type:
                if channel:
                    pref.channel = NotifChannel(channel)
                if frequency:
                    pref.frequency = NotifFrequency(frequency)
                if enabled is not None:
                    pref.enabled = enabled
                return pref
        return None

    def should_notify(self, user_id: str, event_type: str) -> tuple[bool, NotifChannel, NotifFrequency]:
        prefs = self.get_preferences(user_id)
        for pref in prefs:
            if pref.event_type == event_type:
                return pref.enabled, pref.channel, pref.frequency
        return False, NotifChannel.IN_APP, NotifFrequency.OFF

    def mute_all(self, user_id: str) -> None:
        prefs = self.get_preferences(user_id)
        for p in prefs:
            p.enabled = False

    def reset_to_defaults(self, user_id: str) -> list[NotifPreference]:
        if user_id in self._user_prefs:
            del self._user_prefs[user_id]
        return self.get_preferences(user_id)


# Singleton
notif_prefs = NotifPreferencesManager()
