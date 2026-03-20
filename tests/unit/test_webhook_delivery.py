"""Tests for the outbound webhook delivery system."""

from datetime import datetime, timedelta

import pytest

from xcapitsff.core.webhook_delivery import (
    DeliveryStatus,
    MAX_CONSECUTIVE_FAILURES,
    RETRY_BACKOFF_SECONDS,
    WebhookDelivery,
    WebhookEndpoint,
    WebhookManager,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr():
    """Return a fresh WebhookManager with no pre-registered endpoints."""
    return WebhookManager()


@pytest.fixture
def mgr_with_endpoint(mgr):
    """Return a WebhookManager with one active endpoint subscribed to lead events."""
    ep = mgr.register_endpoint(
        tenant_id="t1",
        url="https://example.com/hook",
        secret="s3cret",
        events=["lead.created", "lead.updated"],
    )
    return mgr, ep


# ---------------------------------------------------------------------------
# Endpoint registration
# ---------------------------------------------------------------------------


def test_register_endpoint(mgr):
    """Registering an endpoint stores it and returns a populated dataclass."""
    ep = mgr.register_endpoint(
        tenant_id="t1",
        url="https://example.com/hook",
        secret="my_secret",
        events=["lead.created"],
    )

    assert isinstance(ep, WebhookEndpoint)
    assert ep.tenant_id == "t1"
    assert ep.url == "https://example.com/hook"
    assert ep.secret == "my_secret"
    assert ep.events == ["lead.created"]
    assert ep.active is True
    assert ep.failure_count == 0
    assert ep.id in mgr._endpoints


def test_register_multiple_endpoints(mgr):
    """Multiple endpoints can be registered for the same tenant."""
    ep1 = mgr.register_endpoint("t1", "https://a.com/hook", "s1", ["lead.created"])
    ep2 = mgr.register_endpoint("t1", "https://b.com/hook", "s2", ["ticket.created"])

    assert len(mgr.list_endpoints("t1")) == 2
    assert ep1.id != ep2.id


# ---------------------------------------------------------------------------
# HMAC signature
# ---------------------------------------------------------------------------


def test_sign_payload_returns_sha256_prefixed(mgr):
    """Signature should be prefixed with 'sha256='."""
    sig = mgr._sign_payload("secret", {"key": "value"})
    assert sig.startswith("sha256=")
    assert len(sig) > len("sha256=")


def test_sign_payload_deterministic(mgr):
    """Same secret + payload must produce the same signature."""
    payload = {"event": "lead.created", "id": 42}
    sig1 = mgr._sign_payload("secret", payload)
    sig2 = mgr._sign_payload("secret", payload)
    assert sig1 == sig2


def test_sign_payload_different_secret(mgr):
    """Different secrets must produce different signatures."""
    payload = {"event": "test"}
    sig1 = mgr._sign_payload("secret_a", payload)
    sig2 = mgr._sign_payload("secret_b", payload)
    assert sig1 != sig2


def test_sign_payload_different_payload(mgr):
    """Different payloads must produce different signatures."""
    sig1 = mgr._sign_payload("secret", {"a": 1})
    sig2 = mgr._sign_payload("secret", {"a": 2})
    assert sig1 != sig2


# ---------------------------------------------------------------------------
# Delivery queuing
# ---------------------------------------------------------------------------


def test_deliver_queues_to_matching_endpoints(mgr_with_endpoint):
    """deliver() should create a delivery for each matching active endpoint."""
    mgr, ep = mgr_with_endpoint
    deliveries = mgr.deliver("lead.created", "t1", {"id": 1})

    assert len(deliveries) == 1
    d = deliveries[0]
    assert d.endpoint_id == ep.id
    assert d.event_type == "lead.created"
    assert d.payload == {"id": 1}
    assert d.status == DeliveryStatus.PENDING
    assert d.attempt_count == 0


def test_deliver_skips_inactive_endpoints(mgr_with_endpoint):
    """Inactive endpoints should not receive deliveries."""
    mgr, ep = mgr_with_endpoint
    ep.active = False

    deliveries = mgr.deliver("lead.created", "t1", {"id": 1})
    assert deliveries == []


def test_deliver_skips_non_matching_events(mgr_with_endpoint):
    """Endpoints not subscribed to the event type should be skipped."""
    mgr, ep = mgr_with_endpoint
    deliveries = mgr.deliver("ticket.created", "t1", {"id": 1})
    assert deliveries == []


def test_deliver_skips_other_tenants(mgr_with_endpoint):
    """Endpoints belonging to a different tenant should be skipped."""
    mgr, ep = mgr_with_endpoint
    deliveries = mgr.deliver("lead.created", "other_tenant", {"id": 1})
    assert deliveries == []


# ---------------------------------------------------------------------------
# Attempt delivery (mock)
# ---------------------------------------------------------------------------


def test_attempt_delivery_success(mgr_with_endpoint):
    """Successful delivery sets status to DELIVERED and resets failure count."""
    mgr, ep = mgr_with_endpoint
    deliveries = mgr.deliver("lead.created", "t1", {"id": 1})
    d = deliveries[0]

    mgr._attempt_delivery(d)

    assert d.status == DeliveryStatus.DELIVERED
    assert d.response_status == 200
    assert d.delivered_at is not None
    assert ep.failure_count == 0
    assert ep.last_success_at is not None


def test_attempt_delivery_failure(mgr):
    """Delivery to a /fail URL should fail and increment failure_count."""
    ep = mgr.register_endpoint("t1", "https://example.com/fail", "s", ["e"])
    deliveries = mgr.deliver("e", "t1", {"x": 1})
    d = deliveries[0]

    mgr._attempt_delivery(d)

    assert d.response_status == 500
    assert d.attempt_count == 1
    assert ep.failure_count == 1
    assert ep.last_failure_at is not None
    # Should be pending for retry (not dead yet)
    assert d.status == DeliveryStatus.PENDING


def test_attempt_delivery_orphaned_endpoint(mgr):
    """Delivery whose endpoint was deleted should be marked DEAD."""
    ep = mgr.register_endpoint("t1", "https://example.com/hook", "s", ["e"])
    deliveries = mgr.deliver("e", "t1", {"x": 1})
    d = deliveries[0]

    # Delete endpoint without using delete_endpoint (which cleans deliveries)
    del mgr._endpoints[ep.id]

    mgr._attempt_delivery(d)
    assert d.status == DeliveryStatus.DEAD


# ---------------------------------------------------------------------------
# Retry & exponential backoff
# ---------------------------------------------------------------------------


def test_retry_exponential_backoff_timing(mgr):
    """Each retry should schedule the next attempt with increasing delay."""
    ep = mgr.register_endpoint("t1", "https://example.com/fail", "s", ["e"])
    deliveries = mgr.deliver("e", "t1", {"x": 1})
    d = deliveries[0]

    for attempt in range(4):
        before = datetime.now()
        mgr._attempt_delivery(d)
        expected_backoff = RETRY_BACKOFF_SECONDS[min(attempt, len(RETRY_BACKOFF_SECONDS) - 1)]

        assert d.next_retry_at is not None
        delta = (d.next_retry_at - before).total_seconds()
        # Allow 2-second tolerance for timing
        assert abs(delta - expected_backoff) < 2, (
            f"Attempt {attempt + 1}: expected ~{expected_backoff}s backoff, got {delta:.1f}s"
        )


def test_max_attempts_then_dead(mgr):
    """After max_attempts (5), delivery should be marked DEAD."""
    ep = mgr.register_endpoint("t1", "https://example.com/fail", "s", ["e"])
    deliveries = mgr.deliver("e", "t1", {"x": 1})
    d = deliveries[0]

    for _ in range(5):
        mgr._attempt_delivery(d)

    assert d.status == DeliveryStatus.DEAD
    assert d.attempt_count == 5


def test_retry_failed_processes_due_retries(mgr):
    """retry_failed() should re-attempt deliveries whose retry time has passed."""
    ep = mgr.register_endpoint("t1", "https://example.com/fail", "s", ["e"])
    deliveries = mgr.deliver("e", "t1", {"x": 1})
    d = deliveries[0]

    # First attempt — fails and schedules retry
    mgr._attempt_delivery(d)
    assert d.attempt_count == 1
    assert d.status == DeliveryStatus.PENDING

    # Move next_retry_at to the past so retry_failed picks it up
    d.next_retry_at = datetime.now() - timedelta(seconds=1)

    retried = mgr.retry_failed()
    assert d.id in retried
    assert d.attempt_count == 2


def test_retry_failed_skips_future_retries(mgr):
    """retry_failed() should not process deliveries whose retry time is in the future."""
    ep = mgr.register_endpoint("t1", "https://example.com/fail", "s", ["e"])
    deliveries = mgr.deliver("e", "t1", {"x": 1})
    d = deliveries[0]

    mgr._attempt_delivery(d)
    # next_retry_at is already in the future — should be skipped
    retried = mgr.retry_failed()
    assert retried == []


# ---------------------------------------------------------------------------
# Auto-disable (circuit breaker)
# ---------------------------------------------------------------------------


def test_auto_disable_after_consecutive_failures(mgr):
    """Endpoint should be auto-disabled after MAX_CONSECUTIVE_FAILURES."""
    ep = mgr.register_endpoint("t1", "https://example.com/fail", "s", ["e"])

    # Simulate many failures by setting failure_count just below threshold
    ep.failure_count = MAX_CONSECUTIVE_FAILURES - 1

    deliveries = mgr.deliver("e", "t1", {"x": 1})
    d = deliveries[0]
    mgr._attempt_delivery(d)

    assert ep.failure_count == MAX_CONSECUTIVE_FAILURES
    assert ep.active is False


# ---------------------------------------------------------------------------
# Delivery stats
# ---------------------------------------------------------------------------


def test_delivery_stats_empty(mgr):
    """Stats for a tenant with no deliveries should return zeroes."""
    stats = mgr.get_delivery_stats("t1")
    assert stats["total_deliveries"] == 0
    assert stats["total_delivered"] == 0
    assert stats["success_rate"] == 0.0


def test_delivery_stats_mixed(mgr):
    """Stats should correctly aggregate across multiple deliveries."""
    ep = mgr.register_endpoint("t1", "https://example.com/hook", "s", ["e"])

    # Create and deliver several events
    for i in range(5):
        ds = mgr.deliver("e", "t1", {"i": i})
        for d in ds:
            mgr._attempt_delivery(d)

    stats = mgr.get_delivery_stats("t1")
    assert stats["total_deliveries"] == 5
    assert stats["total_delivered"] == 5
    assert stats["success_rate"] == 100.0


# ---------------------------------------------------------------------------
# Update endpoint
# ---------------------------------------------------------------------------


def test_update_endpoint_url(mgr_with_endpoint):
    """Updating the URL should persist the change."""
    mgr, ep = mgr_with_endpoint
    updated = mgr.update_endpoint(ep.id, url="https://new.example.com/hook")

    assert updated.url == "https://new.example.com/hook"
    assert updated.id == ep.id


def test_update_endpoint_events(mgr_with_endpoint):
    """Updating the events list should replace the old one."""
    mgr, ep = mgr_with_endpoint
    updated = mgr.update_endpoint(ep.id, events=["ticket.created"])

    assert updated.events == ["ticket.created"]


def test_update_endpoint_reactivate_resets_failures(mgr_with_endpoint):
    """Re-activating an endpoint should reset its failure_count."""
    mgr, ep = mgr_with_endpoint
    ep.active = False
    ep.failure_count = 30

    updated = mgr.update_endpoint(ep.id, active=True)
    assert updated.active is True
    assert updated.failure_count == 0


def test_update_endpoint_not_found(mgr):
    """Updating a non-existent endpoint should raise KeyError."""
    with pytest.raises(KeyError, match="not found"):
        mgr.update_endpoint("nonexistent", url="https://x.com")


# ---------------------------------------------------------------------------
# Delete endpoint
# ---------------------------------------------------------------------------


def test_delete_endpoint(mgr_with_endpoint):
    """Deleting an endpoint removes it and its deliveries."""
    mgr, ep = mgr_with_endpoint
    mgr.deliver("lead.created", "t1", {"id": 1})

    mgr.delete_endpoint(ep.id)

    assert ep.id not in mgr._endpoints
    assert len(mgr._deliveries) == 0


def test_delete_endpoint_not_found(mgr):
    """Deleting a non-existent endpoint should raise KeyError."""
    with pytest.raises(KeyError, match="not found"):
        mgr.delete_endpoint("nonexistent")


# ---------------------------------------------------------------------------
# Test event delivery
# ---------------------------------------------------------------------------


def test_test_event_delivery(mgr_with_endpoint):
    """Sending a test event should deliver to matching endpoints immediately."""
    mgr, ep = mgr_with_endpoint
    deliveries = mgr.deliver("lead.created", "t1", {"test": True})

    assert len(deliveries) == 1
    d = deliveries[0]
    mgr._attempt_delivery(d)

    assert d.status == DeliveryStatus.DELIVERED
    assert d.response_status == 200


# ---------------------------------------------------------------------------
# Get deliveries
# ---------------------------------------------------------------------------


def test_get_deliveries_all(mgr_with_endpoint):
    """get_deliveries without status filter returns all deliveries."""
    mgr, ep = mgr_with_endpoint
    mgr.deliver("lead.created", "t1", {"id": 1})
    mgr.deliver("lead.updated", "t1", {"id": 1})

    deliveries = mgr.get_deliveries(ep.id)
    assert len(deliveries) == 2


def test_get_deliveries_by_status(mgr_with_endpoint):
    """get_deliveries with status filter only returns matching deliveries."""
    mgr, ep = mgr_with_endpoint
    ds = mgr.deliver("lead.created", "t1", {"id": 1})
    mgr._attempt_delivery(ds[0])

    pending = mgr.get_deliveries(ep.id, status=DeliveryStatus.PENDING)
    delivered = mgr.get_deliveries(ep.id, status=DeliveryStatus.DELIVERED)

    assert len(pending) == 0
    assert len(delivered) == 1


# ---------------------------------------------------------------------------
# List endpoints for tenant
# ---------------------------------------------------------------------------


def test_list_endpoints_filters_by_tenant(mgr):
    """list_endpoints should only return endpoints for the specified tenant."""
    mgr.register_endpoint("t1", "https://a.com/hook", "s1", ["e"])
    mgr.register_endpoint("t2", "https://b.com/hook", "s2", ["e"])

    assert len(mgr.list_endpoints("t1")) == 1
    assert len(mgr.list_endpoints("t2")) == 1
    assert len(mgr.list_endpoints("t3")) == 0
