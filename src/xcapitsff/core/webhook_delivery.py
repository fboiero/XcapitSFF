"""Outbound webhook delivery system — reliable event delivery to external endpoints.

Supports:
- HMAC-SHA256 payload signing for authenticity verification
- Exponential backoff retries (1min, 5min, 30min, 2hr, 12hr)
- Auto-disable after 50 consecutive failures (circuit breaker)
- Per-tenant endpoint management with event filtering
- Delivery tracking with full audit trail

All storage is in-memory (dict-based) for now, structured for easy
migration to a persistent backend.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Retry backoff schedule in seconds: 1min, 5min, 30min, 2hr, 12hr
RETRY_BACKOFF_SECONDS = [60, 300, 1800, 7200, 43200]

# Circuit-breaker threshold: auto-disable endpoint after N consecutive failures
MAX_CONSECUTIVE_FAILURES = 50


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class WebhookEndpoint:
    """An outbound webhook subscription for a tenant."""

    id: str
    tenant_id: str
    url: str
    secret: str
    events: list[str]
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    failure_count: int = 0
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None


@dataclass
class WebhookDelivery:
    """A single delivery attempt record for an outbound webhook."""

    id: str
    endpoint_id: str
    event_type: str
    payload: dict[str, Any]
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempt_count: int = 0
    max_attempts: int = 5
    next_retry_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)
    delivered_at: datetime | None = None
    response_status: int | None = None
    response_body: str | None = None


class WebhookManager:
    """Manages outbound webhook endpoint registration and event delivery.

    All state is held in-memory via plain dicts.  The public API is
    designed so that swapping in a database-backed store requires only
    replacing the storage layer.
    """

    def __init__(self) -> None:
        self._endpoints: dict[str, WebhookEndpoint] = {}
        self._deliveries: dict[str, WebhookDelivery] = {}

    # ------------------------------------------------------------------
    # Endpoint management
    # ------------------------------------------------------------------

    def register_endpoint(
        self,
        tenant_id: str,
        url: str,
        secret: str,
        events: list[str],
    ) -> WebhookEndpoint:
        """Register a new outbound webhook endpoint for *tenant_id*."""
        endpoint = WebhookEndpoint(
            id=str(uuid.uuid4())[:8],
            tenant_id=tenant_id,
            url=url,
            secret=secret,
            events=events,
        )
        self._endpoints[endpoint.id] = endpoint
        logger.info(
            "Registered webhook endpoint %s for tenant %s -> %s (events=%s)",
            endpoint.id,
            tenant_id,
            url,
            events,
        )
        return endpoint

    def list_endpoints(self, tenant_id: str) -> list[WebhookEndpoint]:
        """Return all endpoints belonging to *tenant_id*."""
        return [
            ep for ep in self._endpoints.values()
            if ep.tenant_id == tenant_id
        ]

    def update_endpoint(
        self,
        endpoint_id: str,
        *,
        url: str | None = None,
        secret: str | None = None,
        events: list[str] | None = None,
        active: bool | None = None,
    ) -> WebhookEndpoint:
        """Update fields on an existing endpoint.

        Raises ``KeyError`` if the endpoint does not exist.
        """
        ep = self._endpoints.get(endpoint_id)
        if ep is None:
            raise KeyError(f"Endpoint '{endpoint_id}' not found")

        if url is not None:
            ep.url = url
        if secret is not None:
            ep.secret = secret
        if events is not None:
            ep.events = events
        if active is not None:
            ep.active = active
            # Reset failure count when re-activating
            if active:
                ep.failure_count = 0

        logger.info("Updated webhook endpoint %s", endpoint_id)
        return ep

    def delete_endpoint(self, endpoint_id: str) -> None:
        """Remove an endpoint and all its delivery records.

        Raises ``KeyError`` if the endpoint does not exist.
        """
        if endpoint_id not in self._endpoints:
            raise KeyError(f"Endpoint '{endpoint_id}' not found")

        del self._endpoints[endpoint_id]

        # Clean up associated deliveries
        to_remove = [
            d_id for d_id, d in self._deliveries.items()
            if d.endpoint_id == endpoint_id
        ]
        for d_id in to_remove:
            del self._deliveries[d_id]

        logger.info("Deleted webhook endpoint %s (and %d deliveries)", endpoint_id, len(to_remove))

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    def deliver(
        self,
        event_type: str,
        tenant_id: str,
        payload: dict[str, Any],
    ) -> list[WebhookDelivery]:
        """Queue delivery of *event_type* to all matching active endpoints.

        Returns the list of created :class:`WebhookDelivery` records.
        """
        deliveries: list[WebhookDelivery] = []
        for ep in self._endpoints.values():
            if ep.tenant_id != tenant_id:
                continue
            if not ep.active:
                continue
            if event_type not in ep.events:
                continue

            delivery = WebhookDelivery(
                id=str(uuid.uuid4())[:8],
                endpoint_id=ep.id,
                event_type=event_type,
                payload=payload,
            )
            self._deliveries[delivery.id] = delivery
            deliveries.append(delivery)
            logger.info(
                "Queued delivery %s for endpoint %s (event=%s)",
                delivery.id,
                ep.id,
                event_type,
            )

        return deliveries

    # ------------------------------------------------------------------
    # Signing
    # ------------------------------------------------------------------

    @staticmethod
    def _sign_payload(secret: str, payload: dict[str, Any]) -> str:
        """Compute HMAC-SHA256 signature of *payload* using *secret*.

        The payload is serialised to JSON with sorted keys and no extra
        whitespace before signing (canonical form).
        """
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        sig = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={sig}"

    # ------------------------------------------------------------------
    # Attempt delivery (mock mode)
    # ------------------------------------------------------------------

    def _attempt_delivery(self, delivery: WebhookDelivery) -> None:
        """Simulate an HTTP POST to the endpoint.

        In production this would use ``httpx.AsyncClient`` to POST the
        signed payload.  For now we simulate success/failure based on
        the endpoint URL convention:

        - URLs containing ``/fail`` always fail (for testing).
        - Everything else succeeds.
        """
        ep = self._endpoints.get(delivery.endpoint_id)
        if ep is None:
            delivery.status = DeliveryStatus.DEAD
            return

        delivery.attempt_count += 1
        signature = self._sign_payload(ep.secret, delivery.payload)

        # --- Mock transport ---
        simulate_failure = "/fail" in ep.url

        if simulate_failure:
            delivery.status = DeliveryStatus.FAILED
            delivery.response_status = 500
            delivery.response_body = "Internal Server Error"
            ep.failure_count += 1
            ep.last_failure_at = datetime.now()

            # Schedule retry or mark dead
            if delivery.attempt_count >= delivery.max_attempts:
                delivery.status = DeliveryStatus.DEAD
                logger.warning(
                    "Delivery %s dead after %d attempts",
                    delivery.id,
                    delivery.attempt_count,
                )
            else:
                backoff_idx = min(delivery.attempt_count - 1, len(RETRY_BACKOFF_SECONDS) - 1)
                delivery.next_retry_at = datetime.now() + timedelta(
                    seconds=RETRY_BACKOFF_SECONDS[backoff_idx],
                )
                delivery.status = DeliveryStatus.PENDING
                logger.info(
                    "Delivery %s failed, retry #%d at %s",
                    delivery.id,
                    delivery.attempt_count,
                    delivery.next_retry_at.isoformat(),
                )

            # Circuit breaker: auto-disable after threshold
            if ep.failure_count >= MAX_CONSECUTIVE_FAILURES:
                ep.active = False
                logger.warning(
                    "Endpoint %s auto-disabled after %d consecutive failures",
                    ep.id,
                    ep.failure_count,
                )
        else:
            delivery.status = DeliveryStatus.DELIVERED
            delivery.response_status = 200
            delivery.response_body = "OK"
            delivery.delivered_at = datetime.now()
            ep.failure_count = 0
            ep.last_success_at = datetime.now()
            logger.info("Delivery %s succeeded", delivery.id)

    # ------------------------------------------------------------------
    # Retry processing
    # ------------------------------------------------------------------

    def retry_failed(self) -> list[str]:
        """Process all pending deliveries whose retry time has arrived.

        Returns the list of delivery IDs that were retried.
        """
        now = datetime.now()
        retried: list[str] = []

        for delivery in list(self._deliveries.values()):
            if delivery.status != DeliveryStatus.PENDING:
                continue
            if delivery.attempt_count == 0:
                # First attempt — not a retry
                continue
            if delivery.next_retry_at is not None and delivery.next_retry_at > now:
                continue

            self._attempt_delivery(delivery)
            retried.append(delivery.id)

        return retried

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_deliveries(
        self,
        endpoint_id: str,
        status: DeliveryStatus | None = None,
    ) -> list[WebhookDelivery]:
        """Return deliveries for *endpoint_id* with optional status filter."""
        result = [
            d for d in self._deliveries.values()
            if d.endpoint_id == endpoint_id
        ]
        if status is not None:
            result = [d for d in result if d.status == status]
        return result

    def get_delivery_stats(self, tenant_id: str) -> dict[str, Any]:
        """Compute aggregate delivery statistics for a tenant."""
        tenant_endpoints = {
            ep.id for ep in self._endpoints.values()
            if ep.tenant_id == tenant_id
        }
        tenant_deliveries = [
            d for d in self._deliveries.values()
            if d.endpoint_id in tenant_endpoints
        ]

        total = len(tenant_deliveries)
        delivered = sum(1 for d in tenant_deliveries if d.status == DeliveryStatus.DELIVERED)
        failed = sum(1 for d in tenant_deliveries if d.status == DeliveryStatus.FAILED)
        dead = sum(1 for d in tenant_deliveries if d.status == DeliveryStatus.DEAD)
        pending = sum(1 for d in tenant_deliveries if d.status == DeliveryStatus.PENDING)

        success_rate = (delivered / total * 100) if total > 0 else 0.0

        return {
            "total_deliveries": total,
            "total_delivered": delivered,
            "total_failed": failed,
            "total_dead": dead,
            "total_pending": pending,
            "success_rate": round(success_rate, 2),
        }


# Singleton
webhook_manager = WebhookManager()
