"""Tasks & Reminders management system.

Provides a task and reminder manager for tracking to-dos, follow-ups,
calls, meetings, demos, and proposals linked to CRM entities (leads,
tickets, contacts, deals).  Supports recurring tasks, due-date filtering,
overdue detection, and per-user statistics.

All storage is in-memory for simplicity; swap with DB-backed storage later.
"""

from __future__ import annotations

import enum
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, enum.Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    FOLLOW_UP = "follow_up"
    DEMO = "demo"
    PROPOSAL = "proposal"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Task:
    """A single task / to-do item."""

    id: str
    tenant_id: str
    title: str
    description: str = ""
    type: TaskType = TaskType.CUSTOM
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    assigned_to: str | None = None
    created_by: str | None = None
    entity_type: str | None = None  # lead / ticket / contact / deal / none
    entity_id: str | None = None
    due_date: str | None = None  # YYYY-MM-DD
    due_time: str | None = None  # HH:MM (24h)
    completed_at: str | None = None
    tags: list[str] = field(default_factory=list)
    recurring: bool = False
    recurrence_pattern: str | None = None  # daily / weekly / monthly
    created_at: str = field(default_factory=lambda: datetime.now(tz=None).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=None).isoformat())


@dataclass
class Reminder:
    """A reminder attached to a task."""

    id: str
    task_id: str
    remind_at: str  # ISO-8601 datetime string
    method: str = "in_app"  # in_app / email / both
    sent: bool = False


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class TaskManager:
    """In-memory task & reminder manager."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._reminders: dict[str, Reminder] = {}

    # -- helpers -------------------------------------------------------------

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    @property
    def reminder_count(self) -> int:
        return len(self._reminders)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(tz=None).isoformat()

    @staticmethod
    def _today_str() -> str:
        return datetime.now(tz=None).strftime("%Y-%m-%d")

    # -- CRUD ----------------------------------------------------------------

    def create(self, tenant_id: str, title: str, **kwargs) -> Task:
        """Create a new task."""
        task_id = uuid.uuid4().hex[:12]
        now = self._now_iso()

        # Coerce enums if given as strings
        if "type" in kwargs and isinstance(kwargs["type"], str):
            kwargs["type"] = TaskType(kwargs["type"])
        if "priority" in kwargs and isinstance(kwargs["priority"], str):
            kwargs["priority"] = TaskPriority(kwargs["priority"])
        if "status" in kwargs and isinstance(kwargs["status"], str):
            kwargs["status"] = TaskStatus(kwargs["status"])

        task = Task(
            id=task_id,
            tenant_id=tenant_id,
            title=title,
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._tasks[task_id] = task
        logger.info("Task created: %s (tenant=%s)", task_id, tenant_id)
        return task

    def update(self, task_id: str, **kwargs) -> Task | None:
        """Update fields on an existing task. Returns None if not found."""
        task = self._tasks.get(task_id)
        if task is None:
            return None

        # Coerce enums
        if "type" in kwargs and isinstance(kwargs["type"], str):
            kwargs["type"] = TaskType(kwargs["type"])
        if "priority" in kwargs and isinstance(kwargs["priority"], str):
            kwargs["priority"] = TaskPriority(kwargs["priority"])
        if "status" in kwargs and isinstance(kwargs["status"], str):
            kwargs["status"] = TaskStatus(kwargs["status"])

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = self._now_iso()
        return task

    def delete(self, task_id: str) -> bool:
        """Delete a task and its reminders. Returns True if found."""
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        # Remove associated reminders
        to_remove = [rid for rid, r in self._reminders.items() if r.task_id == task_id]
        for rid in to_remove:
            del self._reminders[rid]
        logger.info("Task deleted: %s", task_id)
        return True

    def get(self, task_id: str) -> Task | None:
        """Get a task by id."""
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        tenant_id: str,
        assigned_to: str | None = None,
        status: str | TaskStatus | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        due_date: str | None = None,
        priority: str | TaskPriority | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """List tasks with optional filters, pagination."""
        results = [t for t in self._tasks.values() if t.tenant_id == tenant_id]

        if assigned_to is not None:
            results = [t for t in results if t.assigned_to == assigned_to]
        if status is not None:
            status_val = status if isinstance(status, str) else status.value
            results = [t for t in results if t.status.value == status_val]
        if entity_type is not None:
            results = [t for t in results if t.entity_type == entity_type]
        if entity_id is not None:
            results = [t for t in results if t.entity_id == entity_id]
        if due_date is not None:
            results = [t for t in results if t.due_date == due_date]
        if priority is not None:
            priority_val = priority if isinstance(priority, str) else priority.value
            results = [t for t in results if t.priority.value == priority_val]

        # Sort by created_at descending
        results.sort(key=lambda t: t.created_at, reverse=True)
        return results[offset : offset + limit]

    # -- Status transitions --------------------------------------------------

    def complete(self, task_id: str) -> Task | None:
        """Mark a task as DONE and record completion timestamp."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = TaskStatus.DONE
        task.completed_at = self._now_iso()
        task.updated_at = self._now_iso()
        logger.info("Task completed: %s", task_id)
        return task

    def cancel(self, task_id: str) -> Task | None:
        """Mark a task as CANCELLED."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = TaskStatus.CANCELLED
        task.updated_at = self._now_iso()
        logger.info("Task cancelled: %s", task_id)
        return task

    def reassign(self, task_id: str, new_assignee: str) -> Task | None:
        """Reassign a task to a different user."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.assigned_to = new_assignee
        task.updated_at = self._now_iso()
        logger.info("Task %s reassigned to %s", task_id, new_assignee)
        return task

    # -- Query helpers -------------------------------------------------------

    def get_overdue(self, tenant_id: str) -> list[Task]:
        """Return tasks that are past their due_date and not done/cancelled."""
        today = self._today_str()
        results: list[Task] = []
        for t in self._tasks.values():
            if t.tenant_id != tenant_id:
                continue
            if t.status in (TaskStatus.DONE, TaskStatus.CANCELLED):
                continue
            if t.due_date and t.due_date < today:
                results.append(t)
        return results

    def get_today(self, tenant_id: str, user_id: str) -> list[Task]:
        """Return tasks due today for a specific user."""
        today = self._today_str()
        return [
            t
            for t in self._tasks.values()
            if t.tenant_id == tenant_id
            and t.assigned_to == user_id
            and t.due_date == today
            and t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
        ]

    def get_upcoming(self, tenant_id: str, user_id: str, days: int = 7) -> list[Task]:
        """Return tasks due within the next *days* for a specific user."""
        today = datetime.now(tz=None).date()
        end = today + timedelta(days=days)
        today_str = today.isoformat()
        end_str = end.isoformat()
        return [
            t
            for t in self._tasks.values()
            if t.tenant_id == tenant_id
            and t.assigned_to == user_id
            and t.due_date is not None
            and today_str <= t.due_date <= end_str
            and t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
        ]

    # -- Reminders -----------------------------------------------------------

    def add_reminder(
        self,
        task_id: str,
        remind_at: str,
        method: str = "in_app",
    ) -> Reminder | None:
        """Attach a reminder to a task. Returns None if task not found."""
        if task_id not in self._tasks:
            return None
        reminder_id = uuid.uuid4().hex[:12]
        reminder = Reminder(
            id=reminder_id,
            task_id=task_id,
            remind_at=remind_at,
            method=method,
        )
        self._reminders[reminder_id] = reminder
        logger.info("Reminder %s added to task %s", reminder_id, task_id)
        return reminder

    def get_due_reminders(self) -> list[Reminder]:
        """Return reminders whose remind_at is at or before now and not yet sent."""
        now_iso = self._now_iso()
        return [
            r
            for r in self._reminders.values()
            if not r.sent and r.remind_at <= now_iso
        ]

    def mark_reminder_sent(self, reminder_id: str) -> bool:
        """Mark a reminder as sent. Returns True if found."""
        reminder = self._reminders.get(reminder_id)
        if reminder is None:
            return False
        reminder.sent = True
        return True

    # -- Statistics ----------------------------------------------------------

    def get_task_stats(self, tenant_id: str, user_id: str | None = None) -> dict:
        """Aggregate statistics for a tenant, optionally filtered by user."""
        tasks = [t for t in self._tasks.values() if t.tenant_id == tenant_id]
        if user_id is not None:
            tasks = [t for t in tasks if t.assigned_to == user_id]

        total = len(tasks)
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        done_count = 0
        completion_hours_total = 0.0
        today = self._today_str()

        for t in tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1
            if t.status == TaskStatus.DONE:
                done_count += 1
                if t.completed_at and t.created_at:
                    try:
                        created = datetime.fromisoformat(t.created_at)
                        completed = datetime.fromisoformat(t.completed_at)
                        delta_hours = (completed - created).total_seconds() / 3600
                        completion_hours_total += delta_hours
                    except (ValueError, TypeError):
                        pass

        overdue_count = len([
            t
            for t in tasks
            if t.due_date
            and t.due_date < today
            and t.status not in (TaskStatus.DONE, TaskStatus.CANCELLED)
        ])

        completion_rate = (done_count / total * 100) if total > 0 else 0.0
        avg_completion_hours = (
            round(completion_hours_total / done_count, 2) if done_count > 0 else 0.0
        )

        return {
            "total": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue_count": overdue_count,
            "completion_rate": round(completion_rate, 2),
            "avg_completion_hours": avg_completion_hours,
        }

    # -- Recurring tasks -----------------------------------------------------

    def create_recurring(self, task_id: str) -> Task | None:
        """Create the next occurrence of a recurring task.

        Copies the original task with a new due_date shifted by the
        recurrence pattern (daily / weekly / monthly).
        Returns None if the source task is not found or not recurring.
        """
        source = self._tasks.get(task_id)
        if source is None or not source.recurring or not source.recurrence_pattern:
            return None

        if not source.due_date:
            return None

        try:
            old_date = datetime.strptime(source.due_date, "%Y-%m-%d").date()
        except ValueError:
            return None

        pattern = source.recurrence_pattern.lower()
        if pattern == "daily":
            new_date = old_date + timedelta(days=1)
        elif pattern == "weekly":
            new_date = old_date + timedelta(weeks=1)
        elif pattern == "monthly":
            # Approximate month shift (30 days)
            new_date = old_date + timedelta(days=30)
        else:
            return None

        new_task = self.create(
            tenant_id=source.tenant_id,
            title=source.title,
            description=source.description,
            type=source.type,
            priority=source.priority,
            assigned_to=source.assigned_to,
            created_by=source.created_by,
            entity_type=source.entity_type,
            entity_id=source.entity_id,
            due_date=new_date.isoformat(),
            due_time=source.due_time,
            tags=list(source.tags),
            recurring=True,
            recurrence_pattern=source.recurrence_pattern,
        )
        logger.info(
            "Recurring task created: %s (from %s, next due %s)",
            new_task.id,
            task_id,
            new_date.isoformat(),
        )
        return new_task


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
task_manager = TaskManager()
