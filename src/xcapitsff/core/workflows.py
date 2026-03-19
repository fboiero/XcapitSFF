"""Visual workflow builder engine -- no-code automation system."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TriggerType(str, Enum):
    """How a workflow is triggered."""
    EVENT = "event"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    WEBHOOK = "webhook"


class ActionType(str, Enum):
    """Atomic actions that a workflow step can perform."""
    SEND_EMAIL = "send_email"
    SEND_OUTREACH = "send_outreach"
    CREATE_TICKET = "create_ticket"
    UPDATE_LEAD = "update_lead"
    ASSIGN_AGENT = "assign_agent"
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    SET_FIELD = "set_field"
    NOTIFY = "notify"
    WAIT = "wait"
    CONDITION = "condition"
    CALL_WEBHOOK = "call_webhook"
    RUN_AGENT = "run_agent"


class StepType(str, Enum):
    """Semantic category of a workflow step."""
    ACTION = "action"
    CONDITION = "condition"
    DELAY = "delay"
    PARALLEL = "parallel"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WorkflowStep:
    step_id: str
    type: StepType
    action_type: ActionType | None = None
    config: dict[str, Any] = field(default_factory=dict)
    next_steps: list[str] = field(default_factory=list)
    condition_true_step: str | None = None
    condition_false_step: str | None = None


@dataclass
class Workflow:
    workflow_id: str
    name: str
    description: str
    tenant_id: str
    trigger: TriggerType
    trigger_config: dict[str, Any]
    steps: list[WorkflowStep]
    is_active: bool = True
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_count: int = 0
    last_executed: datetime | None = None


@dataclass
class WorkflowExecution:
    execution_id: str
    workflow_id: str
    trigger_data: dict[str, Any]
    status: str = "running"  # running | completed | failed | cancelled
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    steps_executed: list[str] = field(default_factory=list)
    current_step: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Condition evaluator helpers
# ---------------------------------------------------------------------------

_OPERATORS: dict[str, Any] = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "contains": lambda a, b: b in a if isinstance(a, (str, list)) else False,
    "not_contains": lambda a, b: b not in a if isinstance(a, (str, list)) else True,
    "in": lambda a, b: a in b if isinstance(b, (str, list)) else False,
    "exists": lambda a, _: a is not None,
}


def _resolve(context: dict[str, Any], key: str) -> Any:
    """Resolve a dotted key against a nested dict."""
    parts = key.split(".")
    cur: Any = context
    for p in parts:
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur


# ---------------------------------------------------------------------------
# Pre-built templates
# ---------------------------------------------------------------------------

def _build_templates() -> dict[str, dict[str, Any]]:
    """Return pre-built workflow template definitions."""
    templates: dict[str, dict[str, Any]] = {}

    # --- new_lead_welcome ---------------------------------------------------
    templates["new_lead_welcome"] = {
        "name": "New Lead Welcome",
        "description": "Welcome new leads: high-score leads get outreach + agent, others get nurtured.",
        "trigger": TriggerType.EVENT,
        "trigger_config": {"event_type": "LEAD_CREATED"},
        "steps": [
            WorkflowStep(
                step_id="check_score",
                type=StepType.CONDITION,
                action_type=ActionType.CONDITION,
                config={"field": "lead.score", "operator": "gte", "value": 50},
                condition_true_step="send_outreach",
                condition_false_step="add_nurture_tag",
            ),
            WorkflowStep(
                step_id="send_outreach",
                type=StepType.ACTION,
                action_type=ActionType.SEND_OUTREACH,
                config={"template": "welcome_high_score"},
                next_steps=["assign_agent"],
            ),
            WorkflowStep(
                step_id="assign_agent",
                type=StepType.ACTION,
                action_type=ActionType.ASSIGN_AGENT,
                config={"strategy": "round_robin"},
            ),
            WorkflowStep(
                step_id="add_nurture_tag",
                type=StepType.ACTION,
                action_type=ActionType.ADD_TAG,
                config={"tag": "nurture"},
            ),
        ],
    }

    # --- ticket_escalation --------------------------------------------------
    templates["ticket_escalation"] = {
        "name": "Ticket Escalation",
        "description": "Escalate tickets that breach SLA.",
        "trigger": TriggerType.EVENT,
        "trigger_config": {"event_type": "TICKET_SLA_BREACHED"},
        "steps": [
            WorkflowStep(
                step_id="notify_lead",
                type=StepType.ACTION,
                action_type=ActionType.NOTIFY,
                config={"target": "team_lead"},
                next_steps=["assign_senior"],
            ),
            WorkflowStep(
                step_id="assign_senior",
                type=StepType.ACTION,
                action_type=ActionType.ASSIGN_AGENT,
                config={"agent": "senior"},
                next_steps=["tag_escalated"],
            ),
            WorkflowStep(
                step_id="tag_escalated",
                type=StepType.ACTION,
                action_type=ActionType.ADD_TAG,
                config={"tag": "escalated"},
            ),
        ],
    }

    # --- deal_won -----------------------------------------------------------
    templates["deal_won"] = {
        "name": "Deal Won",
        "description": "Celebrate a won deal: congratulate, create onboarding ticket, notify success team.",
        "trigger": TriggerType.EVENT,
        "trigger_config": {"event_type": "LEAD_STAGE_CHANGED", "stage": "won"},
        "steps": [
            WorkflowStep(
                step_id="send_congrats",
                type=StepType.ACTION,
                action_type=ActionType.SEND_EMAIL,
                config={"template": "congrats"},
                next_steps=["create_onboarding"],
            ),
            WorkflowStep(
                step_id="create_onboarding",
                type=StepType.ACTION,
                action_type=ActionType.CREATE_TICKET,
                config={"type": "onboarding"},
                next_steps=["notify_success"],
            ),
            WorkflowStep(
                step_id="notify_success",
                type=StepType.ACTION,
                action_type=ActionType.NOTIFY,
                config={"target": "success_team"},
            ),
        ],
    }

    return templates


WORKFLOW_TEMPLATES: dict[str, dict[str, Any]] = _build_templates()


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """In-memory workflow execution engine."""

    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}
        self._executions: dict[str, WorkflowExecution] = {}

    # -- CRUD ----------------------------------------------------------------

    def create_workflow(
        self,
        name: str,
        tenant_id: str,
        trigger: TriggerType,
        steps: list[WorkflowStep],
        trigger_config: dict[str, Any] | None = None,
        description: str = "",
    ) -> Workflow:
        wf = Workflow(
            workflow_id=str(uuid.uuid4()),
            name=name,
            description=description,
            tenant_id=tenant_id,
            trigger=trigger,
            trigger_config=trigger_config or {},
            steps=steps,
        )
        self._workflows[wf.workflow_id] = wf
        return wf

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self, tenant_id: str | None = None) -> list[Workflow]:
        wfs = list(self._workflows.values())
        if tenant_id is not None:
            wfs = [w for w in wfs if w.tenant_id == tenant_id]
        return wfs

    def toggle_workflow(self, workflow_id: str) -> bool:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise ValueError(f"Workflow {workflow_id} not found")
        wf.is_active = not wf.is_active
        wf.updated_at = datetime.now(timezone.utc)
        return wf.is_active

    # -- Execution -----------------------------------------------------------

    def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise ValueError(f"Workflow {workflow_id} not found")
        if not wf.is_active:
            raise ValueError(f"Workflow {workflow_id} is not active")

        trigger_data = trigger_data or {}

        execution = WorkflowExecution(
            execution_id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            trigger_data=trigger_data,
        )

        steps_map: dict[str, WorkflowStep] = {s.step_id: s for s in wf.steps}

        # Determine the first step (first in the list)
        if not wf.steps:
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            self._executions[execution.execution_id] = execution
            self._record_execution(wf)
            return execution

        queue: list[str] = [wf.steps[0].step_id]

        try:
            while queue:
                step_id = queue.pop(0)
                step = steps_map.get(step_id)
                if step is None:
                    continue

                execution.current_step = step_id
                execution.steps_executed.append(step_id)

                if step.type == StepType.CONDITION:
                    result = self.evaluate_condition(step, trigger_data)
                    next_id = step.condition_true_step if result else step.condition_false_step
                    if next_id:
                        queue.append(next_id)

                elif step.type == StepType.DELAY:
                    # In a real system we'd schedule a resume.  Here we just
                    # record the delay and continue.
                    pass  # delay recorded in steps_executed
                    if step.next_steps:
                        queue.extend(step.next_steps)

                elif step.type == StepType.PARALLEL:
                    # Mark all next_steps as ready (add them all to the queue)
                    if step.next_steps:
                        queue.extend(step.next_steps)

                elif step.type == StepType.ACTION:
                    self._execute_action(step, trigger_data)
                    if step.next_steps:
                        queue.extend(step.next_steps)

            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
        except Exception as exc:
            execution.status = "failed"
            execution.error = str(exc)
            execution.completed_at = datetime.now(timezone.utc)

        self._executions[execution.execution_id] = execution
        self._record_execution(wf)
        return execution

    # -- Query executions ----------------------------------------------------

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        return self._executions.get(execution_id)

    def get_executions(self, workflow_id: str) -> list[WorkflowExecution]:
        return [e for e in self._executions.values() if e.workflow_id == workflow_id]

    # -- Condition evaluation ------------------------------------------------

    def evaluate_condition(self, step: WorkflowStep, context: dict[str, Any]) -> bool:
        """Evaluate a step's condition against *context*.

        The step config is expected to contain:
          - ``field``: dotted path into *context*
          - ``operator``: one of the keys in ``_OPERATORS``
          - ``value``: right-hand operand
        """
        cfg = step.config
        field_path: str = cfg.get("field", "")
        operator: str = cfg.get("operator", "eq")
        expected = cfg.get("value")

        actual = _resolve(context, field_path)
        op_fn = _OPERATORS.get(operator)
        if op_fn is None:
            return False
        try:
            return bool(op_fn(actual, expected))
        except (TypeError, ValueError):
            return False

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        total_workflows = len(self._workflows)
        active_workflows = sum(1 for w in self._workflows.values() if w.is_active)
        total_executions = len(self._executions)
        completed = sum(1 for e in self._executions.values() if e.status == "completed")
        failed = sum(1 for e in self._executions.values() if e.status == "failed")
        running = sum(1 for e in self._executions.values() if e.status == "running")
        cancelled = sum(1 for e in self._executions.values() if e.status == "cancelled")

        return {
            "total_workflows": total_workflows,
            "active_workflows": active_workflows,
            "inactive_workflows": total_workflows - active_workflows,
            "total_executions": total_executions,
            "completed_executions": completed,
            "failed_executions": failed,
            "running_executions": running,
            "cancelled_executions": cancelled,
        }

    # -- Internals -----------------------------------------------------------

    @staticmethod
    def _execute_action(step: WorkflowStep, context: dict[str, Any]) -> None:
        """Simulate action execution.

        In a production system each ``ActionType`` would dispatch to an
        adapter (email service, CRM, ticketing, etc.).  Here we simply
        record that the action was invoked.
        """
        # No-op -- side-effects would go here.

    @staticmethod
    def _record_execution(wf: Workflow) -> None:
        wf.execution_count += 1
        wf.last_executed = datetime.now(timezone.utc)
