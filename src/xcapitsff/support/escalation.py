"""Escalation Workflow Engine — structured escalation paths for tickets.

Defines escalation levels, rules, and actions. Integrates with the
SLA monitor and notification system.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from xcapitsff.core.events import Event, EventType, event_bus

logger = logging.getLogger(__name__)


class EscalationLevel(str, Enum):
    L1 = "L1"  # First-line support agent
    L2 = "L2"  # Senior support / specialist
    L3 = "L3"  # Team lead / manager
    L4 = "L4"  # VP / executive (critical issues)


class EscalationReason(str, Enum):
    SLA_BREACH = "sla_breach"
    CUSTOMER_DISSATISFIED = "customer_dissatisfied"
    REPEATED_CONTACT = "repeated_contact"
    HIGH_VALUE_CUSTOMER = "high_value_customer"
    SECURITY_ISSUE = "security_issue"
    FINANCIAL_RISK = "financial_risk"
    MANUAL = "manual"


@dataclass
class EscalationAction:
    ticket_id: int
    from_level: EscalationLevel
    to_level: EscalationLevel
    reason: EscalationReason
    assigned_to: str
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    auto: bool = True  # was it automatic or manual?


@dataclass
class EscalationPolicy:
    """Defines when and how to escalate."""
    level: EscalationLevel
    max_response_minutes: int
    max_resolution_hours: int
    assigned_pool: list[str]  # agent names in this level
    auto_escalate_after_minutes: int | None = None


# Default escalation policies
DEFAULT_POLICIES: list[EscalationPolicy] = [
    EscalationPolicy(
        level=EscalationLevel.L1,
        max_response_minutes=30,
        max_resolution_hours=24,
        assigned_pool=["support_responder", "support_responder_billing",
                       "support_responder_tech", "support_responder_account"],
        auto_escalate_after_minutes=60,
    ),
    EscalationPolicy(
        level=EscalationLevel.L2,
        max_response_minutes=15,
        max_resolution_hours=8,
        assigned_pool=["support_responder_senior", "support_responder_crypto"],
        auto_escalate_after_minutes=120,
    ),
    EscalationPolicy(
        level=EscalationLevel.L3,
        max_response_minutes=10,
        max_resolution_hours=4,
        assigned_pool=["team_lead_support"],
        auto_escalate_after_minutes=240,
    ),
    EscalationPolicy(
        level=EscalationLevel.L4,
        max_response_minutes=5,
        max_resolution_hours=2,
        assigned_pool=["vp_customer_success"],
        auto_escalate_after_minutes=None,  # no auto-escalation beyond L4
    ),
]


class EscalationEngine:
    """Manages ticket escalation workflows."""

    def __init__(self, policies: list[EscalationPolicy] | None = None):
        self.policies = {p.level: p for p in (policies or DEFAULT_POLICIES)}
        self._history: list[EscalationAction] = []
        self._current_levels: dict[int, EscalationLevel] = {}

    def get_current_level(self, ticket_id: int) -> EscalationLevel:
        return self._current_levels.get(ticket_id, EscalationLevel.L1)

    def get_policy(self, level: EscalationLevel) -> EscalationPolicy | None:
        return self.policies.get(level)

    def _next_level(self, current: EscalationLevel) -> EscalationLevel | None:
        levels = [EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3, EscalationLevel.L4]
        idx = levels.index(current)
        if idx + 1 < len(levels):
            return levels[idx + 1]
        return None

    async def escalate(
        self,
        ticket_id: int,
        reason: EscalationReason,
        notes: str = "",
        auto: bool = True,
    ) -> EscalationAction | None:
        """Escalate a ticket to the next level."""
        current = self.get_current_level(ticket_id)
        next_level = self._next_level(current)

        if next_level is None:
            logger.warning(f"Ticket {ticket_id} already at max escalation level ({current.value})")
            return None

        policy = self.policies.get(next_level)
        if not policy:
            return None

        # Pick the first available agent from the pool
        assigned_to = policy.assigned_pool[0] if policy.assigned_pool else "unassigned"

        action = EscalationAction(
            ticket_id=ticket_id,
            from_level=current,
            to_level=next_level,
            reason=reason,
            assigned_to=assigned_to,
            notes=notes,
            auto=auto,
        )

        self._current_levels[ticket_id] = next_level
        self._history.append(action)

        # Emit event
        await event_bus.emit(Event(
            type=EventType.TICKET_ESCALATED,
            data={
                "ticket_id": ticket_id,
                "from_level": current.value,
                "to_level": next_level.value,
                "reason": reason.value,
                "assigned_to": assigned_to,
            },
            source="escalation_engine",
        ))

        logger.info(
            f"Ticket {ticket_id} escalated: {current.value} → {next_level.value} "
            f"({reason.value}) → {assigned_to}"
        )
        return action

    def should_auto_escalate(
        self, ticket_id: int, age_minutes: float, interactions_without_resolution: int
    ) -> tuple[bool, EscalationReason | None]:
        """Check if a ticket should be auto-escalated."""
        current = self.get_current_level(ticket_id)
        policy = self.policies.get(current)

        if not policy or policy.auto_escalate_after_minutes is None:
            return False, None

        if age_minutes >= policy.auto_escalate_after_minutes:
            return True, EscalationReason.SLA_BREACH

        if interactions_without_resolution >= 3:
            return True, EscalationReason.REPEATED_CONTACT

        return False, None

    def get_history(self, ticket_id: int | None = None) -> list[EscalationAction]:
        if ticket_id is not None:
            return [a for a in self._history if a.ticket_id == ticket_id]
        return list(self._history)

    def get_stats(self) -> dict:
        by_level: dict[str, int] = {}
        by_reason: dict[str, int] = {}
        auto_count = 0
        manual_count = 0

        for action in self._history:
            by_level[action.to_level.value] = by_level.get(action.to_level.value, 0) + 1
            by_reason[action.reason.value] = by_reason.get(action.reason.value, 0) + 1
            if action.auto:
                auto_count += 1
            else:
                manual_count += 1

        return {
            "total_escalations": len(self._history),
            "by_level": by_level,
            "by_reason": by_reason,
            "auto": auto_count,
            "manual": manual_count,
            "tickets_at_max_level": sum(
                1 for level in self._current_levels.values()
                if level == EscalationLevel.L4
            ),
        }


# Singleton
escalation_engine = EscalationEngine()
