"""Execution Engine — core module connecting agent orchestration components.

Bridges the Agent Registry, Task Pipeline, Dispatcher, Artifact Store, and
Review Gate into a unified execution loop. Each tick picks ready tasks,
selects the best available agent, dispatches work, stores artifacts, and
routes results through review gates when required.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from xcapitsff.agents.agent_registry import (
    AgentCapability,
    AgentProfile,
    AgentRegistry,
    AgentStatus,
)
from xcapitsff.agents.dispatcher import AgentDispatcher
from xcapitsff.core.artifact_store import ArtifactFormat, ArtifactStore, ArtifactType
from xcapitsff.core.review_gate import ReviewGateManager
from xcapitsff.core.task_pipeline import (
    PipelineTask,
    PipelineTaskStatus,
    TaskPipeline,
    TaskPriority,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Priority ordering for sorting (lower value = higher priority)
# ---------------------------------------------------------------------------
_PRIORITY_ORDER = {
    TaskPriority.CRITICAL: 0,
    TaskPriority.HIGH: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.LOW: 3,
}

# ---------------------------------------------------------------------------
# Phase → capability mapping
# ---------------------------------------------------------------------------
_PHASE_CAPABILITY_MAP: dict[str, str] = {
    "discovery": AgentCapability.DISCOVER.value,
    "specification": AgentCapability.SPEC.value,
    "planning": AgentCapability.PLAN.value,
    "implementation": AgentCapability.IMPLEMENT.value,
    "testing": AgentCapability.TEST.value,
    "review": AgentCapability.REVIEW.value,
    "deployment": AgentCapability.DOCUMENT.value,
    "maintenance": AgentCapability.SUPPORT.value,
}

# ---------------------------------------------------------------------------
# Phase → artifact type mapping
# ---------------------------------------------------------------------------
_PHASE_ARTIFACT_MAP: dict[str, str] = {
    "discovery": ArtifactType.PRD.value,
    "specification": ArtifactType.SPEC.value,
    "planning": ArtifactType.PROPOSAL.value,
    "implementation": ArtifactType.CODE.value,
    "testing": ArtifactType.TEST.value,
    "review": ArtifactType.REVIEW.value,
    "deployment": ArtifactType.CONFIG.value,
    "maintenance": ArtifactType.REPORT.value,
}

# Phases that require review before proceeding
_REVIEW_PHASES = {"specification", "planning", "review", "deployment"}


@dataclass
class ExecutionRecord:
    """Record of a single task execution attempt."""

    id: str
    task_id: str
    agent_id: str
    workspace_id: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    backend: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: float = 0
    attempt: int = 1
    error: str | None = None
    output_preview: str = ""


class ExecutionEngine:
    """Connects registry, pipeline, dispatcher, artifacts, and reviews."""

    def __init__(
        self,
        registry: AgentRegistry,
        pipeline: TaskPipeline,
        dispatcher: AgentDispatcher,
        artifacts: ArtifactStore,
        reviews: ReviewGateManager,
    ) -> None:
        self._registry = registry
        self._pipeline = pipeline
        self._dispatcher = dispatcher
        self._artifacts = artifacts
        self._reviews = reviews

        self._history: list[ExecutionRecord] = []
        self._running: dict[str, ExecutionRecord] = {}

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def tick(self) -> list[str]:
        """Run one iteration of the execution loop.

        Returns the list of task IDs that were processed.
        """
        ready = self._pipeline.get_ready_tasks()
        if not ready:
            return []

        # Sort by priority (CRITICAL first)
        ready.sort(key=lambda t: _PRIORITY_ORDER.get(t.priority, 99))

        processed: list[str] = []

        for task in ready:
            # Determine the required capability
            cap_str = self._phase_to_capability(task.phase)
            if task.capability_required:
                cap_str = task.capability_required

            # Find an available agent
            try:
                capability = AgentCapability(cap_str)
            except ValueError:
                logger.warning(
                    "Unknown capability '%s' for task %s, skipping",
                    cap_str,
                    task.id,
                )
                continue

            agent = self._registry.select_best_agent(capability)
            if agent is None:
                logger.debug(
                    "No available agent for capability '%s', skipping task %s",
                    cap_str,
                    task.id,
                )
                continue

            # Assign, start, execute
            self._pipeline.assign_task(task.id, agent.id)
            self._pipeline.start_task(task.id)
            self._registry.mark_busy(agent.id, task.id)

            record = self._execute(task, agent)

            processed.append(task.id)

        return processed

    # ------------------------------------------------------------------
    # Public: execute a specific task
    # ------------------------------------------------------------------

    def execute_task(self, task_id: str) -> ExecutionRecord | None:
        """Execute a specific task by ID, regardless of queue position."""
        task = self._pipeline.get_task(task_id)
        if task is None:
            return None

        # Determine capability
        cap_str = self._phase_to_capability(task.phase)
        if task.capability_required:
            cap_str = task.capability_required

        try:
            capability = AgentCapability(cap_str)
        except ValueError:
            return None

        agent = self._registry.select_best_agent(capability)
        if agent is None:
            return None

        self._pipeline.assign_task(task.id, agent.id)
        self._pipeline.start_task(task.id)
        self._registry.mark_busy(agent.id, task.id)

        return self._execute(task, agent)

    # ------------------------------------------------------------------
    # Internal execution
    # ------------------------------------------------------------------

    def _execute(self, task: PipelineTask, agent: AgentProfile) -> ExecutionRecord:
        """Run a task via the dispatcher and handle the result."""
        record = ExecutionRecord(
            id=str(uuid.uuid4()),
            task_id=task.id,
            agent_id=agent.id,
            workspace_id=task.workspace_id,
            started_at=datetime.now(tz=None),
            attempt=task.retry_count + 1,
        )
        self._running[task.id] = record

        context = self._build_context(task)

        try:
            # Dispatch — the dispatcher.dispatch() is async but in dry-run
            # mode returns immediately.  We run it through asyncio so the
            # engine itself stays synchronous (simplifies testing).
            loop: asyncio.AbstractEventLoop | None = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Already inside an event loop — create a task on it.
                # This branch is typically hit in production (FastAPI).
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(
                        asyncio.run,
                        self._dispatcher.dispatch(
                            agent_role=agent.role,
                            context=context,
                            system_prompt=agent.system_prompt,
                        ),
                    ).result()
            else:
                result = asyncio.run(
                    self._dispatcher.dispatch(
                        agent_role=agent.role,
                        context=context,
                        system_prompt=agent.system_prompt,
                    )
                )

            record.completed_at = datetime.now(tz=None)
            record.backend = result.backend
            record.tokens_input = result.tokens_input
            record.tokens_output = result.tokens_output
            record.duration_ms = result.duration_ms
            record.success = result.success
            record.output_preview = (result.content or "")[:200]

            if result.success:
                self._handle_success(task, agent, record, result.content)
            else:
                record.error = result.error or "dispatch returned success=False"
                self._handle_failure(task, agent, record)

        except Exception as exc:
            record.completed_at = datetime.now(tz=None)
            record.success = False
            record.error = str(exc)
            self._handle_failure(task, agent, record)

        # Bookkeeping
        self._running.pop(task.id, None)
        self._history.append(record)

        # Record agent metrics
        duration_seconds = record.duration_ms / 1000 if record.duration_ms else 0
        total_tokens = record.tokens_input + record.tokens_output
        self._registry.record_completion(agent.id, duration_seconds, total_tokens)

        return record

    def _handle_success(
        self,
        task: PipelineTask,
        agent: AgentProfile,
        record: ExecutionRecord,
        content: str,
    ) -> None:
        """Store artifact, complete task, free agent, maybe send to review."""
        # Determine artifact type from phase
        art_type_str = self._phase_to_artifact_type(task.phase)
        try:
            art_type = ArtifactType(art_type_str)
        except ValueError:
            art_type = ArtifactType.DOCUMENT

        artifact = self._artifacts.store(
            workspace_id=task.workspace_id,
            task_id=task.id,
            artifact_type=art_type,
            name=f"{task.phase}-{task.id}",
            content=content,
            format=ArtifactFormat.MARKDOWN,
            created_by_agent=agent.id,
        )

        total_tokens = record.tokens_input + record.tokens_output
        self._pipeline.complete_task(
            task.id,
            output_artifact_id=artifact.id,
            actual_tokens=total_tokens,
        )
        self._registry.mark_available(agent.id)

        # Check if this phase needs review
        if self._needs_review(task):
            self._pipeline.send_to_review(task.id)
            self._reviews.request_review(
                workspace_id=task.workspace_id,
                task_id=task.id,
                phase=task.phase,
                artifact_ids=[artifact.id],
                priority=task.priority.value,
            )
            logger.info("Task %s sent to review (phase=%s)", task.id, task.phase)

    def _handle_failure(
        self,
        task: PipelineTask,
        agent: AgentProfile,
        record: ExecutionRecord,
    ) -> None:
        """Handle a failed execution — retry or permanent failure."""
        self._registry.mark_available(agent.id)
        error_msg = record.error or "unknown error"

        if self._pipeline.can_retry(task.id):
            self._pipeline.fail_task(task.id, error_msg)
            # Re-queue for retry
            task_obj = self._pipeline.get_task(task.id)
            if task_obj:
                task_obj.status = PipelineTaskStatus.QUEUED
            logger.info(
                "Task %s failed (attempt %d), re-queued for retry",
                task.id,
                record.attempt,
            )
        else:
            self._pipeline.fail_task(task.id, error_msg)
            logger.warning(
                "Task %s permanently failed after %d attempts: %s",
                task.id,
                record.attempt,
                error_msg,
            )

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def _build_context(self, task: PipelineTask) -> str:
        """Build the full context string for the dispatcher."""
        parts: list[str] = []
        parts.append(f"Task: {task.title}")

        if task.description:
            parts.append(f"\nDescription:\n{task.description}")

        # Append content from input artifacts
        for art_id in task.input_artifacts:
            artifact = self._artifacts.get(art_id)
            if artifact:
                parts.append(f"\n--- Input Artifact: {artifact.name} ---")
                parts.append(artifact.content)

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _needs_review(task: PipelineTask) -> bool:
        """Return True if the task's phase requires review."""
        return task.phase in _REVIEW_PHASES

    @staticmethod
    def _phase_to_capability(phase: str) -> str:
        """Map a pipeline phase to an AgentCapability value."""
        return _PHASE_CAPABILITY_MAP.get(phase, AgentCapability.IMPLEMENT.value)

    @staticmethod
    def _phase_to_artifact_type(phase: str) -> str:
        """Map a pipeline phase to an ArtifactType value."""
        return _PHASE_ARTIFACT_MAP.get(phase, ArtifactType.DOCUMENT.value)

    # ------------------------------------------------------------------
    # Stats & history
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return aggregate execution statistics."""
        total = len(self._history)
        successes = sum(1 for r in self._history if r.success)
        failures = total - successes
        total_tokens = sum(r.tokens_input + r.tokens_output for r in self._history)
        total_duration = sum(r.duration_ms for r in self._history)

        by_backend: dict[str, int] = {}
        for r in self._history:
            backend = r.backend or "unknown"
            by_backend[backend] = by_backend.get(backend, 0) + 1

        return {
            "total_executions": total,
            "success_count": successes,
            "fail_count": failures,
            "success_rate": (successes / total) if total > 0 else 0.0,
            "total_tokens": total_tokens,
            "avg_duration_ms": (total_duration / total) if total > 0 else 0.0,
            "by_backend": by_backend,
            "currently_running": len(self._running),
        }

    def get_execution_history(
        self,
        workspace_id: str | None = None,
        limit: int = 50,
    ) -> list[ExecutionRecord]:
        """Return recent execution records, optionally filtered by workspace."""
        records = self._history
        if workspace_id is not None:
            records = [r for r in records if r.workspace_id == workspace_id]
        return records[-limit:]

    def get_running_tasks(self) -> dict[str, ExecutionRecord]:
        """Return currently running task execution records."""
        return dict(self._running)


# ---------------------------------------------------------------------------
# Module-level singleton — lazy initialization
# ---------------------------------------------------------------------------

execution_engine: ExecutionEngine | None = None


def init_execution_engine(
    registry: AgentRegistry,
    pipeline: TaskPipeline,
    dispatcher: AgentDispatcher,
    artifacts: ArtifactStore,
    reviews: ReviewGateManager,
) -> ExecutionEngine:
    """Initialize and return the module-level execution engine singleton."""
    global execution_engine
    execution_engine = ExecutionEngine(registry, pipeline, dispatcher, artifacts, reviews)
    return execution_engine
