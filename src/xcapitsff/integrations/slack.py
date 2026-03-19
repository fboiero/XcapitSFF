"""Slack webhook integration — send notifications and alerts to Slack channels.

Provides a simple webhook-based integration with Slack. When no ``webhook_url``
is configured (empty string or ``None``), the module operates in **mock mode**,
logging messages instead of sending HTTP requests.

Typical usage::

    slack = SlackWebhook("https://hooks.slack.com/services/T.../B.../xxx")
    slack.send_notification("New lead", "A hot lead was qualified", color="good")
    slack.send_alert("sla_breach", "Ticket #42 breached SLA", severity="high")
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Severity colour mapping
# ---------------------------------------------------------------------------

_SEVERITY_COLORS: dict[str, str] = {
    "info": "#36a64f",      # green
    "low": "#36a64f",       # green
    "warning": "#ff9900",   # orange
    "medium": "#ff9900",    # orange
    "high": "#e01e5a",      # red
    "critical": "#e01e5a",  # red
}


# ---------------------------------------------------------------------------
# SlackWebhook
# ---------------------------------------------------------------------------


class SlackWebhook:
    """Slack webhook integration with automatic mock-mode fallback.

    When ``webhook_url`` is falsy (empty string or ``None``), all methods
    operate in mock mode: messages are logged but no HTTP requests are made.

    Args:
        webhook_url: Slack Incoming Webhook URL. Pass an empty string or
            ``None`` to enable mock mode.
    """

    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url: str = webhook_url or ""
        self.mock_mode: bool = not bool(self.webhook_url)
        self._sent_log: list[dict[str, Any]] = []

        if self.mock_mode:
            logger.info("SlackWebhook initialised in MOCK mode (no webhook URL configured)")

    # -- Internal helpers ---------------------------------------------------

    def _post_payload(self, payload: dict[str, Any]) -> bool:
        """POST a JSON payload to the Slack webhook URL.

        Returns ``True`` on success, ``False`` on failure.
        """
        if self.mock_mode:
            logger.info("[SLACK-MOCK] %s", json.dumps(payload, ensure_ascii=False)[:500])
            self._sent_log.append(payload)
            return True

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                success = resp.status == 200
                if success:
                    self._sent_log.append(payload)
                return success
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            logger.error("Slack webhook POST failed: %s", exc)
            return False

    # -- Public API ---------------------------------------------------------

    def send_notification(
        self,
        title: str,
        body: str,
        color: str = "#36a64f",
        fields: list[dict[str, str]] | None = None,
    ) -> bool:
        """Send a rich notification to Slack.

        Args:
            title: Attachment title (bold header).
            body: Attachment text / description.
            color: Sidebar colour hex code (default green).
            fields: Optional list of ``{"title": ..., "value": ..., "short": ...}``
                Slack attachment fields.

        Returns:
            ``True`` if the message was accepted, ``False`` otherwise.
        """
        attachment: dict[str, Any] = {
            "fallback": f"{title}: {body}",
            "color": color,
            "title": title,
            "text": body,
            "ts": int(datetime.now().timestamp()),
        }
        if fields:
            attachment["fields"] = fields

        payload = {"attachments": [attachment]}
        return self._post_payload(payload)

    def send_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "info",
    ) -> bool:
        """Send a severity-tagged alert to Slack.

        Args:
            alert_type: Machine-readable alert type (e.g. ``"sla_breach"``).
            message: Human-readable description.
            severity: One of ``"info"``, ``"low"``, ``"warning"``, ``"medium"``,
                ``"high"``, ``"critical"``.

        Returns:
            ``True`` if the message was accepted, ``False`` otherwise.
        """
        color = _SEVERITY_COLORS.get(severity.lower(), "#cccccc")
        emoji = {
            "info": "information_source",
            "low": "large_blue_circle",
            "warning": "warning",
            "medium": "large_orange_circle",
            "high": "red_circle",
            "critical": "rotating_light",
        }.get(severity.lower(), "bell")

        title = f":{emoji}: [{severity.upper()}] {alert_type}"
        return self.send_notification(
            title=title,
            body=message,
            color=color,
            fields=[
                {"title": "Type", "value": alert_type, "short": True},
                {"title": "Severity", "value": severity.upper(), "short": True},
            ],
        )

    # -- Introspection ------------------------------------------------------

    def get_sent_log(self) -> list[dict[str, Any]]:
        """Return a copy of all payloads that were sent (or mock-logged)."""
        return list(self._sent_log)
