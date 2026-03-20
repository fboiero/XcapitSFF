"""API endpoints for the integrations hub.

Exposes CRUD operations, connection testing, sync triggers, and health
monitoring for external-service integrations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.integrations_hub import (
    IntegrationType,
    integrations_hub,
)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ConnectRequest(BaseModel):
    tenant_id: str
    type: IntegrationType
    name: str
    config: dict


class UpdateConfigRequest(BaseModel):
    config: dict


class SyncRequest(BaseModel):
    direction: str = "outbound"
    entity_type: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _integration_to_dict(integration) -> dict:
    """Serialise an Integration dataclass to a JSON-safe dict."""
    return {
        "id": integration.id,
        "tenant_id": integration.tenant_id,
        "type": integration.type.value,
        "name": integration.name,
        "status": integration.status.value,
        "config": integration.config,
        "created_at": integration.created_at.isoformat(),
        "last_sync_at": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
        "sync_count": integration.sync_count,
        "error_message": integration.error_message,
        "enabled": integration.enabled,
    }


def _sync_log_to_dict(log) -> dict:
    """Serialise a SyncLog dataclass to a JSON-safe dict."""
    return {
        "id": log.id,
        "integration_id": log.integration_id,
        "direction": log.direction.value,
        "entity_type": log.entity_type,
        "records_synced": log.records_synced,
        "errors": log.errors,
        "started_at": log.started_at.isoformat(),
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        "status": log.status.value,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/available")
async def get_available_integrations():
    """Return the catalog of all available integration types."""
    return integrations_hub.get_available_integrations()


@router.post("")
async def connect_integration(body: ConnectRequest):
    """Connect a new integration for a tenant."""
    try:
        integration = integrations_hub.connect(
            tenant_id=body.tenant_id,
            type=body.type,
            name=body.name,
            config=body.config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _integration_to_dict(integration)


@router.get("")
async def list_integrations(tenant_id: str):
    """List all integrations for a tenant."""
    integrations = integrations_hub.list_integrations(tenant_id)
    return [_integration_to_dict(i) for i in integrations]


@router.get("/health")
async def get_integration_health(tenant_id: str):
    """Return an aggregate health summary for a tenant's integrations."""
    return integrations_hub.get_integration_health(tenant_id)


@router.get("/{integration_id}")
async def get_integration(integration_id: str):
    """Return a single integration by id."""
    try:
        integration = integrations_hub.get_integration(integration_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _integration_to_dict(integration)


@router.put("/{integration_id}")
async def update_integration_config(integration_id: str, body: UpdateConfigRequest):
    """Update the configuration for an integration."""
    try:
        integration = integrations_hub.update_config(integration_id, body.config)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _integration_to_dict(integration)


@router.delete("/{integration_id}")
async def disconnect_integration(integration_id: str):
    """Disconnect (remove) an integration."""
    success = integrations_hub.disconnect(integration_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Integration not found: {integration_id}")
    return {"success": True, "message": "Integration disconnected"}


@router.post("/{integration_id}/test")
async def test_connection(integration_id: str):
    """Test the connection for an integration."""
    try:
        result = integrations_hub.test_connection(integration_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@router.post("/{integration_id}/sync")
async def trigger_sync(integration_id: str, body: SyncRequest | None = None):
    """Trigger a synchronisation for an integration."""
    direction = body.direction if body else "outbound"
    entity_type = body.entity_type if body else None
    try:
        log = integrations_hub.sync(
            integration_id, direction=direction, entity_type=entity_type
        )
    except (KeyError, ValueError) as exc:
        status = 404 if isinstance(exc, KeyError) else 400
        raise HTTPException(status_code=status, detail=str(exc))
    return _sync_log_to_dict(log)


@router.get("/{integration_id}/logs")
async def get_sync_logs(integration_id: str, limit: int = 20):
    """Return the most recent sync logs for an integration."""
    try:
        logs = integrations_hub.get_sync_logs(integration_id, limit=limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return [_sync_log_to_dict(log) for log in logs]


@router.post("/{integration_id}/enable")
async def enable_integration(integration_id: str):
    """Enable an integration."""
    try:
        integration = integrations_hub.enable(integration_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _integration_to_dict(integration)


@router.post("/{integration_id}/disable")
async def disable_integration(integration_id: str):
    """Disable an integration (pauses syncing)."""
    try:
        integration = integrations_hub.disable(integration_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _integration_to_dict(integration)
