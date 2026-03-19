"""Tests for audit log."""

from xcapitsff.core.audit import AuditAction, AuditLog


def test_record_entry():
    log = AuditLog()
    entry = log.record(AuditAction.CREATE, "lead", 1, "system")
    assert entry.action == AuditAction.CREATE
    assert entry.entity_type == "lead"
    assert entry.entity_id == 1
    assert log.count == 1


def test_record_with_changes():
    log = AuditLog()
    entry = log.record(
        AuditAction.STAGE_CHANGE, "lead", 1, "pipeline",
        changes={"stage": {"old": "raw", "new": "qualified"}},
    )
    assert entry.changes["stage"]["old"] == "raw"


def test_query_by_entity():
    log = AuditLog()
    log.record(AuditAction.CREATE, "lead", 1)
    log.record(AuditAction.CREATE, "ticket", 1)
    log.record(AuditAction.UPDATE, "lead", 2)

    leads = log.query(entity_type="lead")
    assert len(leads) == 2
    tickets = log.query(entity_type="ticket")
    assert len(tickets) == 1


def test_query_by_action():
    log = AuditLog()
    log.record(AuditAction.CREATE, "lead", 1)
    log.record(AuditAction.UPDATE, "lead", 1)
    log.record(AuditAction.DELETE, "lead", 1)

    creates = log.query(action=AuditAction.CREATE)
    assert len(creates) == 1


def test_query_by_actor():
    log = AuditLog()
    log.record(AuditAction.CREATE, "lead", 1, "system")
    log.record(AuditAction.UPDATE, "lead", 1, "sales_qualifier")
    log.record(AuditAction.RESOLVE, "ticket", 1, "support_responder")

    agent_actions = log.query(actor="sales_qualifier")
    assert len(agent_actions) == 1


def test_entity_history():
    log = AuditLog()
    log.record(AuditAction.CREATE, "lead", 42)
    log.record(AuditAction.SCORE, "lead", 42)
    log.record(AuditAction.QUALIFY, "lead", 42)
    log.record(AuditAction.CREATE, "lead", 43)

    history = log.get_entity_history("lead", 42)
    assert len(history) == 3


def test_stats():
    log = AuditLog()
    log.record(AuditAction.CREATE, "lead", 1, "system")
    log.record(AuditAction.CREATE, "lead", 2, "webhook")
    log.record(AuditAction.RESOLVE, "ticket", 1, "support_responder")

    stats = log.get_stats()
    assert stats["total_entries"] == 3
    assert stats["by_action"]["create"] == 2
    assert stats["by_entity_type"]["lead"] == 2
    assert stats["by_actor"]["system"] == 1


def test_max_entries():
    log = AuditLog(max_entries=5)
    for i in range(10):
        log.record(AuditAction.CREATE, "lead", i)
    assert log.count == 5


def test_str_representation():
    log = AuditLog()
    entry = log.record(AuditAction.ESCALATE, "ticket", 99, "sla_monitor")
    assert "escalate" in str(entry)
    assert "ticket#99" in str(entry)
    assert "sla_monitor" in str(entry)
