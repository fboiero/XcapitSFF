"""Tests for the integrations hub."""

import pytest

from xcapitsff.core.integrations_hub import (
    INTEGRATION_CATALOG,
    Integration,
    IntegrationStatus,
    IntegrationType,
    IntegrationsHub,
    SyncDirection,
    SyncLog,
    SyncStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hub():
    """Return a fresh IntegrationsHub with no pre-existing integrations."""
    return IntegrationsHub()


def _slack_config() -> dict:
    return {"webhook_url": "https://hooks.slack.com/services/T/B/X"}


def _smtp_config() -> dict:
    return {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user",
        "password": "pass",
    }


# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------


def test_connect_integration(hub):
    """Connecting an integration creates it with CONNECTED status."""
    integration = hub.connect("tenant-1", IntegrationType.SLACK, "My Slack", _slack_config())

    assert isinstance(integration, Integration)
    assert integration.tenant_id == "tenant-1"
    assert integration.type == IntegrationType.SLACK
    assert integration.name == "My Slack"
    assert integration.status == IntegrationStatus.CONNECTED
    assert integration.enabled is True
    assert integration.sync_count == 0
    assert integration.id in hub._integrations


def test_connect_missing_required_fields(hub):
    """Connecting with missing required fields raises ValueError."""
    with pytest.raises(ValueError, match="Missing required config fields"):
        hub.connect("tenant-1", IntegrationType.SLACK, "Bad Slack", {})


def test_connect_multiple_integrations(hub):
    """Multiple integrations can coexist for the same tenant."""
    hub.connect("tenant-1", IntegrationType.SLACK, "Slack 1", _slack_config())
    hub.connect("tenant-1", IntegrationType.EMAIL_SMTP, "SMTP", _smtp_config())

    assert len(hub.list_integrations("tenant-1")) == 2


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------


def test_disconnect(hub):
    """Disconnecting an integration removes it."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    assert hub.disconnect(integration.id) is True
    assert integration.id not in hub._integrations


def test_disconnect_nonexistent(hub):
    """Disconnecting a nonexistent integration returns False."""
    assert hub.disconnect("no-such-id") is False


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------


def test_test_connection_success(hub):
    """test_connection returns success when config has no simulate_failure."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    result = hub.test_connection(integration.id)

    assert result["success"] is True
    assert "latency_ms" in result
    assert integration.status == IntegrationStatus.CONNECTED


def test_test_connection_failure(hub):
    """test_connection returns failure when simulate_failure is set."""
    config = {**_slack_config(), "simulate_failure": True}
    integration = hub.connect("t1", IntegrationType.SLACK, "S", config)
    result = hub.test_connection(integration.id)

    assert result["success"] is False
    assert integration.status == IntegrationStatus.ERROR
    assert integration.error_message is not None


def test_test_connection_not_found(hub):
    """test_connection raises KeyError for missing integration."""
    with pytest.raises(KeyError):
        hub.test_connection("ghost")


# ---------------------------------------------------------------------------
# List integrations
# ---------------------------------------------------------------------------


def test_list_integrations(hub):
    """list_integrations returns only integrations for the given tenant."""
    hub.connect("t1", IntegrationType.SLACK, "S1", _slack_config())
    hub.connect("t2", IntegrationType.SLACK, "S2", _slack_config())

    result = hub.list_integrations("t1")
    assert len(result) == 1
    assert result[0].tenant_id == "t1"


def test_list_integrations_empty(hub):
    """list_integrations returns empty list for tenant with no integrations."""
    assert hub.list_integrations("nobody") == []


# ---------------------------------------------------------------------------
# Update config
# ---------------------------------------------------------------------------


def test_update_config(hub):
    """update_config merges new keys into existing config."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    updated = hub.update_config(integration.id, {"channel": "#general"})

    assert updated.config["channel"] == "#general"
    assert updated.config["webhook_url"] == _slack_config()["webhook_url"]


def test_update_config_not_found(hub):
    """update_config raises KeyError for missing integration."""
    with pytest.raises(KeyError):
        hub.update_config("ghost", {"key": "val"})


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def test_sync_creates_log(hub):
    """sync() creates a SyncLog and increments sync_count."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    log = hub.sync(integration.id, direction="outbound", entity_type="leads")

    assert isinstance(log, SyncLog)
    assert log.integration_id == integration.id
    assert log.direction == SyncDirection.OUTBOUND
    assert log.entity_type == "leads"
    assert log.records_synced > 0
    assert integration.sync_count == 1
    assert integration.last_sync_at is not None


def test_sync_disabled_integration_raises(hub):
    """sync() raises ValueError if integration is disabled."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    hub.disable(integration.id)

    with pytest.raises(ValueError, match="disabled"):
        hub.sync(integration.id)


def test_sync_not_found(hub):
    """sync() raises KeyError for missing integration."""
    with pytest.raises(KeyError):
        hub.sync("ghost")


# ---------------------------------------------------------------------------
# Sync logs
# ---------------------------------------------------------------------------


def test_get_sync_logs(hub):
    """get_sync_logs returns logs for an integration."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    hub.sync(integration.id)
    hub.sync(integration.id)

    logs = hub.get_sync_logs(integration.id)
    assert len(logs) == 2
    assert all(isinstance(l, SyncLog) for l in logs)


def test_get_sync_logs_respects_limit(hub):
    """get_sync_logs respects the limit parameter."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    for _ in range(5):
        hub.sync(integration.id)

    logs = hub.get_sync_logs(integration.id, limit=2)
    assert len(logs) == 2


# ---------------------------------------------------------------------------
# Available integrations catalog
# ---------------------------------------------------------------------------


def test_get_available_integrations(hub):
    """get_available_integrations returns the full catalog."""
    catalog = hub.get_available_integrations()

    assert isinstance(catalog, list)
    assert len(catalog) == len(IntegrationType)

    types = {entry["type"] for entry in catalog}
    assert "slack" in types
    assert "salesforce" in types

    for entry in catalog:
        assert "description" in entry
        assert "required_config_fields" in entry
        assert "optional_config_fields" in entry
        assert "supports_inbound" in entry
        assert "supports_outbound" in entry


# ---------------------------------------------------------------------------
# Enable / Disable
# ---------------------------------------------------------------------------


def test_enable(hub):
    """enable() sets enabled to True."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    hub.disable(integration.id)
    assert integration.enabled is False

    hub.enable(integration.id)
    assert integration.enabled is True


def test_disable(hub):
    """disable() sets enabled to False."""
    integration = hub.connect("t1", IntegrationType.SLACK, "S", _slack_config())
    hub.disable(integration.id)
    assert integration.enabled is False


def test_enable_not_found(hub):
    """enable() raises KeyError for missing integration."""
    with pytest.raises(KeyError):
        hub.enable("ghost")


def test_disable_not_found(hub):
    """disable() raises KeyError for missing integration."""
    with pytest.raises(KeyError):
        hub.disable("ghost")


# ---------------------------------------------------------------------------
# Integration health
# ---------------------------------------------------------------------------


def test_integration_health(hub):
    """get_integration_health returns correct aggregate data."""
    hub.connect("t1", IntegrationType.SLACK, "S1", _slack_config())
    i2 = hub.connect("t1", IntegrationType.EMAIL_SMTP, "SMTP", _smtp_config())
    hub.sync(i2.id)

    # Force one to error
    i3 = hub.connect(
        "t1",
        IntegrationType.HUBSPOT,
        "HS",
        {"api_key": "k", "simulate_failure": True},
    )
    hub.test_connection(i3.id)

    health = hub.get_integration_health("t1")
    assert health["total"] == 3
    assert health["connected"] == 2
    assert health["errors"] == 1
    assert health["last_sync"] is not None


def test_integration_health_empty_tenant(hub):
    """Health for a tenant with no integrations returns zeros."""
    health = hub.get_integration_health("nobody")
    assert health["total"] == 0
    assert health["connected"] == 0
    assert health["errors"] == 0
    assert health["last_sync"] is None


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


def test_multi_tenant_isolation(hub):
    """Integrations from different tenants do not leak across tenants."""
    hub.connect("t1", IntegrationType.SLACK, "S1", _slack_config())
    hub.connect("t2", IntegrationType.SLACK, "S2", _slack_config())
    hub.connect("t2", IntegrationType.EMAIL_SMTP, "SMTP2", _smtp_config())

    t1 = hub.list_integrations("t1")
    t2 = hub.list_integrations("t2")

    assert len(t1) == 1
    assert len(t2) == 2
    assert all(i.tenant_id == "t1" for i in t1)
    assert all(i.tenant_id == "t2" for i in t2)


# ---------------------------------------------------------------------------
# Required fields validation per type
# ---------------------------------------------------------------------------


def test_required_fields_validation_salesforce(hub):
    """Salesforce requires client_id, client_secret, instance_url."""
    with pytest.raises(ValueError, match="client_id"):
        hub.connect("t1", IntegrationType.SALESFORCE, "SF", {"instance_url": "https://x"})


def test_required_fields_validation_stripe(hub):
    """Stripe requires api_key."""
    with pytest.raises(ValueError, match="api_key"):
        hub.connect("t1", IntegrationType.STRIPE, "Stripe", {})


def test_required_fields_validation_twilio(hub):
    """Twilio requires account_sid, auth_token, from_number."""
    with pytest.raises(ValueError, match="Missing required config fields"):
        hub.connect("t1", IntegrationType.TWILIO, "Twilio", {"account_sid": "sid"})


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_singleton_import():
    """The module exports a singleton integrations_hub instance."""
    from xcapitsff.core.integrations_hub import integrations_hub as singleton

    assert isinstance(singleton, IntegrationsHub)


# ---------------------------------------------------------------------------
# Catalog completeness
# ---------------------------------------------------------------------------


def test_catalog_covers_all_types():
    """Every IntegrationType has a catalog entry."""
    for itype in IntegrationType:
        assert itype in INTEGRATION_CATALOG, f"Missing catalog entry for {itype}"
