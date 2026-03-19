"""Task scheduler — periodic execution of background operations.

Provides a simple async task scheduler that manages periodic operations
such as SLA compliance checks, stale-lead detection, data-quality audits,
and event-bus cleanup.  Tasks are registered with a name and an interval;
the scheduler checks which tasks are due and runs them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Type alias for async task callbacks
AsyncCallback = Callable[[], Coroutine[Any, Any, Any]]


@dataclass
class ScheduledTask:
    """Metadata for a single periodic task."""

    name: str
    interval_seconds: float
    callback: AsyncCallback
    last_run: datetime | None = None
    next_run: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    run_count: int = 0
    last_error: str | None = None


class Scheduler:
    """Simple async task scheduler for periodic operations.

    Tasks are registered via :meth:`register` and executed by calling
    :meth:`run_pending` (typically on a timer or inside a lifespan loop).
    """

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        interval_seconds: float,
        callback: AsyncCallback,
    ) -> ScheduledTask:
        """Register a periodic task.

        If a task with the same *name* already exists it will be replaced.
        """
        task = ScheduledTask(
            name=name,
            interval_seconds=interval_seconds,
            callback=callback,
            next_run=datetime.now(),
        )
        self._tasks[name] = task
        logger.info("Registered scheduled task '%s' (every %ss)", name, interval_seconds)
        return task

    def unregister(self, name: str) -> bool:
        """Remove a task by name. Returns ``True`` if the task existed."""
        if name in self._tasks:
            del self._tasks[name]
            logger.info("Unregistered scheduled task '%s'", name)
            return True
        return False

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run_pending(self) -> list[str]:
        """Check all tasks and run any that are due.

        Returns the list of task names that were executed.
        """
        now = datetime.now()
        executed: list[str] = []

        for task in list(self._tasks.values()):
            if not task.is_active:
                continue
            if now >= task.next_run:
                await self._execute(task)
                executed.append(task.name)

        return executed

    async def run_once(self, name: str) -> dict[str, Any]:
        """Manually trigger a specific task by name.

        Returns a status dict with the outcome.
        """
        task = self._tasks.get(name)
        if task is None:
            return {"success": False, "error": f"Task '{name}' not found"}

        await self._execute(task)

        return {
            "success": task.last_error is None,
            "task": name,
            "run_count": task.run_count,
            "last_error": task.last_error,
        }

    async def _execute(self, task: ScheduledTask) -> None:
        """Run a single task and update its bookkeeping fields."""
        now = datetime.now()
        try:
            await task.callback()
            task.last_error = None
            logger.info("Task '%s' completed successfully", task.name)
        except Exception as exc:
            task.last_error = str(exc)
            logger.error("Task '%s' failed: %s", task.name, exc, exc_info=True)
        finally:
            task.last_run = now
            task.run_count += 1
            task.next_run = now + timedelta(seconds=task.interval_seconds)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Return a status summary for all registered tasks."""
        tasks_status = []
        for task in self._tasks.values():
            tasks_status.append({
                "name": task.name,
                "interval_seconds": task.interval_seconds,
                "is_active": task.is_active,
                "run_count": task.run_count,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat(),
                "last_error": task.last_error,
            })
        return {
            "total_tasks": len(self._tasks),
            "active_tasks": sum(1 for t in self._tasks.values() if t.is_active),
            "tasks": tasks_status,
        }

    def list_tasks(self) -> list[str]:
        """Return the names of all registered tasks."""
        return list(self._tasks.keys())


# ======================================================================
# Singleton scheduler & pre-registered tasks
# ======================================================================

scheduler = Scheduler()


# --- Default task callbacks -------------------------------------------

async def _sla_check_callback() -> None:
    """Run SLA compliance check using the SLA monitor."""
    from xcapitsff.core.database import async_session
    from xcapitsff.support.sla_monitor import check_sla_compliance

    async with async_session() as db:
        result = await check_sla_compliance(db)
        logger.info("SLA check complete: %s", result.summary())


async def _stale_leads_check_callback() -> None:
    """Find leads that have been sitting in early stages too long."""
    from xcapitsff.core.database import async_session
    from xcapitsff.core.data_quality import check_lead_quality

    async with async_session() as db:
        report = await check_lead_quality(db)
        stale = [d for d in report.details if "RAW stage" in d.description]
        logger.info(
            "Stale leads check: %d total issues, %d stale leads",
            report.issues_found,
            len(stale),
        )


async def _data_quality_check_callback() -> None:
    """Run a full data-quality sweep."""
    from xcapitsff.core.database import async_session
    from xcapitsff.core.data_quality import run_full_quality_check

    async with async_session() as db:
        report = await run_full_quality_check(db)
        logger.info(
            "Data quality check complete: %d total issues",
            report["summary"]["total_issues"],
        )


async def _event_cleanup_callback() -> None:
    """Trim old events from the event bus to reclaim memory."""
    from xcapitsff.core.events import event_bus

    before = len(event_bus._event_log)
    max_keep = event_bus._max_log_size
    if len(event_bus._event_log) > max_keep:
        event_bus._event_log = event_bus._event_log[-max_keep:]
    after = len(event_bus._event_log)
    logger.info("Event cleanup: %d -> %d events", before, after)


# --- Register default tasks -------------------------------------------

scheduler.register("sla_check", 15 * 60, _sla_check_callback)               # every 15 min
scheduler.register("stale_leads_check", 6 * 3600, _stale_leads_check_callback)  # every 6 hours
scheduler.register("data_quality_check", 24 * 3600, _data_quality_check_callback)  # every 24 hours
scheduler.register("event_cleanup", 12 * 3600, _event_cleanup_callback)       # every 12 hours
