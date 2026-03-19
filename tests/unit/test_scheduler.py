"""Tests for the task scheduler system."""

from datetime import datetime, timedelta

import pytest

from xcapitsff.core.scheduler import Scheduler, ScheduledTask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _noop_callback():
    """A no-op async callback for testing."""
    pass


async def _failing_callback():
    """A callback that always raises."""
    raise RuntimeError("task exploded")


async def _tracking_callback(tracker: list):
    """Append a timestamp to *tracker* so the caller can verify execution."""
    tracker.append(datetime.now())


# ---------------------------------------------------------------------------
# Scheduler core
# ---------------------------------------------------------------------------


@pytest.fixture
def sched():
    """Return a fresh Scheduler with no pre-registered tasks."""
    return Scheduler()


@pytest.mark.asyncio
async def test_register_task(sched):
    """Registering a task adds it to the task list."""
    task = sched.register("my_task", 60, _noop_callback)

    assert isinstance(task, ScheduledTask)
    assert task.name == "my_task"
    assert task.interval_seconds == 60
    assert task.is_active is True
    assert task.run_count == 0
    assert "my_task" in sched.list_tasks()


@pytest.mark.asyncio
async def test_unregister_task(sched):
    """Unregistering removes the task and returns True."""
    sched.register("temp", 10, _noop_callback)
    assert sched.unregister("temp") is True
    assert "temp" not in sched.list_tasks()


@pytest.mark.asyncio
async def test_unregister_missing_task(sched):
    """Unregistering a non-existent task returns False."""
    assert sched.unregister("does_not_exist") is False


@pytest.mark.asyncio
async def test_run_pending_executes_due_tasks(sched):
    """run_pending should execute tasks whose next_run is in the past."""
    tracker: list[datetime] = []

    async def cb():
        await _tracking_callback(tracker)

    sched.register("fast", 1, cb)
    # next_run was set to now(), so it should be due immediately
    executed = await sched.run_pending()

    assert "fast" in executed
    assert len(tracker) == 1


@pytest.mark.asyncio
async def test_run_pending_skips_inactive(sched):
    """Inactive tasks are not executed by run_pending."""
    tracker: list[datetime] = []

    async def cb():
        await _tracking_callback(tracker)

    sched.register("paused", 1, cb)
    sched._tasks["paused"].is_active = False

    executed = await sched.run_pending()

    assert executed == []
    assert len(tracker) == 0


@pytest.mark.asyncio
async def test_run_pending_skips_not_due(sched):
    """Tasks whose next_run is in the future are not executed."""
    tracker: list[datetime] = []

    async def cb():
        await _tracking_callback(tracker)

    sched.register("later", 3600, cb)
    sched._tasks["later"].next_run = datetime.now() + timedelta(hours=1)

    executed = await sched.run_pending()

    assert executed == []
    assert len(tracker) == 0


@pytest.mark.asyncio
async def test_run_once_success(sched):
    """run_once triggers a specific task and reports success."""
    sched.register("once_task", 999, _noop_callback)
    result = await sched.run_once("once_task")

    assert result["success"] is True
    assert result["task"] == "once_task"
    assert result["run_count"] == 1
    assert result["last_error"] is None


@pytest.mark.asyncio
async def test_run_once_missing(sched):
    """run_once for a non-existent task returns an error dict."""
    result = await sched.run_once("ghost")

    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_run_once_failing_callback(sched):
    """run_once captures the error but does not raise."""
    sched.register("bad", 60, _failing_callback)
    result = await sched.run_once("bad")

    assert result["success"] is False
    assert "task exploded" in result["last_error"]
    assert sched._tasks["bad"].run_count == 1


@pytest.mark.asyncio
async def test_task_run_count_increments(sched):
    """Each execution increments run_count."""
    sched.register("counter", 1, _noop_callback)
    await sched.run_once("counter")
    await sched.run_once("counter")
    await sched.run_once("counter")

    assert sched._tasks["counter"].run_count == 3


@pytest.mark.asyncio
async def test_next_run_updates_after_execution(sched):
    """After execution, next_run should be pushed into the future."""
    sched.register("updater", 300, _noop_callback)
    before = sched._tasks["updater"].next_run

    await sched.run_once("updater")

    after = sched._tasks["updater"].next_run
    assert after > before


@pytest.mark.asyncio
async def test_get_status(sched):
    """get_status returns a well-structured summary."""
    sched.register("alpha", 60, _noop_callback)
    sched.register("beta", 120, _noop_callback)
    sched._tasks["beta"].is_active = False

    status = sched.get_status()

    assert status["total_tasks"] == 2
    assert status["active_tasks"] == 1
    assert len(status["tasks"]) == 2
    names = {t["name"] for t in status["tasks"]}
    assert names == {"alpha", "beta"}


@pytest.mark.asyncio
async def test_list_tasks(sched):
    """list_tasks returns all registered task names."""
    sched.register("a", 1, _noop_callback)
    sched.register("b", 2, _noop_callback)

    assert set(sched.list_tasks()) == {"a", "b"}


@pytest.mark.asyncio
async def test_register_replaces_existing(sched):
    """Re-registering a task with the same name replaces it."""
    sched.register("dup", 60, _noop_callback)
    sched.register("dup", 120, _noop_callback)

    assert len(sched.list_tasks()) == 1
    assert sched._tasks["dup"].interval_seconds == 120


@pytest.mark.asyncio
async def test_last_run_is_set_after_execution(sched):
    """last_run should be None before first run, then populated."""
    sched.register("lr", 60, _noop_callback)
    assert sched._tasks["lr"].last_run is None

    await sched.run_once("lr")
    assert sched._tasks["lr"].last_run is not None


# ---------------------------------------------------------------------------
# Singleton / pre-registered tasks
# ---------------------------------------------------------------------------


def test_default_scheduler_has_preregistered_tasks():
    """The module-level scheduler singleton has the four default tasks."""
    from xcapitsff.core.scheduler import scheduler as default_scheduler

    expected = {"sla_check", "stale_leads_check", "data_quality_check", "event_cleanup"}
    assert expected.issubset(set(default_scheduler.list_tasks()))


def test_default_task_intervals():
    """Verify the default intervals for pre-registered tasks."""
    from xcapitsff.core.scheduler import scheduler as default_scheduler

    intervals = {t: default_scheduler._tasks[t].interval_seconds for t in default_scheduler.list_tasks()}
    assert intervals["sla_check"] == 15 * 60
    assert intervals["stale_leads_check"] == 6 * 3600
    assert intervals["data_quality_check"] == 24 * 3600
    assert intervals["event_cleanup"] == 12 * 3600
