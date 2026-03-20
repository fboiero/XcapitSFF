"""API endpoints for outbound webhook delivery management.

Exposes CRUD for webhook endpoints, delivery history queries,
test-event dispatch, and aggregate delivery statistics.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.webhook_delivery import DeliveryStatus, webhook_manager

router = APIRouter(prefix="/webhook-delivery", tags=["Webhook Delivery"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RegisterEndpointRequest(BaseModel):
    tenant_id: str
    url: str
    secret: str
    events: list[str]


class UpdateEndpointRequest(BaseModel):
    url: str | None = None
    secret: str | None = None
    events: list[str] | None = None
    active: bool | None = None


class TestEventRequest(BaseModel):
    tenant_id: str
    event_type: str
    payload: dict | None = None


# ---------------------------------------------------------------------------
# Endpoint helpers
# ---------------------------------------------------------------------------


def _endpoint_to_dict(ep) -> dict:
    return {
        "id": ep.id,
        "tenant_id": ep.tenant_id,
        "url": ep.url,
        "events": ep.events,
        "active": ep.active,
        "created_at": ep.created_at.isoformat(),
        "failure_count": ep.failure_count,
        "last_success_at": ep.last_success_at.isoformat() if ep.last_success_at else None,
        "last_failure_at": ep.last_failure_at.isoformat() if ep.last_failure_at else None,
    }


def _delivery_to_dict(d) -> dict:
    return {
        "id": d.id,
        "endpoint_id": d.endpoint_id,
        "event_type": d.event_type,
        "payload": d.payload,
        "status": d.status.value,
        "attempt_count": d.attempt_count,
        "max_attempts": d.max_attempts,
        "next_retry_at": d.next_retry_at.isoformat() if d.next_retry_at else None,
        "created_at": d.created_at.isoformat(),
        "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
        "response_status": d.response_status,
        "response_body": d.response_body,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/endpoints")
async def register_endpoint(body: RegisterEndpointRequest):
    """Register a new outbound webhook endpoint."""
    ep = webhook_manager.register_endpoint(
        tenant_id=body.tenant_id,
        url=body.url,
        secret=body.secret,
        events=body.events,
    )
    return _endpoint_to_dict(ep)


@router.get("/endpoints")
async def list_endpoints(tenant_id: str):
    """List all webhook endpoints for a tenant."""
    endpoints = webhook_manager.list_endpoints(tenant_id)
    return {
        "count": len(endpoints),
        "endpoints": [_endpoint_to_dict(ep) for ep in endpoints],
    }


@router.put("/endpoints/{endpoint_id}")
async def update_endpoint(endpoint_id: str, body: UpdateEndpointRequest):
    """Update an existing webhook endpoint."""
    try:
        ep = webhook_manager.update_endpoint(
            endpoint_id,
            url=body.url,
            secret=body.secret,
            events=body.events,
            active=body.active,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_id}' not found")
    return _endpoint_to_dict(ep)


@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(endpoint_id: str):
    """Delete a webhook endpoint and its delivery history."""
    try:
        webhook_manager.delete_endpoint(endpoint_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_id}' not found")
    return {"status": "deleted", "endpoint_id": endpoint_id}


@router.get("/endpoints/{endpoint_id}/deliveries")
async def list_deliveries(endpoint_id: str, status: str | None = None):
    """List delivery records for a specific endpoint."""
    if endpoint_id not in webhook_manager._endpoints:
        raise HTTPException(status_code=404, detail=f"Endpoint '{endpoint_id}' not found")

    status_filter = None
    if status is not None:
        try:
            status_filter = DeliveryStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    deliveries = webhook_manager.get_deliveries(endpoint_id, status=status_filter)
    return {
        "count": len(deliveries),
        "deliveries": [_delivery_to_dict(d) for d in deliveries],
    }


@router.post("/endpoints/test")
async def send_test_event(body: TestEventRequest):
    """Send a test event to all matching endpoints for a tenant."""
    payload = body.payload or {"test": True, "message": "Webhook test event"}
    deliveries = webhook_manager.deliver(
        event_type=body.event_type,
        tenant_id=body.tenant_id,
        payload=payload,
    )

    # Immediately attempt delivery for test events
    for d in deliveries:
        webhook_manager._attempt_delivery(d)

    return {
        "deliveries_created": len(deliveries),
        "results": [_delivery_to_dict(d) for d in deliveries],
    }


@router.get("/stats")
async def delivery_stats(tenant_id: str):
    """Get aggregate delivery statistics for a tenant."""
    return webhook_manager.get_delivery_stats(tenant_id)
