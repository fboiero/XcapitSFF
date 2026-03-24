"""Tests for task_pipeline module — 25+ tests covering task lifecycle."""

from datetime import datetime, timedelta

import pytest

from xcapitsff.core.task_pipeline import (
    PipelineTask,
    PipelineTaskStatus,
    TaskPipeline,
    TaskPriority,
)


@pytest.fixture
def pipeline():
    return TaskPipeline()


@pytest.fixture
def task(pipeline):
    return pipeline.create_task("WS-0001", "Build API endpoint")


# --- Creation ---


class TestTaskCreation:
    def test_create_task_basic(self, pipeline):
        t = pipeline.create_task("WS-0001", "My Task")
        assert t.id.startswith("PT-")
        assert t.workspace_id == "WS-0001"
        assert t.title == "My Task"
        assert t.status == PipelineTaskStatus.QUEUED
        assert t.priority == TaskPriority.MEDIUM

    def test_create_task_with_options(self, pipeline):
        t = pipeline.create_task(
            "WS-0001",
            "Task",
            description="desc",
            phase="testing",
            capability_required="code_review",
            dependencies=["PT-0001"],
            input_artifacts=["art-1"],
            priority="high",
            estimated_tokens=5000,
        )
        assert t.description == "desc"
        assert t.phase == "testing"
        assert t.capability_required == "code_review"
        assert t.dependencies == ["PT-0001"]
        assert t.input_artifacts == ["art-1"]
        assert t.priority == TaskPriority.HIGH
        assert t.estimated_tokens == 5000

    def test_create_task_defaults(self, task):
        assert task.agent_id is None
        assert task.output_artifact_id is None
        assert task.retry_count == 0
        assert task.max_retries == 3
        assert task.error is None
        assert task.result_content is None
        assert isinstance(task.created_at, datetime)
        assert task.started_at is None
        assert task.completed_at is None


# --- Status Transitions ---


class TestStatusTransitions:
    def test_assign_task(self, pipeline, task):
        result = pipeline.assign_task(task.id, "agent-1")
        assert result is not None
        assert result.status == PipelineTaskStatus.ASSIGNED
        assert result.agent_id == "agent-1"

    def test_start_task(self, pipeline, task):
        pipeline.assign_task(task.id, "agent-1")
        result = pipeline.start_task(task.id)
        assert result is not None
        assert result.status == PipelineTaskStatus.RUNNING
        assert result.started_at is not None

    def test_complete_task(self, pipeline, task):
        pipeline.assign_task(task.id, "agent-1")
        pipeline.start_task(task.id)
        result = pipeline.complete_task(task.id, output_artifact_id="art-out", actual_tokens=1200)
        assert result is not None
        assert result.status == PipelineTaskStatus.DONE
        assert result.completed_at is not None
        assert result.output_artifact_id == "art-out"
        assert result.actual_tokens == 1200

    def test_full_lifecycle(self, pipeline, task):
        pipeline.assign_task(task.id, "agent-1")
        pipeline.start_task(task.id)
        pipeline.complete_task(task.id)
        assert task.status == PipelineTaskStatus.DONE

    def test_fail_task(self, pipeline, task):
        pipeline.assign_task(task.id, "agent-1")
        pipeline.start_task(task.id)
        result = pipeline.fail_task(task.id, "Out of memory")
        assert result is not None
        assert result.status == PipelineTaskStatus.FAILED
        assert result.retry_count == 1
        assert result.error == "Out of memory"

    def test_cancel_task(self, pipeline, task):
        result = pipeline.cancel_task(task.id)
        assert result is not None
        assert result.status == PipelineTaskStatus.CANCELLED

    def test_nonexistent_task_operations(self, pipeline):
        assert pipeline.assign_task("PT-0000", "agent") is None
        assert pipeline.start_task("PT-0000") is None
        assert pipeline.complete_task("PT-0000") is None
        assert pipeline.fail_task("PT-0000", "err") is None
        assert pipeline.cancel_task("PT-0000") is None


# --- Dependency Resolution ---


class TestDependencies:
    def test_task_no_dependencies_is_ready(self, pipeline):
        t = pipeline.create_task("WS-0001", "Independent Task")
        ready = pipeline.get_ready_tasks()
        assert t.id in [r.id for r in ready]

    def test_task_with_unmet_dependency_not_ready(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task 1")
        t2 = pipeline.create_task("WS-0001", "Task 2", dependencies=[t1.id])
        ready = pipeline.get_ready_tasks()
        ready_ids = [r.id for r in ready]
        assert t1.id in ready_ids
        assert t2.id not in ready_ids

    def test_task_with_met_dependency_is_ready(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task 1")
        t2 = pipeline.create_task("WS-0001", "Task 2", dependencies=[t1.id])
        pipeline.assign_task(t1.id, "agent-1")
        pipeline.start_task(t1.id)
        pipeline.complete_task(t1.id)
        ready = pipeline.get_ready_tasks()
        ready_ids = [r.id for r in ready]
        assert t2.id in ready_ids

    def test_task_with_approved_dependency_is_ready(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task 1")
        t2 = pipeline.create_task("WS-0001", "Task 2", dependencies=[t1.id])
        # Set t1 to APPROVED status (via review flow)
        pipeline.send_to_review(t1.id)
        pipeline.approve_task(t1.id)  # This sets DONE
        ready = pipeline.get_ready_tasks()
        ready_ids = [r.id for r in ready]
        assert t2.id in ready_ids

    def test_ready_tasks_filtered_by_workspace(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task A")
        t2 = pipeline.create_task("WS-0002", "Task B")
        ready = pipeline.get_ready_tasks(workspace_id="WS-0001")
        ready_ids = [r.id for r in ready]
        assert t1.id in ready_ids
        assert t2.id not in ready_ids

    def test_dependency_graph(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task 1")
        t2 = pipeline.create_task("WS-0001", "Task 2", dependencies=[t1.id])
        t3 = pipeline.create_task("WS-0001", "Task 3", dependencies=[t1.id, t2.id])
        graph = pipeline.get_dependency_graph("WS-0001")
        assert graph[t1.id] == []
        assert graph[t2.id] == [t1.id]
        assert set(graph[t3.id]) == {t1.id, t2.id}


# --- Review Cycle ---


class TestReviewCycle:
    def test_send_to_review(self, pipeline, task):
        result = pipeline.send_to_review(task.id)
        assert result is not None
        assert result.status == PipelineTaskStatus.REVIEW

    def test_approve_task(self, pipeline, task):
        pipeline.send_to_review(task.id)
        result = pipeline.approve_task(task.id)
        assert result is not None
        assert result.status == PipelineTaskStatus.DONE

    def test_reject_task_requeues(self, pipeline, task):
        pipeline.send_to_review(task.id)
        result = pipeline.reject_task(task.id, "Needs more tests")
        assert result is not None
        assert result.status == PipelineTaskStatus.QUEUED
        assert result.error == "Needs more tests"

    def test_reject_nonexistent(self, pipeline):
        assert pipeline.reject_task("PT-0000", "feedback") is None
        assert pipeline.send_to_review("PT-0000") is None
        assert pipeline.approve_task("PT-0000") is None


# --- Retry Logic ---


class TestRetryLogic:
    def test_can_retry_initially(self, pipeline, task):
        assert pipeline.can_retry(task.id) is True

    def test_can_retry_after_failures(self, pipeline, task):
        for _ in range(3):
            pipeline.fail_task(task.id, "error")
        assert pipeline.can_retry(task.id) is False

    def test_can_retry_nonexistent(self, pipeline):
        assert pipeline.can_retry("PT-0000") is False


# --- Pipeline View ---


class TestPipelineView:
    def test_pipeline_view_grouped_by_status(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task 1")
        t2 = pipeline.create_task("WS-0001", "Task 2")
        pipeline.assign_task(t2.id, "agent-1")
        view = pipeline.get_pipeline_view("WS-0001")
        assert "queued" in view["counts"]
        assert "assigned" in view["counts"]
        assert view["counts"]["queued"] == 1
        assert view["counts"]["assigned"] == 1

    def test_pipeline_view_empty(self, pipeline):
        view = pipeline.get_pipeline_view("WS-9999")
        assert view["tasks"] == {}
        assert view["counts"] == {}


# --- Filter by Workspace/Status/Phase ---


class TestFiltering:
    def test_list_by_workspace(self, pipeline):
        pipeline.create_task("WS-0001", "Task A")
        pipeline.create_task("WS-0002", "Task B")
        result = pipeline.list_tasks(workspace_id="WS-0001")
        assert len(result) == 1

    def test_list_by_status(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task 1")
        t2 = pipeline.create_task("WS-0001", "Task 2")
        pipeline.assign_task(t1.id, "agent-1")
        result = pipeline.list_tasks(status=PipelineTaskStatus.ASSIGNED)
        assert len(result) == 1

    def test_list_by_phase(self, pipeline):
        pipeline.create_task("WS-0001", "Task A", phase="testing")
        pipeline.create_task("WS-0001", "Task B", phase="implementation")
        result = pipeline.list_tasks(phase="testing")
        assert len(result) == 1

    def test_get_tasks_for_phase(self, pipeline):
        pipeline.create_task("WS-0001", "Task A", phase="testing")
        pipeline.create_task("WS-0001", "Task B", phase="implementation")
        result = pipeline.get_tasks_for_phase("WS-0001", "testing")
        assert len(result) == 1
        assert result[0].phase == "testing"

    def test_get_task(self, pipeline, task):
        result = pipeline.get_task(task.id)
        assert result is task

    def test_get_task_nonexistent(self, pipeline):
        result = pipeline.get_task("PT-0000")
        assert result is None


# --- Stats ---


class TestStats:
    def test_stats_empty(self, pipeline):
        stats = pipeline.get_stats()
        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["avg_completion_seconds"] == 0.0

    def test_stats_with_tasks(self, pipeline):
        t1 = pipeline.create_task("WS-0001", "Task 1")
        pipeline.create_task("WS-0001", "Task 2")
        pipeline.assign_task(t1.id, "agent-1")
        stats = pipeline.get_stats()
        assert stats["total"] == 2
        assert stats["by_status"]["assigned"] == 1
        assert stats["by_status"]["queued"] == 1

    def test_stats_with_completion_time(self, pipeline):
        t = pipeline.create_task("WS-0001", "Task")
        pipeline.assign_task(t.id, "agent-1")
        pipeline.start_task(t.id)
        # Manually set started_at to ensure measurable delta
        t.started_at = datetime.now() - timedelta(seconds=10)
        pipeline.complete_task(t.id)
        stats = pipeline.get_stats()
        assert stats["avg_completion_seconds"] >= 9.0

    def test_stats_filtered_by_workspace(self, pipeline):
        pipeline.create_task("WS-0001", "Task A")
        pipeline.create_task("WS-0002", "Task B")
        stats = pipeline.get_stats(workspace_id="WS-0001")
        assert stats["total"] == 1
