"""Tests for SLA policy management system."""

from datetime import datetime, timedelta

from xcapitsff.core.sla_policies import (
    SLAPolicyManager,
    SLAPriority,
    SLATarget,
)


def _make_manager() -> SLAPolicyManager:
    return SLAPolicyManager()


def _default_targets() -> SLATarget:
    return SLATarget(
        first_response_minutes=60,
        resolution_minutes=240,
        update_frequency_minutes=30,
    )


# ---- CRUD ----


def test_create_policy():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Critical SLA",
        priority=SLAPriority.CRITICAL,
        targets=_default_targets(),
    )
    assert policy.name == "Critical SLA"
    assert policy.priority == SLAPriority.CRITICAL
    assert policy.tenant_id == "t1"
    assert policy.active is True
    assert policy.id is not None


def test_default_policies_setup():
    mgr = _make_manager()
    policies = mgr.setup_defaults("t1")
    assert len(policies) == 4
    priorities = {p.priority for p in policies}
    assert priorities == {
        SLAPriority.CRITICAL,
        SLAPriority.HIGH,
        SLAPriority.MEDIUM,
        SLAPriority.LOW,
    }


def test_list_policies():
    mgr = _make_manager()
    mgr.setup_defaults("t1")
    policies = mgr.list_policies("t1")
    assert len(policies) == 4


def test_policy_matching_by_priority():
    mgr = _make_manager()
    mgr.setup_defaults("t1")
    policy = mgr.get_policy_for_ticket("t1", SLAPriority.HIGH)
    assert policy is not None
    assert policy.priority == SLAPriority.HIGH


def test_policy_matching_returns_none_for_missing():
    mgr = _make_manager()
    result = mgr.get_policy_for_ticket("t1", SLAPriority.HIGH)
    assert result is None


def test_update_policy():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Test",
        priority=SLAPriority.LOW,
        targets=_default_targets(),
    )
    updated = mgr.update_policy(policy.id, name="Updated Name", active=False)
    assert updated.name == "Updated Name"
    assert updated.active is False


def test_update_policy_not_found():
    mgr = _make_manager()
    try:
        mgr.update_policy("nonexistent", name="X")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_delete_policy():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="To Delete",
        priority=SLAPriority.LOW,
        targets=_default_targets(),
    )
    assert mgr.delete_policy(policy.id) is True
    assert mgr.list_policies("t1") == []


def test_delete_policy_not_found():
    mgr = _make_manager()
    assert mgr.delete_policy("nonexistent") is False


# ---- SLA status calculation ----


def test_sla_status_within_sla():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Medium",
        priority=SLAPriority.MEDIUM,
        targets=SLATarget(
            first_response_minutes=480,
            resolution_minutes=1440,
            update_frequency_minutes=240,
        ),
    )
    created_at = datetime.now() - timedelta(minutes=10)
    first_response_at = created_at + timedelta(minutes=5)

    status = mgr.calculate_sla_status(
        ticket_id="ticket-1",
        policy_id=policy.id,
        created_at=created_at,
        first_response_at=first_response_at,
    )
    assert status.is_within_sla is True
    assert status.first_response_met is True
    assert status.resolution_met is None  # not resolved yet
    assert len(status.breaches) == 0


def test_sla_status_breached():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Strict",
        priority=SLAPriority.CRITICAL,
        targets=SLATarget(
            first_response_minutes=10,
            resolution_minutes=30,
            update_frequency_minutes=5,
        ),
    )
    created_at = datetime.now() - timedelta(minutes=60)
    first_response_at = created_at + timedelta(minutes=20)  # over 10-min target
    resolved_at = created_at + timedelta(minutes=50)  # over 30-min target

    status = mgr.calculate_sla_status(
        ticket_id="ticket-2",
        policy_id=policy.id,
        created_at=created_at,
        first_response_at=first_response_at,
        resolved_at=resolved_at,
    )
    assert status.is_within_sla is False
    assert status.first_response_met is False
    assert status.resolution_met is False
    assert len(status.breaches) == 2


def test_first_response_breach_detection():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="FR Breach",
        priority=SLAPriority.HIGH,
        targets=SLATarget(
            first_response_minutes=15,
            resolution_minutes=1440,
            update_frequency_minutes=60,
        ),
    )
    created_at = datetime.now() - timedelta(minutes=30)
    first_response_at = created_at + timedelta(minutes=20)  # late

    status = mgr.calculate_sla_status(
        ticket_id="ticket-3",
        policy_id=policy.id,
        created_at=created_at,
        first_response_at=first_response_at,
    )
    assert status.first_response_met is False
    breach_types = [b.breach_type for b in status.breaches]
    assert "first_response" in breach_types


def test_resolution_breach_detection():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Res Breach",
        priority=SLAPriority.MEDIUM,
        targets=SLATarget(
            first_response_minutes=480,
            resolution_minutes=60,
            update_frequency_minutes=30,
        ),
    )
    created_at = datetime.now() - timedelta(minutes=120)
    first_response_at = created_at + timedelta(minutes=5)
    resolved_at = created_at + timedelta(minutes=90)  # over 60-min target

    status = mgr.calculate_sla_status(
        ticket_id="ticket-4",
        policy_id=policy.id,
        created_at=created_at,
        first_response_at=first_response_at,
        resolved_at=resolved_at,
    )
    assert status.resolution_met is False
    breach_types = [b.breach_type for b in status.breaches]
    assert "resolution" in breach_types
    assert "first_response" not in breach_types


def test_time_remaining_calculation():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Time Remaining",
        priority=SLAPriority.LOW,
        targets=SLATarget(
            first_response_minutes=1440,
            resolution_minutes=4320,
            update_frequency_minutes=480,
        ),
    )
    created_at = datetime.now() - timedelta(minutes=100)

    status = mgr.calculate_sla_status(
        ticket_id="ticket-5",
        policy_id=policy.id,
        created_at=created_at,
    )
    # First response due in 1440 - 100 ≈ 1340 minutes
    assert status.time_remaining_minutes > 1300
    assert status.time_remaining_minutes < 1400


def test_time_remaining_resolved():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Resolved",
        priority=SLAPriority.LOW,
        targets=SLATarget(
            first_response_minutes=1440,
            resolution_minutes=4320,
            update_frequency_minutes=480,
        ),
    )
    created_at = datetime.now() - timedelta(minutes=100)
    resolved_at = created_at + timedelta(minutes=50)

    status = mgr.calculate_sla_status(
        ticket_id="ticket-5b",
        policy_id=policy.id,
        created_at=created_at,
        resolved_at=resolved_at,
    )
    assert status.time_remaining_minutes == 0.0


def test_business_hours_only():
    mgr = _make_manager()
    bh = {"start_hour": 9, "end_hour": 17, "timezone": "UTC", "working_days": [0, 1, 2, 3, 4]}
    policy = mgr.create_policy(
        tenant_id="t1",
        name="BH Policy",
        priority=SLAPriority.HIGH,
        targets=SLATarget(
            first_response_minutes=60,
            resolution_minutes=240,
            update_frequency_minutes=30,
        ),
        business_hours_only=True,
        business_hours=bh,
    )
    assert policy.business_hours_only is True
    assert policy.business_hours["start_hour"] == 9
    assert policy.business_hours["end_hour"] == 17

    # Verify deadline calculation extends beyond calendar time when BH apply.
    # Create ticket at 16:30 on a weekday — 60 min target should push into next day.
    # Use a known weekday: 2026-03-16 is a Monday.
    created_at = datetime(2026, 3, 16, 16, 30)
    status = mgr.calculate_sla_status(
        ticket_id="ticket-bh",
        policy_id=policy.id,
        created_at=created_at,
    )
    # 30 min left on Monday, 30 min on Tuesday → due at 09:30 Tue
    expected_due = datetime(2026, 3, 17, 9, 30)
    assert status.first_response_due == expected_due


# ---- Breach recording ----


def test_record_breach():
    mgr = _make_manager()
    breach = mgr.record_breach(
        tenant_id="t1",
        ticket_id="ticket-10",
        policy_id="pol-1",
        breach_type="first_response",
        target_minutes=60,
        actual_minutes=90,
    )
    assert breach.breach_type == "first_response"
    assert breach.actual_minutes == 90


def test_get_breaches_list():
    mgr = _make_manager()
    mgr.record_breach("t1", "ticket-1", "pol-1", "first_response", 60, 90)
    mgr.record_breach("t1", "ticket-2", "pol-1", "resolution", 240, 300)
    breaches = mgr.get_breaches("t1")
    assert len(breaches) == 2


def test_get_breaches_filters_by_tenant():
    mgr = _make_manager()
    mgr.record_breach("t1", "ticket-1", "pol-1", "first_response", 60, 90)
    mgr.record_breach("t2", "ticket-2", "pol-2", "resolution", 240, 300)
    assert len(mgr.get_breaches("t1")) == 1
    assert len(mgr.get_breaches("t2")) == 1


# ---- Compliance ----


def test_compliance_report():
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="High",
        priority=SLAPriority.HIGH,
        targets=_default_targets(),
    )
    mgr.record_breach("t1", "ticket-1", policy.id, "first_response", 60, 90)
    mgr.record_breach("t1", "ticket-2", policy.id, "resolution", 240, 300)

    compliance = mgr.get_sla_compliance("t1")
    assert compliance["total_tickets"] == 2
    assert compliance["breached"] == 2
    assert compliance["compliance_rate"] == 0.0
    assert compliance["avg_response_minutes"] == 90.0
    assert compliance["avg_resolution_minutes"] == 300.0
    assert "high" in compliance["by_priority"]


def test_compliance_no_breaches():
    mgr = _make_manager()
    compliance = mgr.get_sla_compliance("t1")
    assert compliance["total_tickets"] == 0
    assert compliance["compliance_rate"] == 100.0


# ---- Multi-tenant isolation ----


def test_multi_tenant_isolation():
    mgr = _make_manager()
    mgr.setup_defaults("tenant-a")
    mgr.setup_defaults("tenant-b")

    assert len(mgr.list_policies("tenant-a")) == 4
    assert len(mgr.list_policies("tenant-b")) == 4

    # Each tenant gets independent policies
    policy_a = mgr.get_policy_for_ticket("tenant-a", SLAPriority.CRITICAL)
    policy_b = mgr.get_policy_for_ticket("tenant-b", SLAPriority.CRITICAL)
    assert policy_a is not None
    assert policy_b is not None
    assert policy_a.id != policy_b.id

    # Breaches are isolated
    mgr.record_breach("tenant-a", "t-1", policy_a.id, "first_response", 60, 90)
    assert len(mgr.get_breaches("tenant-a")) == 1
    assert len(mgr.get_breaches("tenant-b")) == 0


# ---- Edge cases ----


def test_calculate_status_policy_not_found():
    mgr = _make_manager()
    try:
        mgr.calculate_sla_status(
            ticket_id="ticket-x",
            policy_id="nonexistent",
            created_at=datetime.now(),
        )
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_sla_status_no_response_yet_within_time():
    """No first response yet, but still within the SLA window."""
    mgr = _make_manager()
    policy = mgr.create_policy(
        tenant_id="t1",
        name="Fresh",
        priority=SLAPriority.LOW,
        targets=SLATarget(
            first_response_minutes=1440,
            resolution_minutes=4320,
            update_frequency_minutes=480,
        ),
    )
    created_at = datetime.now() - timedelta(minutes=5)
    status = mgr.calculate_sla_status(
        ticket_id="ticket-fresh",
        policy_id=policy.id,
        created_at=created_at,
    )
    assert status.first_response_met is None
    assert status.is_within_sla is True
