"""Tests for enhanced activity log."""

from datetime import datetime, timedelta

from xcapitsff.core.activity_log import ActivityEntry, ActivityLog


def _make_log() -> ActivityLog:
    return ActivityLog()


# --- Basic logging ---


def test_log_creates_entry():
    al = _make_log()
    entry = al.log("t1", "u1", "create", "lead", 42, "Created lead #42")
    assert isinstance(entry, ActivityEntry)
    assert entry.tenant_id == "t1"
    assert entry.user_id == "u1"
    assert entry.action == "create"
    assert entry.entity_type == "lead"
    assert entry.entity_id == 42
    assert entry.description == "Created lead #42"
    assert entry.id  # uuid assigned


def test_log_with_changes():
    al = _make_log()
    entry = al.log(
        "t1", "u1", "update", "lead", 1, "Updated stage",
        changes={"stage": {"before": "raw", "after": "qualified"}},
    )
    assert entry.changes["stage"]["before"] == "raw"
    assert entry.changes["stage"]["after"] == "qualified"


def test_log_with_ip_and_ua():
    al = _make_log()
    entry = al.log(
        "t1", "u1", "create", "ticket", 5, "New ticket",
        ip="192.168.1.1", ua="Mozilla/5.0",
    )
    assert entry.ip_address == "192.168.1.1"
    assert entry.user_agent == "Mozilla/5.0"


# --- Retrieval with filters ---


def test_get_entries_all():
    al = _make_log()
    al.log("t1", "u1", "create", "lead", 1, "a")
    al.log("t1", "u2", "update", "lead", 1, "b")
    al.log("t1", "u1", "create", "ticket", 1, "c")

    entries = al.get_entries("t1")
    assert len(entries) == 3


def test_get_entries_by_entity_type():
    al = _make_log()
    al.log("t1", "u1", "create", "lead", 1, "a")
    al.log("t1", "u1", "create", "ticket", 1, "b")

    entries = al.get_entries("t1", entity_type="lead")
    assert len(entries) == 1
    assert entries[0].entity_type == "lead"


def test_get_entries_by_user_id():
    al = _make_log()
    al.log("t1", "u1", "create", "lead", 1, "a")
    al.log("t1", "u2", "create", "lead", 2, "b")

    entries = al.get_entries("t1", user_id="u1")
    assert len(entries) == 1


def test_get_entries_by_action():
    al = _make_log()
    al.log("t1", "u1", "create", "lead", 1, "a")
    al.log("t1", "u1", "update", "lead", 1, "b")
    al.log("t1", "u1", "delete", "lead", 1, "c")

    entries = al.get_entries("t1", action="update")
    assert len(entries) == 1
    assert entries[0].action == "update"


def test_get_entries_by_entity_id():
    al = _make_log()
    al.log("t1", "u1", "create", "lead", 1, "a")
    al.log("t1", "u1", "update", "lead", 1, "b")
    al.log("t1", "u1", "create", "lead", 2, "c")

    entries = al.get_entries("t1", entity_type="lead", entity_id=1)
    assert len(entries) == 2


def test_get_entries_newest_first():
    al = _make_log()
    al.log("t1", "u1", "create", "lead", 1, "first")
    al.log("t1", "u1", "update", "lead", 1, "second")

    entries = al.get_entries("t1")
    assert entries[0].description == "second"
    assert entries[1].description == "first"


def test_get_entries_with_limit_and_offset():
    al = _make_log()
    for i in range(10):
        al.log("t1", "u1", "create", "lead", i, f"entry-{i}")

    page1 = al.get_entries("t1", limit=3, offset=0)
    page2 = al.get_entries("t1", limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    ids_1 = {e.id for e in page1}
    ids_2 = {e.id for e in page2}
    assert ids_1.isdisjoint(ids_2)


# --- Entity history ---


def test_entity_history():
    al = _make_log()
    al.log("t1", "u1", "create", "lead", 42, "created")
    al.log("t1", "u1", "update", "lead", 42, "updated")
    al.log("t1", "u2", "assign", "lead", 42, "assigned")
    al.log("t1", "u1", "create", "lead", 43, "other lead")

    history = al.get_entity_history("lead", 42)
    assert len(history) == 3
    assert all(str(e.entity_id) == "42" for e in history)


def test_entity_history_string_id():
    al = _make_log()
    al.log("t1", "u1", "create", "document", "abc-123", "created")
    al.log("t1", "u1", "update", "document", "abc-123", "updated")

    history = al.get_entity_history("document", "abc-123")
    assert len(history) == 2


# --- User activity ---


def test_user_activity():
    al = _make_log()
    now = datetime.now()

    e_recent = al.log("t1", "u1", "create", "lead", 1, "recent")
    e_recent.created_at = now - timedelta(days=5)

    e_old = al.log("t1", "u1", "create", "lead", 2, "old")
    e_old.created_at = now - timedelta(days=60)

    activity = al.get_user_activity("t1", "u1", days=30)
    assert len(activity) == 1
    assert activity[0].description == "recent"


# --- Activity summary ---


def test_activity_summary():
    al = _make_log()
    now = datetime.now()

    for i in range(5):
        e = al.log("t1", "u1", "create", "lead", i, f"lead-{i}")
        e.created_at = now - timedelta(days=1)

    for i in range(3):
        e = al.log("t1", "u2", "update", "ticket", i, f"ticket-{i}")
        e.created_at = now - timedelta(days=2)

    summary = al.get_activity_summary("t1", days=7)
    assert summary["total_actions"] == 8
    assert summary["by_user"]["u1"] == 5
    assert summary["by_user"]["u2"] == 3
    assert summary["by_action"]["create"] == 5
    assert summary["by_action"]["update"] == 3
    assert summary["by_entity_type"]["lead"] == 5
    assert summary["by_entity_type"]["ticket"] == 3


def test_most_active_hour():
    al = _make_log()
    now = datetime.now()

    # Create entries at hour 14 (more) and hour 9 (fewer)
    for i in range(5):
        e = al.log("t1", "u1", "create", "lead", i, "h14")
        e.created_at = now.replace(hour=14, minute=0, second=0) - timedelta(days=1)

    for i in range(2):
        e = al.log("t1", "u1", "update", "lead", i, "h9")
        e.created_at = now.replace(hour=9, minute=0, second=0) - timedelta(days=1)

    summary = al.get_activity_summary("t1", days=7)
    assert summary["most_active_hour"] == 14


def test_activity_summary_empty():
    al = _make_log()
    summary = al.get_activity_summary("t1", days=7)
    assert summary["total_actions"] == 0
    assert summary["most_active_hour"] == 0


# --- Export audit trail ---


def test_export_audit_trail():
    al = _make_log()
    now = datetime.now()

    e1 = al.log("t1", "u1", "create", "lead", 1, "first")
    e1.created_at = now - timedelta(days=10)

    e2 = al.log("t1", "u1", "update", "lead", 1, "second")
    e2.created_at = now - timedelta(days=5)

    e3 = al.log("t1", "u1", "delete", "lead", 1, "third")
    e3.created_at = now - timedelta(days=1)

    start = now - timedelta(days=7)
    end = now

    records = al.export_audit_trail("t1", start, end)
    assert len(records) == 2  # e2 and e3, not e1 (too old)
    assert all(isinstance(r, dict) for r in records)
    assert records[0]["action"] == "update"
    assert records[1]["action"] == "delete"
    assert "created_at" in records[0]


def test_export_audit_trail_tenant_isolated():
    al = _make_log()
    now = datetime.now()

    e1 = al.log("t1", "u1", "create", "lead", 1, "tenant1")
    e1.created_at = now - timedelta(days=1)

    e2 = al.log("t2", "u1", "create", "lead", 2, "tenant2")
    e2.created_at = now - timedelta(days=1)

    start = now - timedelta(days=7)
    end = now

    t1_records = al.export_audit_trail("t1", start, end)
    t2_records = al.export_audit_trail("t2", start, end)

    assert len(t1_records) == 1
    assert t1_records[0]["description"] == "tenant1"
    assert len(t2_records) == 1
    assert t2_records[0]["description"] == "tenant2"


# --- Changes tracking ---


def test_changes_tracking_before_after():
    al = _make_log()
    entry = al.log(
        "t1", "u1", "update", "lead", 1, "Updated score",
        changes={
            "score": {"before": 50, "after": 85},
            "stage": {"before": "raw", "after": "qualified"},
        },
    )
    assert entry.changes["score"]["before"] == 50
    assert entry.changes["score"]["after"] == 85
    assert entry.changes["stage"]["before"] == "raw"
    assert entry.changes["stage"]["after"] == "qualified"
