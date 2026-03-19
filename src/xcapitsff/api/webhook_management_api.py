"""Webhook Management API — configure outbound webhooks per tenant.

Tenants can register webhook URLs to receive real-time notifications
about events in their account (lead created, ticket resolved, etc.).
"""

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass
class WebhookEndpoint:
    endpoint_id: str
    url: str
    events: list[str]  # event types to subscribe to
    secret: str  # HMAC secret for signature
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: datetime | None = None
    failure_count: int = 0
    success_count: int = 0


@dataclass
class WebhookDelivery:
    delivery_id: str
    endpoint_id: str
    event_type: str
    payload: dict
    status_code: int | None = None
    success: bool = False
    error: str | None = None
    delivered_at: datetime = field(default_factory=datetime.now)


class WebhookManager:
    """Manages outbound webhook subscriptions and delivery."""

    def __init__(self):
        self._endpoints: dict[str, WebhookEndpoint] = {}
        self._deliveries: list[WebhookDelivery] = []
        self._counter = 0
        self._delivery_counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"wh-{self._counter:06d}"

    def register(self, url: str, events: list[str], secret: str = "") -> WebhookEndpoint:
        if not secret:
            secret = hashlib.sha256(f"{url}{datetime.now().isoformat()}".encode()).hexdigest()[:32]

        endpoint = WebhookEndpoint(
            endpoint_id=self._next_id(),
            url=url,
            events=events,
            secret=secret,
        )
        self._endpoints[endpoint.endpoint_id] = endpoint
        return endpoint

    def unregister(self, endpoint_id: str) -> bool:
        return self._endpoints.pop(endpoint_id, None) is not None

    def list_endpoints(self) -> list[WebhookEndpoint]:
        return list(self._endpoints.values())

    def get_endpoint(self, endpoint_id: str) -> WebhookEndpoint | None:
        return self._endpoints.get(endpoint_id)

    def toggle(self, endpoint_id: str) -> bool:
        ep = self._endpoints.get(endpoint_id)
        if not ep:
            return False
        ep.is_active = not ep.is_active
        return True

    async def deliver(self, event_type: str, payload: dict) -> list[WebhookDelivery]:
        """Deliver an event to all matching endpoints."""
        results = []
        for ep in self._endpoints.values():
            if not ep.is_active:
                continue
            if event_type not in ep.events and "*" not in ep.events:
                continue

            self._delivery_counter += 1
            delivery_id = f"dlv-{self._delivery_counter:08d}"

            # Sign payload
            body = json.dumps(payload, default=str)
            signature = hmac.new(ep.secret.encode(), body.encode(), hashlib.sha256).hexdigest()

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        ep.url,
                        content=body,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Signature": f"sha256={signature}",
                            "X-Webhook-Event": event_type,
                            "X-Webhook-Delivery": delivery_id,
                        },
                    )
                    delivery = WebhookDelivery(
                        delivery_id=delivery_id,
                        endpoint_id=ep.endpoint_id,
                        event_type=event_type,
                        payload=payload,
                        status_code=resp.status_code,
                        success=200 <= resp.status_code < 300,
                    )
                    if delivery.success:
                        ep.success_count += 1
                    else:
                        ep.failure_count += 1

            except Exception as e:
                delivery = WebhookDelivery(
                    delivery_id=delivery_id,
                    endpoint_id=ep.endpoint_id,
                    event_type=event_type,
                    payload=payload,
                    success=False,
                    error=str(e),
                )
                ep.failure_count += 1

            ep.last_triggered = datetime.now()
            self._deliveries.append(delivery)
            results.append(delivery)

        return results

    def get_deliveries(self, endpoint_id: str | None = None, limit: int = 50) -> list[WebhookDelivery]:
        deliveries = self._deliveries
        if endpoint_id:
            deliveries = [d for d in deliveries if d.endpoint_id == endpoint_id]
        return deliveries[-limit:]

    def get_stats(self) -> dict:
        total_success = sum(ep.success_count for ep in self._endpoints.values())
        total_failure = sum(ep.failure_count for ep in self._endpoints.values())
        return {
            "total_endpoints": len(self._endpoints),
            "active_endpoints": sum(1 for ep in self._endpoints.values() if ep.is_active),
            "total_deliveries": len(self._deliveries),
            "total_success": total_success,
            "total_failure": total_failure,
            "success_rate": round(total_success / max(total_success + total_failure, 1) * 100, 1),
        }


# Singleton
webhook_manager = WebhookManager()
