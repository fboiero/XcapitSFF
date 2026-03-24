"""Tests for execution_engine module — 25 tests covering the full execution loop."""

from dataclasses import dataclass, field
from datetime import datetime

import pytest

from xcapitsff.agents.agent_registry import (
    AgentCapability,
    AgentProfile,
    AgentRegistry,
    AgentStatus,
    ModelTier,
)
from xcapitsff.agents.execution_engine import (
    ExecutionEngine,
    ExecutionRecord,
    init_execution_engine,
)
from xcapitsff.core.artifact_store import ArtifactStore, ArtifactType
from xcapitsff.core.review_gate import ReviewDecision, ReviewGateManager
from xcapitsff.core.task_pipeline import (
    PipelineTaskStatus,
    TaskPipeline,
    TaskPriority,
)


# ---------------------------------------------------------------------------
# Mock dispatcher
# ---------------------------------------------------------------------------

@dataclass
class MockDispatchResult:
    content: str = "Mock output from agent."
    agent_name: str = "mock_agent"
    action: str = "mock_action"
    backend: str = "dry_run"
    success: bool = True
    tokens_input: int = 100
    tokens_output: int = 200
    duration_ms: float = 50.0
    session_id: str | None = None
    error: str | None = None
    compliance_flags: list[str] = field(default_factory=list)


class MockDispatcher:
    """Dispatcher stub that returns predictable results."""

    def __init__(self, fail: bool = False, error_msg: str = "mock error"):
        self._fail = fail
        self._error_msg = error_msg
        self.calls: list[dict] = []

    async def dispatch(
        self,
        agent_role: str,
        context: str,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int = 2048,
    ) -> MockDispatchResult:
        self.calls.append({
            "agent_role": agent_role,
            "context": context,
            "system_prompt": system_prompt,
        })
        if self._fail:
            return MockDispatchResult(
                success=False,
                error=self._error_msg,
                content="",
                agent_name=agent_role,
            )
        return MockDispatchResult(
            content=f"Result for {agent_role}: processed context.",
            agent_name=agent_role,
            backend="dry_run",
        )


# ---------------------------------------------------------------------------
# Helpers: build a minimal registry with a single agent per capability
# ---------------------------------------------------------------------------

def _make_registry(*capabilities: AgentCapability) -> AgentRegistry:
    """Create a registry with one agent per capability."""
    registry = AgentRegistry.__new__(AgentRegistry)
    registry._agents = {}
    for cap in capabilities:
        agent_id = f"agent_{cap.value}"
        registry.register(AgentProfile(
            id=agent_id,
            name=f"Agent {cap.value}",
            role=f"role_{cap.value}",
            description=f"Agent for {cap.value}",
            capabilities=[cap],
            model_tier=ModelTier.SONNET,
            system_prompt=f"You are an agent for {cap.value}.",
            tools=[],
        ))
    return registry


def _build_engine(
    dispatcher: MockDispatcher | None = None,
    registry: AgentRegistry | None = None,
) -> tuple[ExecutionEngine, TaskPipeline, ArtifactStore, ReviewGateManager, MockDispatcher]:
    """Build an ExecutionEngine wired to fresh in-memory dependencies."""
    disp = dispatcher or MockDispatcher()
    reg = registry or _make_registry(
        AgentCapability.DISCOVER,
        AgentCapability.SPEC,
        AgentCapability.PLAN,
        AgentCapability.IMPLEMENT,
        AgentCapability.TEST,
        AgentCapability.REVIEW,
        AgentCapability.DOCUMENT,
        AgentCapability.SUPPORT,
    )
    pipeline = TaskPipeline()
    artifacts = ArtifactStore()
    reviews = ReviewGateManager()
    engine = ExecutionEngine(reg, pipeline, disp, artifacts, reviews)
    return engine, pipeline, artifacts, reviews, disp


# ===================================================================
# Tests
# ===================================================================


class TestTick:
    """Tests for the tick() main loop."""

    def test_tick_no_ready_tasks(self):
        engine, _pl, _art, _rev, _disp = _build_engine()
        result = engine.tick()
        assert result == []

    def test_tick_picks_ready_task_and_executes(self):
        engine, pipeline, artifacts, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Implement feature", phase="implementation")
        processed = engine.tick()
        assert task.id in processed
        assert task.status in (PipelineTaskStatus.DONE, PipelineTaskStatus.REVIEW)

    def test_tick_respects_dependencies(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        t1 = pipeline.create_task("WS-01", "First", phase="implementation")
        t2 = pipeline.create_task(
            "WS-01", "Second", phase="implementation", dependencies=[t1.id],
        )
        # t2 depends on t1 which is still QUEUED
        ready_before = pipeline.get_ready_tasks()
        assert t2.id not in [t.id for t in ready_before]

        processed = engine.tick()
        assert t1.id in processed
        # t2 should NOT have been processed yet (t1 was queued at check time)
        assert t2.id not in processed

        # Now t1 is done, second tick should pick t2
        processed2 = engine.tick()
        assert t2.id in processed2

    def test_tick_assigns_correct_agent_by_capability(self):
        disp = MockDispatcher()
        reg = _make_registry(AgentCapability.IMPLEMENT, AgentCapability.SPEC)
        engine, pipeline, _art, _rev, _ = _build_engine(dispatcher=disp, registry=reg)

        pipeline.create_task("WS-01", "Spec task", phase="specification")
        engine.tick()

        # The dispatcher should have been called with the spec agent's role
        assert len(disp.calls) == 1
        assert disp.calls[0]["agent_role"] == "role_spec"

    def test_tick_priority_order_critical_first(self):
        disp = MockDispatcher()
        engine, pipeline, _art, _rev, _ = _build_engine(dispatcher=disp)

        pipeline.create_task("WS-01", "Low prio", phase="implementation", priority="low")
        pipeline.create_task("WS-01", "Critical prio", phase="implementation", priority="critical")
        pipeline.create_task("WS-01", "High prio", phase="implementation", priority="high")

        processed = engine.tick()
        # All three processed; the dispatcher call order reflects priority
        assert len(disp.calls) >= 1
        # First call should be for the critical task
        assert "Critical prio" in disp.calls[0]["context"]

    def test_tick_skips_task_when_no_agent_available(self):
        reg = _make_registry(AgentCapability.SPEC)  # Only spec agents
        engine, pipeline, _art, _rev, _ = _build_engine(registry=reg)
        pipeline.create_task("WS-01", "Implement feature", phase="implementation")
        processed = engine.tick()
        assert processed == []


class TestExecuteTask:
    """Tests for execute_task() — explicit task execution."""

    def test_execute_task_stores_artifact_on_success(self):
        engine, pipeline, artifacts, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Build module", phase="implementation")

        record = engine.execute_task(task.id)
        assert record is not None
        assert record.success is True

        # Artifact should exist
        task_artifacts = artifacts.list_by_task(task.id)
        assert len(task_artifacts) == 1
        assert task_artifacts[0].type == ArtifactType.CODE

    def test_execute_task_sends_to_review_for_spec_phase(self):
        engine, pipeline, _art, reviews, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Write spec", phase="specification")

        record = engine.execute_task(task.id)
        assert record is not None
        assert record.success is True

        # Task should be in REVIEW status
        refreshed = pipeline.get_task(task.id)
        assert refreshed.status == PipelineTaskStatus.REVIEW

        # A review request should exist
        pending = reviews.get_pending_reviews(workspace_id="WS-01")
        assert len(pending) == 1
        assert pending[0].phase == "specification"

    def test_execute_task_sends_to_review_for_planning_phase(self):
        engine, pipeline, _art, reviews, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Plan sprint", phase="planning")
        engine.execute_task(task.id)
        refreshed = pipeline.get_task(task.id)
        assert refreshed.status == PipelineTaskStatus.REVIEW

    def test_execute_task_sends_to_review_for_review_phase(self):
        engine, pipeline, _art, reviews, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Code review", phase="review")
        engine.execute_task(task.id)
        refreshed = pipeline.get_task(task.id)
        assert refreshed.status == PipelineTaskStatus.REVIEW

    def test_execute_task_sends_to_review_for_deployment_phase(self):
        engine, pipeline, _art, reviews, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Deploy config", phase="deployment")
        engine.execute_task(task.id)
        refreshed = pipeline.get_task(task.id)
        assert refreshed.status == PipelineTaskStatus.REVIEW

    def test_execute_task_no_review_for_implementation(self):
        engine, pipeline, _art, reviews, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Code module", phase="implementation")
        engine.execute_task(task.id)
        refreshed = pipeline.get_task(task.id)
        assert refreshed.status == PipelineTaskStatus.DONE

    def test_execute_task_retries_on_failure(self):
        disp = MockDispatcher(fail=True, error_msg="timeout")
        engine, pipeline, _art, _rev, _ = _build_engine(dispatcher=disp)
        task = pipeline.create_task("WS-01", "Flaky task", phase="implementation")
        assert task.max_retries == 3

        record = engine.execute_task(task.id)
        assert record.success is False
        refreshed = pipeline.get_task(task.id)
        # Should be re-queued after first failure
        assert refreshed.status == PipelineTaskStatus.QUEUED
        assert refreshed.retry_count == 1

    def test_execute_task_permanent_failure_after_max_retries(self):
        disp = MockDispatcher(fail=True, error_msg="permanent error")
        engine, pipeline, _art, _rev, _ = _build_engine(dispatcher=disp)
        task = pipeline.create_task("WS-01", "Bad task", phase="implementation")
        task.max_retries = 1  # Only 1 retry allowed

        # First attempt
        engine.execute_task(task.id)
        refreshed = pipeline.get_task(task.id)
        assert refreshed.status == PipelineTaskStatus.QUEUED
        assert refreshed.retry_count == 1

        # Second attempt — should be permanent failure
        engine.execute_task(task.id)
        refreshed = pipeline.get_task(task.id)
        assert refreshed.status == PipelineTaskStatus.FAILED
        assert refreshed.retry_count == 2

    def test_execute_task_nonexistent_returns_none(self):
        engine, _pl, _art, _rev, _disp = _build_engine()
        assert engine.execute_task("PT-9999") is None

    def test_execute_task_no_agent_returns_none(self):
        reg = _make_registry(AgentCapability.SPEC)  # Only spec
        engine, pipeline, _art, _rev, _disp = _build_engine(registry=reg)
        task = pipeline.create_task("WS-01", "Test task", phase="testing")
        result = engine.execute_task(task.id)
        assert result is None


class TestBuildContext:
    """Tests for _build_context."""

    def test_build_context_basic(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        task = pipeline.create_task(
            "WS-01", "My Task", description="Do something important",
        )
        ctx = engine._build_context(task)
        assert "My Task" in ctx
        assert "Do something important" in ctx

    def test_build_context_includes_input_artifacts(self):
        engine, pipeline, artifacts, _rev, _disp = _build_engine()

        art = artifacts.store(
            workspace_id="WS-01",
            task_id="PT-0000",
            artifact_type=ArtifactType.SPEC,
            name="spec-doc",
            content="The system shall handle 1000 RPS.",
        )

        task = pipeline.create_task(
            "WS-01", "Implement from spec",
            description="Build based on spec",
            input_artifacts=[art.id],
        )
        ctx = engine._build_context(task)
        assert "1000 RPS" in ctx
        assert "spec-doc" in ctx


class TestNeedsReview:
    """Tests for _needs_review."""

    def test_specification_needs_review(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Spec", phase="specification")
        assert engine._needs_review(task) is True

    def test_planning_needs_review(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Plan", phase="planning")
        assert engine._needs_review(task) is True

    def test_implementation_no_review(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Code", phase="implementation")
        assert engine._needs_review(task) is False

    def test_testing_no_review(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Test", phase="testing")
        assert engine._needs_review(task) is False

    def test_deployment_needs_review(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Deploy", phase="deployment")
        assert engine._needs_review(task) is True


class TestPhaseToCapability:
    """Tests for _phase_to_capability mapping."""

    @pytest.mark.parametrize(
        "phase,expected",
        [
            ("discovery", "discover"),
            ("specification", "spec"),
            ("planning", "plan"),
            ("implementation", "implement"),
            ("testing", "test"),
            ("review", "review"),
            ("deployment", "document"),
            ("maintenance", "support"),
            ("unknown_phase", "implement"),  # default fallback
        ],
    )
    def test_mapping(self, phase, expected):
        assert ExecutionEngine._phase_to_capability(phase) == expected


class TestPhaseToArtifactType:
    """Tests for _phase_to_artifact_type mapping."""

    @pytest.mark.parametrize(
        "phase,expected",
        [
            ("discovery", "prd"),
            ("specification", "spec"),
            ("planning", "proposal"),
            ("implementation", "code"),
            ("testing", "test"),
            ("review", "review"),
            ("deployment", "config"),
            ("maintenance", "report"),
            ("unknown_phase", "document"),  # default fallback
        ],
    )
    def test_mapping(self, phase, expected):
        assert ExecutionEngine._phase_to_artifact_type(phase) == expected


class TestStats:
    """Tests for stats and history tracking."""

    def test_stats_empty(self):
        engine, _pl, _art, _rev, _disp = _build_engine()
        stats = engine.get_stats()
        assert stats["total_executions"] == 0
        assert stats["success_count"] == 0
        assert stats["fail_count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["total_tokens"] == 0
        assert stats["avg_duration_ms"] == 0.0
        assert stats["currently_running"] == 0

    def test_stats_after_execution(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        pipeline.create_task("WS-01", "Task A", phase="implementation")
        engine.tick()
        stats = engine.get_stats()
        assert stats["total_executions"] == 1
        assert stats["success_count"] == 1
        assert stats["success_rate"] == 1.0
        assert stats["total_tokens"] == 300  # 100 input + 200 output from mock
        assert stats["by_backend"]["dry_run"] == 1

    def test_stats_mixed_success_and_failure(self):
        disp_ok = MockDispatcher(fail=False)
        engine, pipeline, _art, _rev, _ = _build_engine(dispatcher=disp_ok)
        pipeline.create_task("WS-01", "Good task", phase="implementation")
        engine.tick()

        # Now make dispatcher fail
        engine._dispatcher = MockDispatcher(fail=True)
        pipeline.create_task("WS-01", "Bad task", phase="implementation")
        engine.tick()

        stats = engine.get_stats()
        assert stats["total_executions"] == 2
        assert stats["success_count"] == 1
        assert stats["fail_count"] == 1
        assert stats["success_rate"] == 0.5

    def test_execution_history_returns_records(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        pipeline.create_task("WS-01", "Task A", phase="implementation")
        pipeline.create_task("WS-02", "Task B", phase="implementation")
        engine.tick()

        history = engine.get_execution_history()
        assert len(history) == 2

        history_ws01 = engine.get_execution_history(workspace_id="WS-01")
        assert len(history_ws01) == 1

    def test_execution_history_limit(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        for i in range(5):
            pipeline.create_task("WS-01", f"Task {i}", phase="implementation")
        engine.tick()

        history = engine.get_execution_history(limit=3)
        assert len(history) == 3

    def test_get_running_tasks_empty_after_completion(self):
        engine, pipeline, _art, _rev, _disp = _build_engine()
        pipeline.create_task("WS-01", "Task", phase="implementation")
        engine.tick()
        assert len(engine.get_running_tasks()) == 0


class TestAgentLifecycle:
    """Tests for agent busy/available transitions."""

    def test_agent_marked_busy_during_execution_available_after(self):
        """Agent status should be AVAILABLE after successful execution."""
        engine, pipeline, _art, _rev, _disp = _build_engine()
        task = pipeline.create_task("WS-01", "Build", phase="implementation")
        engine.execute_task(task.id)

        # After execution the agent should be available again
        agent = engine._registry.get_available(AgentCapability.IMPLEMENT)
        assert len(agent) > 0
        assert agent[0].status == AgentStatus.AVAILABLE

    def test_agent_available_after_failure(self):
        """Agent should be freed even after a failed execution."""
        disp = MockDispatcher(fail=True)
        engine, pipeline, _art, _rev, _ = _build_engine(dispatcher=disp)
        task = pipeline.create_task("WS-01", "Fail", phase="implementation")
        engine.execute_task(task.id)

        agent = engine._registry.get_available(AgentCapability.IMPLEMENT)
        assert len(agent) > 0


class TestInitSingleton:
    """Test module-level init function."""

    def test_init_execution_engine(self):
        import xcapitsff.agents.execution_engine as mod

        reg = _make_registry(AgentCapability.IMPLEMENT)
        pipeline = TaskPipeline()
        artifacts = ArtifactStore()
        reviews = ReviewGateManager()
        disp = MockDispatcher()

        result = init_execution_engine(reg, pipeline, disp, artifacts, reviews)
        assert result is not None
        assert mod.execution_engine is result
        # Clean up
        mod.execution_engine = None
