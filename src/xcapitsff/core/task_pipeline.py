"""Task Pipeline — manages task lifecycle for the agent orchestration layer.

Provides task creation, dependency resolution, status transitions,
review cycles, and pipeline analytics.
"""

import logging
import random
import string
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PipelineTaskStatus(str, Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _generate_id(prefix: str) -> str:
    digits = "".join(random.choices(string.digits, k=4))
    return f"{prefix}-{digits}"


@dataclass
class PipelineTask:
    id: str
    workspace_id: str
    title: str
    description: str = ""
    phase: str = "implementation"
    agent_id: str | None = None
    capability_required: str | None = None
    dependencies: list[str] = field(default_factory=list)
    input_artifacts: list[str] = field(default_factory=list)
    output_artifact_id: str | None = None
    status: PipelineTaskStatus = PipelineTaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_tokens: int = 0
    actual_tokens: int = 0
    retry_count: int = 0
    max_retries: int = 3
    error: str | None = None
    result_content: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TaskPipeline:
    """Manages task lifecycle, dependencies, and pipeline analytics."""

    def __init__(self) -> None:
        self._tasks: dict[str, PipelineTask] = {}

    def create_task(
        self,
        workspace_id: str,
        title: str,
        description: str = "",
        phase: str = "implementation",
        capability_required: str | None = None,
        dependencies: list[str] | None = None,
        input_artifacts: list[str] | None = None,
        priority: str = "medium",
        estimated_tokens: int = 0,
    ) -> PipelineTask:
        task = PipelineTask(
            id=_generate_id("PT"),
            workspace_id=workspace_id,
            title=title,
            description=description,
            phase=phase,
            capability_required=capability_required,
            dependencies=dependencies or [],
            input_artifacts=input_artifacts or [],
            priority=TaskPriority(priority),
            estimated_tokens=estimated_tokens,
        )
        self._tasks[task.id] = task
        logger.info(f"Task created: {task.id} ({task.title})")
        return task

    def get_task(self, task_id: str) -> PipelineTask | None:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        workspace_id: str | None = None,
        status: PipelineTaskStatus | None = None,
        phase: str | None = None,
    ) -> list[PipelineTask]:
        result = list(self._tasks.values())
        if workspace_id is not None:
            result = [t for t in result if t.workspace_id == workspace_id]
        if status is not None:
            result = [t for t in result if t.status == status]
        if phase is not None:
            result = [t for t in result if t.phase == phase]
        return result

    def get_ready_tasks(self, workspace_id: str | None = None) -> list[PipelineTask]:
        """Return QUEUED tasks whose dependencies are all DONE or APPROVED."""
        tasks = self.list_tasks(workspace_id=workspace_id, status=PipelineTaskStatus.QUEUED)
        ready = []
        for task in tasks:
            if not task.dependencies:
                ready.append(task)
                continue
            all_met = True
            for dep_id in task.dependencies:
                dep = self._tasks.get(dep_id)
                if dep is None or dep.status not in (
                    PipelineTaskStatus.DONE,
                    PipelineTaskStatus.APPROVED,
                ):
                    all_met = False
                    break
            if all_met:
                ready.append(task)
        return ready

    def assign_task(self, task_id: str, agent_id: str) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.agent_id = agent_id
        task.status = PipelineTaskStatus.ASSIGNED
        return task

    def start_task(self, task_id: str) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = PipelineTaskStatus.RUNNING
        task.started_at = datetime.now()
        return task

    def complete_task(
        self,
        task_id: str,
        output_artifact_id: str | None = None,
        actual_tokens: int = 0,
    ) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = PipelineTaskStatus.DONE
        task.completed_at = datetime.now()
        if output_artifact_id is not None:
            task.output_artifact_id = output_artifact_id
        if actual_tokens:
            task.actual_tokens = actual_tokens
        return task

    def fail_task(self, task_id: str, error: str) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = PipelineTaskStatus.FAILED
        task.retry_count += 1
        task.error = error
        return task

    def cancel_task(self, task_id: str) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = PipelineTaskStatus.CANCELLED
        return task

    def send_to_review(self, task_id: str) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = PipelineTaskStatus.REVIEW
        return task

    def approve_task(self, task_id: str) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = PipelineTaskStatus.DONE
        return task

    def reject_task(self, task_id: str, feedback: str) -> PipelineTask | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = PipelineTaskStatus.QUEUED
        task.error = feedback
        return task

    def can_retry(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None:
            return False
        return task.retry_count < task.max_retries

    def get_tasks_for_phase(self, workspace_id: str, phase: str) -> list[PipelineTask]:
        return self.list_tasks(workspace_id=workspace_id, phase=phase)

    def get_pipeline_view(self, workspace_id: str) -> dict[str, Any]:
        tasks = self.list_tasks(workspace_id=workspace_id)
        grouped: dict[str, list[dict[str, Any]]] = {}
        counts: dict[str, int] = {}
        for task in tasks:
            status_key = task.status.value
            if status_key not in grouped:
                grouped[status_key] = []
                counts[status_key] = 0
            grouped[status_key].append({
                "id": task.id,
                "title": task.title,
                "priority": task.priority.value,
            })
            counts[status_key] += 1
        return {"tasks": grouped, "counts": counts}

    def get_dependency_graph(self, workspace_id: str) -> dict[str, list[str]]:
        tasks = self.list_tasks(workspace_id=workspace_id)
        graph: dict[str, list[str]] = {}
        for task in tasks:
            graph[task.id] = list(task.dependencies)
        return graph

    def get_stats(self, workspace_id: str | None = None) -> dict[str, Any]:
        tasks = self.list_tasks(workspace_id=workspace_id)
        total = len(tasks)
        by_status: dict[str, int] = {}
        completion_times: list[float] = []
        for task in tasks:
            by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
            if task.started_at and task.completed_at:
                delta = (task.completed_at - task.started_at).total_seconds()
                completion_times.append(delta)
        avg_completion = (
            sum(completion_times) / len(completion_times) if completion_times else 0.0
        )
        return {
            "total": total,
            "by_status": by_status,
            "avg_completion_seconds": avg_completion,
        }


# Module-level singleton
task_pipeline = TaskPipeline()
