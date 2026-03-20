"""Integrations hub — manage connections to external services.

Provides a centralized registry for connecting, configuring, testing,
and syncing external service integrations (Slack, Salesforce, Stripe,
etc.).  Each integration belongs to a tenant and maintains its own
configuration, connection status, and sync history.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class IntegrationType(str, Enum):
    SLACK = "slack"
    EMAIL_SMTP = "email_smtp"
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    GOOGLE_CALENDAR = "google_calendar"
    ZAPIER = "zapier"
    STRIPE = "stripe"
    TWILIO = "twilio"
    WHATSAPP = "whatsapp"
    CUSTOM_WEBHOOK = "custom_webhook"


class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    PENDING = "pending"


class SyncDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class SyncStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Integration:
    """A single external-service integration for a tenant."""

    id: str
    tenant_id: str
    type: IntegrationType
    name: str
    status: IntegrationStatus
    config: dict[str, Any]
    created_at: datetime
    last_sync_at: datetime | None = None
    sync_count: int = 0
    error_message: str | None = None
    enabled: bool = True


@dataclass
class SyncLog:
    """Record of a single synchronisation run."""

    id: str
    integration_id: str
    direction: SyncDirection
    entity_type: str | None
    records_synced: int
    errors: list[str]
    started_at: datetime
    completed_at: datetime | None = None
    status: SyncStatus = SyncStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# Integration catalog — metadata for each integration type
# ---------------------------------------------------------------------------

INTEGRATION_CATALOG: dict[IntegrationType, dict[str, Any]] = {
    IntegrationType.SLACK: {
        "description": "Send notifications and alerts to Slack channels",
        "icon": "slack",
        "required_config_fields": ["webhook_url"],
        "optional_config_fields": ["channel", "bot_token"],
        "supports_inbound": False,
        "supports_outbound": True,
    },
    IntegrationType.EMAIL_SMTP: {
        "description": "Send transactional emails via SMTP",
        "icon": "email",
        "required_config_fields": ["host", "port", "username", "password"],
        "optional_config_fields": ["from_name", "use_tls"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.SALESFORCE: {
        "description": "Sync leads, contacts, and opportunities with Salesforce CRM",
        "icon": "salesforce",
        "required_config_fields": ["client_id", "client_secret", "instance_url"],
        "optional_config_fields": ["sandbox", "api_version"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.HUBSPOT: {
        "description": "Sync contacts and deals with HubSpot CRM",
        "icon": "hubspot",
        "required_config_fields": ["api_key"],
        "optional_config_fields": ["portal_id"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.GOOGLE_CALENDAR: {
        "description": "Sync meetings and events with Google Calendar",
        "icon": "google_calendar",
        "required_config_fields": ["client_id", "client_secret", "refresh_token"],
        "optional_config_fields": ["calendar_id"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.ZAPIER: {
        "description": "Connect to 5000+ apps via Zapier webhooks",
        "icon": "zapier",
        "required_config_fields": ["webhook_url"],
        "optional_config_fields": ["zap_id"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.STRIPE: {
        "description": "Manage payments and subscriptions with Stripe",
        "icon": "stripe",
        "required_config_fields": ["api_key"],
        "optional_config_fields": ["webhook_secret", "account_id"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.TWILIO: {
        "description": "Send SMS and voice notifications via Twilio",
        "icon": "twilio",
        "required_config_fields": ["account_sid", "auth_token", "from_number"],
        "optional_config_fields": ["messaging_service_sid"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.WHATSAPP: {
        "description": "Send messages and notifications via WhatsApp Business API",
        "icon": "whatsapp",
        "required_config_fields": ["api_key", "phone_number_id"],
        "optional_config_fields": ["business_account_id"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
    IntegrationType.CUSTOM_WEBHOOK: {
        "description": "Connect to any service via custom webhook URL",
        "icon": "webhook",
        "required_config_fields": ["url"],
        "optional_config_fields": ["method", "headers", "secret"],
        "supports_inbound": True,
        "supports_outbound": True,
    },
}


# ---------------------------------------------------------------------------
# IntegrationsHub
# ---------------------------------------------------------------------------


class IntegrationsHub:
    """Central manager for external-service integrations.

    All data is stored in-memory (dict-based).  Each integration is
    scoped to a ``tenant_id`` so that different tenants are isolated.
    """

    def __init__(self) -> None:
        self._integrations: dict[str, Integration] = {}
        self._sync_logs: dict[str, list[SyncLog]] = {}  # integration_id → logs

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def connect(
        self,
        tenant_id: str,
        type: IntegrationType,
        name: str,
        config: dict[str, Any],
    ) -> Integration:
        """Register and connect a new integration for *tenant_id*.

        Validates that all required config fields for the integration
        type are present before creating the integration.
        """
        catalog = INTEGRATION_CATALOG.get(type)
        if catalog is None:
            raise ValueError(f"Unknown integration type: {type}")

        required = set(catalog["required_config_fields"])
        provided = set(config.keys())
        missing = required - provided
        if missing:
            raise ValueError(
                f"Missing required config fields for {type.value}: {', '.join(sorted(missing))}"
            )

        integration = Integration(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type=type,
            name=name,
            status=IntegrationStatus.CONNECTED,
            config=config,
            created_at=datetime.now(),
        )
        self._integrations[integration.id] = integration
        self._sync_logs[integration.id] = []
        logger.info(
            "Integration connected: %s (%s) for tenant %s",
            name,
            type.value,
            tenant_id,
        )
        return integration

    def disconnect(self, integration_id: str) -> bool:
        """Disconnect (remove) an integration. Returns ``True`` on success."""
        integration = self._integrations.pop(integration_id, None)
        if integration is None:
            return False
        self._sync_logs.pop(integration_id, None)
        logger.info("Integration disconnected: %s", integration_id)
        return True

    def update_config(
        self, integration_id: str, config: dict[str, Any]
    ) -> Integration:
        """Merge *config* into the existing integration config."""
        integration = self._get_or_raise(integration_id)
        integration.config.update(config)
        logger.info("Integration config updated: %s", integration_id)
        return integration

    def get_integration(self, integration_id: str) -> Integration:
        """Return a single integration by id."""
        return self._get_or_raise(integration_id)

    def list_integrations(self, tenant_id: str) -> list[Integration]:
        """Return all integrations for a given tenant."""
        return [
            i for i in self._integrations.values() if i.tenant_id == tenant_id
        ]

    # ------------------------------------------------------------------
    # Connection testing
    # ------------------------------------------------------------------

    def test_connection(self, integration_id: str) -> dict[str, Any]:
        """Test the connection for an integration.

        In a real system this would attempt to reach the external service.
        Here we simulate the test: connections succeed unless the config
        contains ``{"simulate_failure": true}``.
        """
        integration = self._get_or_raise(integration_id)

        start = time.monotonic()

        if integration.config.get("simulate_failure"):
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            integration.status = IntegrationStatus.ERROR
            integration.error_message = "Connection refused (simulated)"
            return {
                "success": False,
                "message": "Connection refused (simulated)",
                "latency_ms": elapsed_ms,
            }

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        integration.status = IntegrationStatus.CONNECTED
        integration.error_message = None
        return {
            "success": True,
            "message": "Connection successful",
            "latency_ms": elapsed_ms,
        }

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------

    def sync(
        self,
        integration_id: str,
        direction: str = "outbound",
        entity_type: str | None = None,
    ) -> SyncLog:
        """Trigger a synchronisation for an integration.

        The actual data transfer is simulated; in production this would
        call the external service's API.
        """
        integration = self._get_or_raise(integration_id)

        if not integration.enabled:
            raise ValueError(
                f"Integration {integration_id} is disabled; enable it before syncing"
            )

        sync_dir = SyncDirection(direction)
        started = datetime.now()

        # Simulate sync
        records = random.randint(1, 50)
        errors: list[str] = []

        if integration.config.get("simulate_sync_error"):
            errors.append("Simulated sync error on record #3")

        log = SyncLog(
            id=str(uuid.uuid4()),
            integration_id=integration_id,
            direction=sync_dir,
            entity_type=entity_type,
            records_synced=records,
            errors=errors,
            started_at=started,
            completed_at=datetime.now(),
            status=SyncStatus.FAILED if errors else SyncStatus.SUCCESS,
        )

        self._sync_logs.setdefault(integration_id, []).append(log)
        integration.sync_count += 1
        integration.last_sync_at = log.completed_at

        logger.info(
            "Sync completed for %s: %d records (%s, %s)",
            integration_id,
            records,
            direction,
            log.status.value,
        )
        return log

    def get_sync_logs(
        self, integration_id: str, limit: int = 20
    ) -> list[SyncLog]:
        """Return the most recent sync logs for an integration."""
        self._get_or_raise(integration_id)
        logs = self._sync_logs.get(integration_id, [])
        return logs[-limit:]

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    @staticmethod
    def get_available_integrations() -> list[dict[str, Any]]:
        """Return the catalog of all available integration types."""
        result: list[dict[str, Any]] = []
        for itype, meta in INTEGRATION_CATALOG.items():
            result.append({
                "type": itype.value,
                **meta,
            })
        return result

    # ------------------------------------------------------------------
    # Enable / Disable
    # ------------------------------------------------------------------

    def enable(self, integration_id: str) -> Integration:
        """Enable an integration."""
        integration = self._get_or_raise(integration_id)
        integration.enabled = True
        logger.info("Integration enabled: %s", integration_id)
        return integration

    def disable(self, integration_id: str) -> Integration:
        """Disable an integration (pauses syncing)."""
        integration = self._get_or_raise(integration_id)
        integration.enabled = False
        logger.info("Integration disabled: %s", integration_id)
        return integration

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def get_integration_health(self, tenant_id: str) -> dict[str, Any]:
        """Return an aggregate health summary for a tenant's integrations."""
        integrations = self.list_integrations(tenant_id)
        total = len(integrations)
        connected = sum(
            1 for i in integrations if i.status == IntegrationStatus.CONNECTED
        )
        errors = sum(
            1 for i in integrations if i.status == IntegrationStatus.ERROR
        )

        last_sync: datetime | None = None
        for i in integrations:
            if i.last_sync_at is not None:
                if last_sync is None or i.last_sync_at > last_sync:
                    last_sync = i.last_sync_at

        return {
            "total": total,
            "connected": connected,
            "errors": errors,
            "last_sync": last_sync.isoformat() if last_sync else None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_raise(self, integration_id: str) -> Integration:
        """Lookup an integration by id or raise ``KeyError``."""
        integration = self._integrations.get(integration_id)
        if integration is None:
            raise KeyError(f"Integration not found: {integration_id}")
        return integration


# ======================================================================
# Singleton
# ======================================================================

integrations_hub = IntegrationsHub()
