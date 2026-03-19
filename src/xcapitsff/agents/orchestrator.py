"""Agent Orchestrator — reacts to business events and dispatches agent tasks.

The orchestrator listens to events from the EventBus and automatically
triggers the appropriate agent actions. This is the "brain" that connects
the event-driven architecture to the AI agent layer.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from xcapitsff.core.events import Event, EventBus, EventType

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentTask:
    task_id: str
    agent_name: str
    action: str
    params: dict
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def complete(self, result: str) -> None:
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now()

    def fail(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()


class AgentOrchestrator:
    """Orchestrates agent tasks based on business events.

    Event → Rule evaluation → Agent task creation → Execution → Result logging

    Rules define which events trigger which agent actions. Rules can be
    conditional (e.g., only trigger for high-priority tickets).
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.task_queue: list[AgentTask] = []
        self.task_history: list[AgentTask] = []
        self.rules: list[dict] = []
        self._task_counter = 0
        self._setup_default_rules()
        self._register_handlers()

    def _next_task_id(self) -> str:
        self._task_counter += 1
        return f"AT-{self._task_counter:04d}"

    def _setup_default_rules(self) -> None:
        """Define default event→agent rules."""
        self.rules = [
            {
                "event": EventType.LEAD_CREATED,
                "agent": "sales_qualifier",
                "action": "qualify_lead",
                "condition": lambda e: True,
                "description": "Auto-qualify new leads",
            },
            {
                "event": EventType.LEADS_IMPORTED,
                "agent": "sales_qualifier",
                "action": "batch_qualify",
                "condition": lambda e: e.data.get("count", 0) > 0,
                "description": "Batch qualify after import",
            },
            {
                "event": EventType.LEAD_QUALIFIED,
                "agent": "outreach_composer",
                "action": "draft_initial_outreach",
                "condition": lambda e: e.data.get("score", 0) >= 60,
                "description": "Auto-draft outreach for high-score qualified leads",
            },
            {
                "event": EventType.TICKET_CREATED,
                "agent": "ticket_router",
                "action": "classify_and_route",
                "condition": lambda e: True,
                "description": "Auto-classify and route new tickets",
            },
            {
                "event": EventType.TICKET_CREATED,
                "agent": "support_responder",
                "action": "draft_response",
                "condition": lambda e: e.data.get("priority") not in ("urgent",),
                "description": "Auto-draft response for non-urgent tickets",
            },
            {
                "event": EventType.TICKET_ESCALATED,
                "agent": "support_responder",
                "action": "escalation_response",
                "condition": lambda e: True,
                "description": "Handle escalated tickets with senior response",
            },
            {
                "event": EventType.TICKET_SLA_BREACHED,
                "agent": "support_responder",
                "action": "sla_breach_response",
                "condition": lambda e: True,
                "description": "Urgent response for SLA breaches",
            },
            {
                "event": EventType.TICKET_MESSAGE_ADDED,
                "agent": "support_responder",
                "action": "followup_response",
                "condition": lambda e: e.data.get("sender") == "customer",
                "description": "Auto-respond to customer messages",
            },
            {
                "event": EventType.LEAD_STAGE_CHANGED,
                "agent": "outreach_composer",
                "action": "stage_appropriate_outreach",
                "condition": lambda e: e.data.get("new_stage") in ("contacted", "meeting"),
                "description": "Draft follow-up for stage transitions",
            },
        ]

    def _register_handlers(self) -> None:
        """Subscribe to all events we have rules for."""
        event_types = set(rule["event"] for rule in self.rules)
        for event_type in event_types:
            self.event_bus.subscribe(event_type, self._handle_event)

    async def _handle_event(self, event: Event) -> None:
        """Process an event against all matching rules."""
        matching_rules = [
            rule for rule in self.rules
            if rule["event"] == event.type and rule["condition"](event)
        ]

        for rule in matching_rules:
            task = AgentTask(
                task_id=self._next_task_id(),
                agent_name=rule["agent"],
                action=rule["action"],
                params={"event": event.type.value, "data": event.data},
            )
            self.task_queue.append(task)
            logger.info(
                f"Task created: {task.task_id} → {task.agent_name}.{task.action} "
                f"(triggered by {event.type.value})"
            )

    async def process_queue(self) -> list[AgentTask]:
        """Process all pending tasks in the queue.

        In a real system, this would invoke the actual AI agents.
        For now, it marks tasks as completed and logs them.
        Returns the list of processed tasks.
        """
        processed = []
        while self.task_queue:
            task = self.task_queue.pop(0)
            task.status = TaskStatus.RUNNING
            logger.info(f"Processing task: {task.task_id} ({task.agent_name}.{task.action})")

            try:
                # In production, this would call the actual agent
                # For now, mark as completed
                task.complete(
                    f"Task {task.task_id} processed by {task.agent_name}"
                )
                processed.append(task)
            except Exception as e:
                task.fail(str(e))
                processed.append(task)
                logger.error(f"Task {task.task_id} failed: {e}")

            self.task_history.append(task)

        return processed

    def add_rule(
        self,
        event_type: EventType,
        agent: str,
        action: str,
        condition=None,
        description: str = "",
    ) -> None:
        """Add a custom event→agent rule."""
        rule = {
            "event": event_type,
            "agent": agent,
            "action": action,
            "condition": condition or (lambda e: True),
            "description": description,
        }
        self.rules.append(rule)
        self.event_bus.subscribe(event_type, self._handle_event)

    def get_pending_tasks(self) -> list[AgentTask]:
        return [t for t in self.task_queue if t.status == TaskStatus.PENDING]

    def get_task_history(self, limit: int = 50) -> list[AgentTask]:
        return self.task_history[-limit:]

    def get_stats(self) -> dict:
        completed = [t for t in self.task_history if t.status == TaskStatus.COMPLETED]
        failed = [t for t in self.task_history if t.status == TaskStatus.FAILED]

        by_agent: dict[str, int] = {}
        for task in self.task_history:
            by_agent[task.agent_name] = by_agent.get(task.agent_name, 0) + 1

        return {
            "total_tasks_processed": len(self.task_history),
            "pending": len(self.task_queue),
            "completed": len(completed),
            "failed": len(failed),
            "by_agent": by_agent,
            "rules_count": len(self.rules),
        }
