"""Tests for the visual workflow builder engine."""

from __future__ import annotations

import pytest

from xcapitsff.core.workflows import (
    ActionType,
    StepType,
    TriggerType,
    Workflow,
    WorkflowEngine,
    WorkflowExecution,
    WorkflowStep,
    WORKFLOW_TEMPLATES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine() -> WorkflowEngine:
    return WorkflowEngine()


def _linear_steps() -> list[WorkflowStep]:
    """A -> B -> C linear chain."""
    return [
        WorkflowStep(
            step_id="a",
            type=StepType.ACTION,
            action_type=ActionType.SEND_EMAIL,
            config={"template": "hello"},
            next_steps=["b"],
        ),
        WorkflowStep(
            step_id="b",
            type=StepType.ACTION,
            action_type=ActionType.ADD_TAG,
            config={"tag": "welcomed"},
            next_steps=["c"],
        ),
        WorkflowStep(
            step_id="c",
            type=StepType.ACTION,
            action_type=ActionType.NOTIFY,
            config={"target": "team"},
        ),
    ]


def _condition_steps() -> list[WorkflowStep]:
    """Condition that branches on lead.score >= 50."""
    return [
        WorkflowStep(
            step_id="check",
            type=StepType.CONDITION,
            action_type=ActionType.CONDITION,
            config={"field": "lead.score", "operator": "gte", "value": 50},
            condition_true_step="high",
            condition_false_step="low",
        ),
        WorkflowStep(
            step_id="high",
            type=StepType.ACTION,
            action_type=ActionType.SEND_OUTREACH,
            config={"template": "vip"},
        ),
        WorkflowStep(
            step_id="low",
            type=StepType.ACTION,
            action_type=ActionType.ADD_TAG,
            config={"tag": "nurture"},
        ),
    ]


# ---------------------------------------------------------------------------
# 1. Create workflow with steps
# ---------------------------------------------------------------------------

class TestCreateWorkflow:
    def test_create_basic_workflow(self):
        eng = _engine()
        wf = eng.create_workflow(
            name="Test WF",
            tenant_id="t1",
            trigger=TriggerType.MANUAL,
            steps=_linear_steps(),
        )
        assert isinstance(wf, Workflow)
        assert wf.name == "Test WF"
        assert wf.tenant_id == "t1"
        assert wf.trigger == TriggerType.MANUAL
        assert len(wf.steps) == 3
        assert wf.is_active is True

    def test_create_workflow_with_trigger_config(self):
        eng = _engine()
        wf = eng.create_workflow(
            name="Scheduled WF",
            tenant_id="t1",
            trigger=TriggerType.SCHEDULE,
            steps=[],
            trigger_config={"cron": "0 9 * * 1"},
        )
        assert wf.trigger_config == {"cron": "0 9 * * 1"}

    def test_workflow_has_uuid(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, [])
        assert len(wf.workflow_id) == 36  # UUID format

    def test_workflow_retrievable_after_creation(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, _linear_steps())
        fetched = eng.get_workflow(wf.workflow_id)
        assert fetched is not None
        assert fetched.workflow_id == wf.workflow_id


# ---------------------------------------------------------------------------
# 2. Execute linear workflow
# ---------------------------------------------------------------------------

class TestLinearExecution:
    def test_linear_execution_completes(self):
        eng = _engine()
        wf = eng.create_workflow("linear", "t1", TriggerType.MANUAL, _linear_steps())
        ex = eng.execute_workflow(wf.workflow_id)
        assert ex.status == "completed"

    def test_linear_execution_records_all_steps(self):
        eng = _engine()
        wf = eng.create_workflow("linear", "t1", TriggerType.MANUAL, _linear_steps())
        ex = eng.execute_workflow(wf.workflow_id)
        assert ex.steps_executed == ["a", "b", "c"]

    def test_execution_has_completed_at(self):
        eng = _engine()
        wf = eng.create_workflow("linear", "t1", TriggerType.MANUAL, _linear_steps())
        ex = eng.execute_workflow(wf.workflow_id)
        assert ex.completed_at is not None

    def test_empty_workflow_completes_immediately(self):
        eng = _engine()
        wf = eng.create_workflow("empty", "t1", TriggerType.MANUAL, [])
        ex = eng.execute_workflow(wf.workflow_id)
        assert ex.status == "completed"
        assert ex.steps_executed == []


# ---------------------------------------------------------------------------
# 3. Execute workflow with condition branches
# ---------------------------------------------------------------------------

class TestConditionExecution:
    def test_condition_true_branch(self):
        eng = _engine()
        wf = eng.create_workflow("cond", "t1", TriggerType.MANUAL, _condition_steps())
        ex = eng.execute_workflow(wf.workflow_id, {"lead": {"score": 80}})
        assert "check" in ex.steps_executed
        assert "high" in ex.steps_executed
        assert "low" not in ex.steps_executed

    def test_condition_false_branch(self):
        eng = _engine()
        wf = eng.create_workflow("cond", "t1", TriggerType.MANUAL, _condition_steps())
        ex = eng.execute_workflow(wf.workflow_id, {"lead": {"score": 20}})
        assert "check" in ex.steps_executed
        assert "low" in ex.steps_executed
        assert "high" not in ex.steps_executed


# ---------------------------------------------------------------------------
# 4. Delay step handling
# ---------------------------------------------------------------------------

class TestDelayStep:
    def test_delay_step_recorded_and_continues(self):
        steps = [
            WorkflowStep(
                step_id="wait",
                type=StepType.DELAY,
                config={"duration_seconds": 3600},
                next_steps=["after_wait"],
            ),
            WorkflowStep(
                step_id="after_wait",
                type=StepType.ACTION,
                action_type=ActionType.NOTIFY,
                config={"target": "team"},
            ),
        ]
        eng = _engine()
        wf = eng.create_workflow("delay", "t1", TriggerType.MANUAL, steps)
        ex = eng.execute_workflow(wf.workflow_id)
        assert "wait" in ex.steps_executed
        assert "after_wait" in ex.steps_executed
        assert ex.status == "completed"


# ---------------------------------------------------------------------------
# 5. Pre-built templates
# ---------------------------------------------------------------------------

class TestTemplates:
    def test_new_lead_welcome_template_exists(self):
        assert "new_lead_welcome" in WORKFLOW_TEMPLATES

    def test_ticket_escalation_template_exists(self):
        assert "ticket_escalation" in WORKFLOW_TEMPLATES

    def test_deal_won_template_exists(self):
        assert "deal_won" in WORKFLOW_TEMPLATES

    def test_templates_have_required_keys(self):
        for tid, tpl in WORKFLOW_TEMPLATES.items():
            assert "name" in tpl, f"Template {tid} missing 'name'"
            assert "trigger" in tpl, f"Template {tid} missing 'trigger'"
            assert "steps" in tpl, f"Template {tid} missing 'steps'"
            assert isinstance(tpl["steps"], list)

    def test_template_steps_are_workflow_step_instances(self):
        for tpl in WORKFLOW_TEMPLATES.values():
            for step in tpl["steps"]:
                assert isinstance(step, WorkflowStep)


# ---------------------------------------------------------------------------
# 6. Toggle active/inactive
# ---------------------------------------------------------------------------

class TestToggle:
    def test_toggle_deactivates(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, [])
        assert wf.is_active is True
        result = eng.toggle_workflow(wf.workflow_id)
        assert result is False
        assert wf.is_active is False

    def test_toggle_reactivates(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, [])
        eng.toggle_workflow(wf.workflow_id)
        result = eng.toggle_workflow(wf.workflow_id)
        assert result is True
        assert wf.is_active is True

    def test_toggle_nonexistent_raises(self):
        eng = _engine()
        with pytest.raises(ValueError):
            eng.toggle_workflow("nonexistent-id")

    def test_execute_inactive_raises(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, _linear_steps())
        eng.toggle_workflow(wf.workflow_id)
        with pytest.raises(ValueError, match="not active"):
            eng.execute_workflow(wf.workflow_id)


# ---------------------------------------------------------------------------
# 7. Execution history tracking
# ---------------------------------------------------------------------------

class TestExecutionHistory:
    def test_execution_retrievable_by_id(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, _linear_steps())
        ex = eng.execute_workflow(wf.workflow_id)
        fetched = eng.get_execution(ex.execution_id)
        assert fetched is not None
        assert fetched.execution_id == ex.execution_id

    def test_executions_listed_for_workflow(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, _linear_steps())
        eng.execute_workflow(wf.workflow_id)
        eng.execute_workflow(wf.workflow_id)
        history = eng.get_executions(wf.workflow_id)
        assert len(history) == 2


# ---------------------------------------------------------------------------
# 8. Stats tracking
# ---------------------------------------------------------------------------

class TestStats:
    def test_stats_empty_engine(self):
        eng = _engine()
        stats = eng.get_stats()
        assert stats["total_workflows"] == 0
        assert stats["total_executions"] == 0

    def test_stats_after_executions(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, _linear_steps())
        eng.execute_workflow(wf.workflow_id)
        eng.execute_workflow(wf.workflow_id)
        stats = eng.get_stats()
        assert stats["total_workflows"] == 1
        assert stats["active_workflows"] == 1
        assert stats["total_executions"] == 2
        assert stats["completed_executions"] == 2

    def test_execution_count_on_workflow(self):
        eng = _engine()
        wf = eng.create_workflow("w", "t1", TriggerType.MANUAL, _linear_steps())
        eng.execute_workflow(wf.workflow_id)
        eng.execute_workflow(wf.workflow_id)
        eng.execute_workflow(wf.workflow_id)
        assert wf.execution_count == 3
        assert wf.last_executed is not None


# ---------------------------------------------------------------------------
# 9. Condition evaluation with different operators
# ---------------------------------------------------------------------------

class TestConditionEvaluation:
    def _step(self, field: str, operator: str, value: object) -> WorkflowStep:
        return WorkflowStep(
            step_id="cond",
            type=StepType.CONDITION,
            config={"field": field, "operator": operator, "value": value},
        )

    def test_eq_true(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "eq", 5), {"x": 5}) is True

    def test_eq_false(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "eq", 5), {"x": 3}) is False

    def test_neq(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "neq", 5), {"x": 3}) is True

    def test_gt(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "gt", 5), {"x": 10}) is True

    def test_gte_boundary(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "gte", 50), {"x": 50}) is True

    def test_lt(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "lt", 5), {"x": 2}) is True

    def test_lte(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "lte", 5), {"x": 5}) is True

    def test_contains_string(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "contains", "oo"), {"x": "foo"}) is True

    def test_not_contains(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "not_contains", "z"), {"x": "foo"}) is True

    def test_in_operator(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "in", ["a", "b"]), {"x": "a"}) is True

    def test_exists_true(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "exists", None), {"x": 42}) is True

    def test_exists_false(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "exists", None), {"y": 42}) is False

    def test_nested_field_resolution(self):
        eng = _engine()
        step = self._step("lead.score", "gte", 50)
        assert eng.evaluate_condition(step, {"lead": {"score": 75}}) is True

    def test_unknown_operator_returns_false(self):
        eng = _engine()
        assert eng.evaluate_condition(self._step("x", "banana", 5), {"x": 5}) is False


# ---------------------------------------------------------------------------
# 10. Parallel steps
# ---------------------------------------------------------------------------

class TestParallelStep:
    def test_parallel_fans_out(self):
        steps = [
            WorkflowStep(
                step_id="fork",
                type=StepType.PARALLEL,
                config={},
                next_steps=["branch_a", "branch_b"],
            ),
            WorkflowStep(
                step_id="branch_a",
                type=StepType.ACTION,
                action_type=ActionType.SEND_EMAIL,
                config={"template": "a"},
            ),
            WorkflowStep(
                step_id="branch_b",
                type=StepType.ACTION,
                action_type=ActionType.NOTIFY,
                config={"target": "ops"},
            ),
        ]
        eng = _engine()
        wf = eng.create_workflow("par", "t1", TriggerType.MANUAL, steps)
        ex = eng.execute_workflow(wf.workflow_id)
        assert "fork" in ex.steps_executed
        assert "branch_a" in ex.steps_executed
        assert "branch_b" in ex.steps_executed
        assert ex.status == "completed"


# ---------------------------------------------------------------------------
# 11. List / filter workflows
# ---------------------------------------------------------------------------

class TestListWorkflows:
    def test_list_all(self):
        eng = _engine()
        eng.create_workflow("a", "t1", TriggerType.MANUAL, [])
        eng.create_workflow("b", "t2", TriggerType.MANUAL, [])
        assert len(eng.list_workflows()) == 2

    def test_list_by_tenant(self):
        eng = _engine()
        eng.create_workflow("a", "t1", TriggerType.MANUAL, [])
        eng.create_workflow("b", "t2", TriggerType.MANUAL, [])
        assert len(eng.list_workflows(tenant_id="t1")) == 1

    def test_get_nonexistent_returns_none(self):
        eng = _engine()
        assert eng.get_workflow("does-not-exist") is None


# ---------------------------------------------------------------------------
# 12. Enums consistency
# ---------------------------------------------------------------------------

class TestEnums:
    def test_trigger_types(self):
        assert set(TriggerType) == {
            TriggerType.EVENT, TriggerType.SCHEDULE,
            TriggerType.MANUAL, TriggerType.WEBHOOK,
        }

    def test_step_types(self):
        assert set(StepType) == {
            StepType.ACTION, StepType.CONDITION,
            StepType.DELAY, StepType.PARALLEL,
        }

    def test_action_types_count(self):
        assert len(ActionType) == 13
