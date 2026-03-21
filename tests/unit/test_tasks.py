"""Tests for Tasks & Reminders management system."""

from datetime import datetime, timedelta

from xcapitsff.core.tasks import (
    Reminder,
    Task,
    TaskManager,
    TaskPriority,
    TaskStatus,
    TaskType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today() -> str:
    return datetime.now(tz=None).strftime("%Y-%m-%d")


def _yesterday() -> str:
    return (datetime.now(tz=None) - timedelta(days=1)).strftime("%Y-%m-%d")


def _tomorrow() -> str:
    return (datetime.now(tz=None) + timedelta(days=1)).strftime("%Y-%m-%d")


def _days_from_now(n: int) -> str:
    return (datetime.now(tz=None) + timedelta(days=n)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


def test_create_task_basic():
    mgr = TaskManager()
    task = mgr.create("t1", "Call John")
    assert task.tenant_id == "t1"
    assert task.title == "Call John"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.MEDIUM
    assert task.type == TaskType.CUSTOM
    assert task.recurring is False
    assert mgr.task_count == 1


def test_create_task_with_all_fields():
    mgr = TaskManager()
    task = mgr.create(
        "t1",
        "Demo for Acme",
        description="Show product features",
        type=TaskType.DEMO,
        priority=TaskPriority.HIGH,
        assigned_to="user1",
        created_by="admin",
        entity_type="lead",
        entity_id="42",
        due_date=_tomorrow(),
        due_time="14:00",
        tags=["vip", "q1"],
        recurring=True,
        recurrence_pattern="weekly",
    )
    assert task.type == TaskType.DEMO
    assert task.priority == TaskPriority.HIGH
    assert task.assigned_to == "user1"
    assert task.entity_type == "lead"
    assert task.entity_id == "42"
    assert task.due_date == _tomorrow()
    assert task.due_time == "14:00"
    assert task.tags == ["vip", "q1"]
    assert task.recurring is True
    assert task.recurrence_pattern == "weekly"


def test_create_task_string_enum_coercion():
    mgr = TaskManager()
    task = mgr.create("t1", "Email follow-up", type="email", priority="urgent")
    assert task.type == TaskType.EMAIL
    assert task.priority == TaskPriority.URGENT


# ---------------------------------------------------------------------------
# Get / Update / Delete
# ---------------------------------------------------------------------------


def test_get_task():
    mgr = TaskManager()
    task = mgr.create("t1", "Task A")
    fetched = mgr.get(task.id)
    assert fetched is not None
    assert fetched.id == task.id


def test_get_nonexistent_returns_none():
    mgr = TaskManager()
    assert mgr.get("nonexistent") is None


def test_update_task():
    mgr = TaskManager()
    task = mgr.create("t1", "Original title")
    updated = mgr.update(task.id, title="Updated title", priority="high")
    assert updated is not None
    assert updated.title == "Updated title"
    assert updated.priority == TaskPriority.HIGH


def test_update_nonexistent_returns_none():
    mgr = TaskManager()
    assert mgr.update("nonexistent", title="x") is None


def test_delete_task():
    mgr = TaskManager()
    task = mgr.create("t1", "To delete")
    assert mgr.delete(task.id) is True
    assert mgr.get(task.id) is None
    assert mgr.task_count == 0


def test_delete_nonexistent_returns_false():
    mgr = TaskManager()
    assert mgr.delete("nonexistent") is False


def test_delete_task_removes_reminders():
    mgr = TaskManager()
    task = mgr.create("t1", "Task with reminder")
    mgr.add_reminder(task.id, "2099-01-01T00:00:00")
    assert mgr.reminder_count == 1
    mgr.delete(task.id)
    assert mgr.reminder_count == 0


# ---------------------------------------------------------------------------
# List with filters
# ---------------------------------------------------------------------------


def test_list_tasks_by_tenant():
    mgr = TaskManager()
    mgr.create("t1", "Task A")
    mgr.create("t2", "Task B")
    mgr.create("t1", "Task C")
    result = mgr.list_tasks("t1")
    assert len(result) == 2


def test_list_tasks_by_status():
    mgr = TaskManager()
    mgr.create("t1", "Todo task")
    t2 = mgr.create("t1", "Done task")
    mgr.complete(t2.id)
    result = mgr.list_tasks("t1", status="done")
    assert len(result) == 1
    assert result[0].id == t2.id


def test_list_tasks_by_assigned_to():
    mgr = TaskManager()
    mgr.create("t1", "Task A", assigned_to="alice")
    mgr.create("t1", "Task B", assigned_to="bob")
    result = mgr.list_tasks("t1", assigned_to="alice")
    assert len(result) == 1
    assert result[0].assigned_to == "alice"


def test_list_tasks_by_priority():
    mgr = TaskManager()
    mgr.create("t1", "Low task", priority="low")
    mgr.create("t1", "Urgent task", priority="urgent")
    result = mgr.list_tasks("t1", priority="urgent")
    assert len(result) == 1
    assert result[0].priority == TaskPriority.URGENT


def test_list_tasks_pagination():
    mgr = TaskManager()
    for i in range(10):
        mgr.create("t1", f"Task {i}")
    page1 = mgr.list_tasks("t1", limit=3, offset=0)
    page2 = mgr.list_tasks("t1", limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    ids1 = {t.id for t in page1}
    ids2 = {t.id for t in page2}
    assert ids1.isdisjoint(ids2)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def test_complete_task():
    mgr = TaskManager()
    task = mgr.create("t1", "Finish report")
    completed = mgr.complete(task.id)
    assert completed is not None
    assert completed.status == TaskStatus.DONE
    assert completed.completed_at is not None


def test_complete_nonexistent():
    mgr = TaskManager()
    assert mgr.complete("nope") is None


def test_cancel_task():
    mgr = TaskManager()
    task = mgr.create("t1", "Cancelled meeting")
    cancelled = mgr.cancel(task.id)
    assert cancelled is not None
    assert cancelled.status == TaskStatus.CANCELLED


def test_cancel_nonexistent():
    mgr = TaskManager()
    assert mgr.cancel("nope") is None


def test_reassign_task():
    mgr = TaskManager()
    task = mgr.create("t1", "Reassign me", assigned_to="alice")
    reassigned = mgr.reassign(task.id, "bob")
    assert reassigned is not None
    assert reassigned.assigned_to == "bob"


def test_reassign_nonexistent():
    mgr = TaskManager()
    assert mgr.reassign("nope", "bob") is None


# ---------------------------------------------------------------------------
# Overdue / Today / Upcoming
# ---------------------------------------------------------------------------


def test_get_overdue():
    mgr = TaskManager()
    mgr.create("t1", "Past due", due_date=_yesterday())
    mgr.create("t1", "Future task", due_date=_tomorrow())
    done = mgr.create("t1", "Done past", due_date=_yesterday())
    mgr.complete(done.id)
    overdue = mgr.get_overdue("t1")
    assert len(overdue) == 1
    assert overdue[0].title == "Past due"


def test_get_today():
    mgr = TaskManager()
    mgr.create("t1", "Today task", assigned_to="user1", due_date=_today())
    mgr.create("t1", "Tomorrow task", assigned_to="user1", due_date=_tomorrow())
    mgr.create("t1", "Other user today", assigned_to="user2", due_date=_today())
    today_tasks = mgr.get_today("t1", "user1")
    assert len(today_tasks) == 1
    assert today_tasks[0].title == "Today task"


def test_get_upcoming():
    mgr = TaskManager()
    mgr.create("t1", "In 3 days", assigned_to="user1", due_date=_days_from_now(3))
    mgr.create("t1", "In 10 days", assigned_to="user1", due_date=_days_from_now(10))
    mgr.create("t1", "In 5 days", assigned_to="user1", due_date=_days_from_now(5))
    upcoming = mgr.get_upcoming("t1", "user1", days=7)
    assert len(upcoming) == 2


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


def test_add_reminder():
    mgr = TaskManager()
    task = mgr.create("t1", "Task with reminder")
    reminder = mgr.add_reminder(task.id, "2099-12-31T23:59:59")
    assert reminder is not None
    assert reminder.task_id == task.id
    assert reminder.method == "in_app"
    assert reminder.sent is False


def test_add_reminder_custom_method():
    mgr = TaskManager()
    task = mgr.create("t1", "Task")
    reminder = mgr.add_reminder(task.id, "2099-01-01T00:00:00", method="email")
    assert reminder is not None
    assert reminder.method == "email"


def test_add_reminder_task_not_found():
    mgr = TaskManager()
    assert mgr.add_reminder("nonexistent", "2099-01-01T00:00:00") is None


def test_get_due_reminders():
    mgr = TaskManager()
    task = mgr.create("t1", "Task")
    # Past reminder should be due
    mgr.add_reminder(task.id, "2000-01-01T00:00:00")
    # Future reminder should not be due
    mgr.add_reminder(task.id, "2099-12-31T23:59:59")
    due = mgr.get_due_reminders()
    assert len(due) == 1


def test_mark_reminder_sent():
    mgr = TaskManager()
    task = mgr.create("t1", "Task")
    reminder = mgr.add_reminder(task.id, "2000-01-01T00:00:00")
    assert reminder is not None
    assert mgr.mark_reminder_sent(reminder.id) is True
    # After marking, should not appear in due list
    due = mgr.get_due_reminders()
    assert len(due) == 0


def test_mark_reminder_sent_nonexistent():
    mgr = TaskManager()
    assert mgr.mark_reminder_sent("nonexistent") is False


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def test_get_task_stats_empty():
    mgr = TaskManager()
    stats = mgr.get_task_stats("t1")
    assert stats["total"] == 0
    assert stats["completion_rate"] == 0.0


def test_get_task_stats_with_data():
    mgr = TaskManager()
    mgr.create("t1", "Task 1", priority="high", assigned_to="user1")
    mgr.create("t1", "Task 2", priority="low", assigned_to="user1")
    t3 = mgr.create("t1", "Task 3", priority="high", assigned_to="user1")
    mgr.complete(t3.id)
    t4 = mgr.create("t1", "Task 4", due_date=_yesterday(), assigned_to="user1")
    stats = mgr.get_task_stats("t1")
    assert stats["total"] == 4
    assert stats["by_status"]["done"] == 1
    assert stats["by_priority"]["high"] == 2
    assert stats["overdue_count"] == 1
    assert stats["completion_rate"] == 25.0


def test_get_task_stats_filtered_by_user():
    mgr = TaskManager()
    mgr.create("t1", "Alice task", assigned_to="alice")
    mgr.create("t1", "Bob task", assigned_to="bob")
    stats = mgr.get_task_stats("t1", user_id="alice")
    assert stats["total"] == 1


# ---------------------------------------------------------------------------
# Recurring tasks
# ---------------------------------------------------------------------------


def test_create_recurring_daily():
    mgr = TaskManager()
    task = mgr.create(
        "t1", "Daily standup",
        due_date=_today(),
        recurring=True,
        recurrence_pattern="daily",
        assigned_to="team",
    )
    new_task = mgr.create_recurring(task.id)
    assert new_task is not None
    assert new_task.id != task.id
    expected = _days_from_now(1)
    assert new_task.due_date == expected
    assert new_task.recurring is True
    assert new_task.recurrence_pattern == "daily"
    assert mgr.task_count == 2


def test_create_recurring_weekly():
    mgr = TaskManager()
    task = mgr.create("t1", "Weekly sync", due_date=_today(), recurring=True, recurrence_pattern="weekly")
    new_task = mgr.create_recurring(task.id)
    assert new_task is not None
    expected = _days_from_now(7)
    assert new_task.due_date == expected


def test_create_recurring_monthly():
    mgr = TaskManager()
    task = mgr.create("t1", "Monthly review", due_date=_today(), recurring=True, recurrence_pattern="monthly")
    new_task = mgr.create_recurring(task.id)
    assert new_task is not None
    expected = _days_from_now(30)
    assert new_task.due_date == expected


def test_create_recurring_non_recurring_returns_none():
    mgr = TaskManager()
    task = mgr.create("t1", "One-off task", recurring=False)
    assert mgr.create_recurring(task.id) is None


def test_create_recurring_no_due_date_returns_none():
    mgr = TaskManager()
    task = mgr.create("t1", "No date", recurring=True, recurrence_pattern="daily")
    assert mgr.create_recurring(task.id) is None


def test_create_recurring_nonexistent_returns_none():
    mgr = TaskManager()
    assert mgr.create_recurring("nonexistent") is None


# ---------------------------------------------------------------------------
# Entity linking
# ---------------------------------------------------------------------------


def test_list_tasks_by_entity():
    mgr = TaskManager()
    mgr.create("t1", "Lead follow-up", entity_type="lead", entity_id="100")
    mgr.create("t1", "Ticket check", entity_type="ticket", entity_id="200")
    mgr.create("t1", "Another lead task", entity_type="lead", entity_id="100")
    result = mgr.list_tasks("t1", entity_type="lead", entity_id="100")
    assert len(result) == 2
