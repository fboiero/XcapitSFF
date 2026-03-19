"""Pipeline Automation Engine — rule-based lead advancement and actions.

Evaluates leads against configurable rules and automatically executes
actions such as stage advancement, agent assignment, outreach triggering,
note addition, notifications, and tagging.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead, LeadStage, OutreachMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TriggerType(str, Enum):
    """How a rule is triggered."""

    EVENT = "event"
    SCHEDULE = "schedule"
    CONDITION = "condition"


class Operator(str, Enum):
    """Comparison operators for conditions."""

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    CONTAINS = "contains"


class ActionType(str, Enum):
    """Types of actions the engine can execute."""

    ADVANCE_STAGE = "advance_stage"
    ASSIGN_AGENT = "assign_agent"
    SEND_OUTREACH = "send_outreach"
    ADD_NOTE = "add_note"
    NOTIFY = "notify"
    TAG = "tag"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Condition:
    """A single condition to evaluate against a lead."""

    field: str
    operator: Operator | str
    value: Any

    def __post_init__(self) -> None:
        if isinstance(self.operator, str):
            self.operator = Operator(self.operator)


@dataclass
class Action:
    """An action to execute when a rule matches."""

    action_type: ActionType | str
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.action_type, str):
            self.action_type = ActionType(self.action_type)


@dataclass
class AutomationRule:
    """A complete automation rule with conditions and actions."""

    rule_id: str
    name: str
    trigger: TriggerType | str
    conditions: list[Condition]
    actions: list[Action]
    is_active: bool = True
    priority: int = 0
    cooldown_minutes: int = 60

    def __post_init__(self) -> None:
        if isinstance(self.trigger, str):
            self.trigger = TriggerType(self.trigger)


@dataclass
class AutomationReport:
    """Summary of a batch automation run."""

    total_leads_evaluated: int = 0
    rules_triggered: int = 0
    actions_executed: int = 0
    by_rule: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------


def evaluate_condition(condition: Condition, lead_data: dict[str, Any]) -> bool:
    """Evaluate a single condition against lead data.

    Returns True if the condition is satisfied, False otherwise.
    Missing fields cause the condition to fail (return False).
    """
    field_value = lead_data.get(condition.field)

    # A missing field means the condition cannot be satisfied
    if field_value is None:
        return False

    op = condition.operator
    expected = condition.value

    try:
        if op == Operator.EQ:
            return field_value == expected
        if op == Operator.NE:
            return field_value != expected
        if op == Operator.GT:
            return float(field_value) > float(expected)
        if op == Operator.LT:
            return float(field_value) < float(expected)
        if op == Operator.GTE:
            return float(field_value) >= float(expected)
        if op == Operator.LTE:
            return float(field_value) <= float(expected)
        if op == Operator.IN:
            if isinstance(expected, (list, tuple, set)):
                return field_value in expected
            return field_value in expected
        if op == Operator.CONTAINS:
            return str(expected) in str(field_value)
    except (TypeError, ValueError):
        return False

    return False


def evaluate_conditions(
    conditions: list[Condition], lead_data: dict[str, Any]
) -> bool:
    """Evaluate all conditions (AND logic). All must pass."""
    return all(evaluate_condition(c, lead_data) for c in conditions)


# ---------------------------------------------------------------------------
# Lead-to-dict helper
# ---------------------------------------------------------------------------


def lead_to_dict(lead: Lead) -> dict[str, Any]:
    """Convert a Lead ORM model to a plain dict for rule evaluation."""
    now = datetime.now(tz=None)
    updated_at = lead.updated_at or lead.created_at or now

    days_in_stage = (now - updated_at).days if updated_at else 0

    stage_value = lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage)
    afinidad_value = (
        lead.afinidad.value if hasattr(lead.afinidad, "value") else str(lead.afinidad)
    )
    region_value = (
        lead.region.value if hasattr(lead.region, "value") else str(lead.region)
    )

    return {
        "id": lead.id,
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "region": region_value,
        "c_level": lead.c_level,
        "score_icp": lead.score_icp,
        "afinidad": afinidad_value,
        "stage": stage_value,
        "notes": lead.notes,
        "assigned_agent": lead.assigned_agent,
        "days_in_stage": days_in_stage,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
    }


# ---------------------------------------------------------------------------
# Pre-configured rules
# ---------------------------------------------------------------------------


def _build_default_rules() -> list[AutomationRule]:
    """Return the set of pre-configured automation rules."""
    return [
        # a. Auto-qualify hot leads: high ICP + C-level + raw stage
        AutomationRule(
            rule_id="auto_qualify_hot",
            name="Auto-qualify hot C-level leads",
            trigger=TriggerType.CONDITION,
            conditions=[
                Condition(field="score_icp", operator=Operator.GTE, value=70),
                Condition(field="c_level", operator=Operator.EQ, value=True),
                Condition(field="stage", operator=Operator.EQ, value="raw"),
            ],
            actions=[
                Action(
                    action_type=ActionType.ADVANCE_STAGE,
                    params={"target_stage": "qualified"},
                ),
            ],
            priority=100,
            cooldown_minutes=60,
        ),
        # b. Auto-qualify high afinidad leads
        AutomationRule(
            rule_id="auto_qualify_high_afinidad",
            name="Auto-qualify high afinidad leads",
            trigger=TriggerType.CONDITION,
            conditions=[
                Condition(field="afinidad", operator=Operator.EQ, value="HIGH"),
                Condition(field="score_icp", operator=Operator.GTE, value=60),
                Condition(field="stage", operator=Operator.EQ, value="raw"),
            ],
            actions=[
                Action(
                    action_type=ActionType.ADVANCE_STAGE,
                    params={"target_stage": "qualified"},
                ),
            ],
            priority=90,
            cooldown_minutes=60,
        ),
        # c. Assign top leads to senior sales
        AutomationRule(
            rule_id="assign_top_leads",
            name="Assign top leads to senior sales",
            trigger=TriggerType.CONDITION,
            conditions=[
                Condition(field="score_icp", operator=Operator.GTE, value=80),
            ],
            actions=[
                Action(
                    action_type=ActionType.ASSIGN_AGENT,
                    params={"agent": "senior_sales"},
                ),
            ],
            priority=80,
            cooldown_minutes=120,
        ),
        # d. Flag stale leads
        AutomationRule(
            rule_id="flag_stale_leads",
            name="Flag stale leads for review",
            trigger=TriggerType.SCHEDULE,
            conditions=[
                Condition(field="days_in_stage", operator=Operator.GT, value=30),
                Condition(
                    field="stage",
                    operator=Operator.NE,
                    value="won",
                ),
                Condition(
                    field="stage",
                    operator=Operator.NE,
                    value="lost",
                ),
            ],
            actions=[
                Action(
                    action_type=ActionType.ADD_NOTE,
                    params={"note": "Lead estancado, revisar"},
                ),
            ],
            priority=50,
            cooldown_minutes=1440,  # once per day
        ),
        # e. Auto-outreach for qualified leads with no outreach
        AutomationRule(
            rule_id="auto_outreach_qualified",
            name="Auto-outreach for qualified leads",
            trigger=TriggerType.CONDITION,
            conditions=[
                Condition(field="stage", operator=Operator.EQ, value="qualified"),
                Condition(field="outreach_count", operator=Operator.EQ, value=0),
                Condition(field="score_icp", operator=Operator.GTE, value=50),
            ],
            actions=[
                Action(
                    action_type=ActionType.SEND_OUTREACH,
                    params={"channel": "email"},
                ),
            ],
            priority=70,
            cooldown_minutes=240,
        ),
        # f. Escalate high-value C-level leads
        AutomationRule(
            rule_id="escalate_high_value",
            name="Escalate high-value C-level leads to VP Sales",
            trigger=TriggerType.CONDITION,
            conditions=[
                Condition(field="score_icp", operator=Operator.GTE, value=90),
                Condition(field="c_level", operator=Operator.EQ, value=True),
            ],
            actions=[
                Action(
                    action_type=ActionType.NOTIFY,
                    params={"recipient": "VP Sales"},
                ),
            ],
            priority=95,
            cooldown_minutes=480,
        ),
    ]


# ---------------------------------------------------------------------------
# Automation Engine
# ---------------------------------------------------------------------------


class AutomationEngine:
    """Rule-based pipeline automation engine.

    Manages a set of automation rules, evaluates them against leads,
    and executes matching actions.
    """

    def __init__(self, load_defaults: bool = True) -> None:
        self._rules: dict[str, AutomationRule] = {}
        self._execution_log: list[dict[str, Any]] = []
        self._stats = {
            "total_evaluations": 0,
            "total_rules_triggered": 0,
            "total_actions_executed": 0,
            "by_rule": {},
            "by_action_type": {},
            "errors": 0,
            "last_run": None,
        }

        if load_defaults:
            for rule in _build_default_rules():
                self.register_rule(rule)

    # -- Rule management ----------------------------------------------------

    def register_rule(self, rule: AutomationRule) -> None:
        """Add or update a rule in the engine."""
        self._rules[rule.rule_id] = rule
        logger.info("Rule registered: %s (%s)", rule.rule_id, rule.name)

    def get_rules(self) -> list[AutomationRule]:
        """Return all registered rules sorted by priority (descending)."""
        return sorted(self._rules.values(), key=lambda r: r.priority, reverse=True)

    def get_rule(self, rule_id: str) -> AutomationRule | None:
        """Get a specific rule by ID."""
        return self._rules.get(rule_id)

    def deactivate_rule(self, rule_id: str) -> bool:
        """Deactivate a rule. Returns False if not found."""
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        rule.is_active = False
        return True

    def activate_rule(self, rule_id: str) -> bool:
        """Activate a rule. Returns False if not found."""
        rule = self._rules.get(rule_id)
        if rule is None:
            return False
        rule.is_active = True
        return True

    # -- Evaluation ---------------------------------------------------------

    def evaluate_lead(self, lead_data: dict[str, Any]) -> list[Action]:
        """Evaluate all active rules against a single lead.

        Returns the list of actions from all matching rules,
        ordered by rule priority (highest first).
        """
        self._stats["total_evaluations"] += 1
        matching_actions: list[Action] = []

        for rule in self.get_rules():
            if not rule.is_active:
                continue

            if evaluate_conditions(rule.conditions, lead_data):
                matching_actions.extend(rule.actions)
                self._stats["total_rules_triggered"] += 1

                # Track per-rule stats
                self._stats["by_rule"].setdefault(rule.rule_id, 0)
                self._stats["by_rule"][rule.rule_id] += 1

                logger.debug(
                    "Rule '%s' matched for lead data (score_icp=%s, stage=%s)",
                    rule.rule_id,
                    lead_data.get("score_icp"),
                    lead_data.get("stage"),
                )

        return matching_actions

    # -- Action execution ---------------------------------------------------

    async def execute_actions(
        self,
        db: AsyncSession,
        lead_id: int,
        actions: list[Action],
    ) -> list[dict[str, Any]]:
        """Execute a list of actions on a lead.

        Returns a list of result dicts describing each executed action.
        """
        results: list[dict[str, Any]] = []

        # Fetch the lead
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if lead is None:
            error_msg = f"Lead {lead_id} not found"
            logger.warning(error_msg)
            return [{"action": "error", "detail": error_msg}]

        for action in actions:
            try:
                action_result = await self._execute_single_action(db, lead, action)
                results.append(action_result)
                self._stats["total_actions_executed"] += 1

                # Track per action-type
                at = action.action_type.value
                self._stats["by_action_type"].setdefault(at, 0)
                self._stats["by_action_type"][at] += 1

            except Exception as exc:
                self._stats["errors"] += 1
                error_detail = {
                    "action": action.action_type.value,
                    "error": str(exc),
                    "lead_id": lead_id,
                }
                results.append(error_detail)
                logger.error(
                    "Action '%s' failed for lead %d: %s",
                    action.action_type.value,
                    lead_id,
                    exc,
                )

        await db.flush()
        return results

    async def _execute_single_action(
        self,
        db: AsyncSession,
        lead: Lead,
        action: Action,
    ) -> dict[str, Any]:
        """Execute one action on a lead. Returns a result dict."""
        at = action.action_type

        if at == ActionType.ADVANCE_STAGE:
            target = action.params.get("target_stage", "qualified")
            old_stage = lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage)
            lead.stage = LeadStage(target)
            logger.info(
                "Lead %d: stage advanced %s -> %s", lead.id, old_stage, target
            )
            return {
                "action": "advance_stage",
                "lead_id": lead.id,
                "old_stage": old_stage,
                "new_stage": target,
            }

        if at == ActionType.ASSIGN_AGENT:
            agent = action.params.get("agent", "unassigned")
            old_agent = lead.assigned_agent
            lead.assigned_agent = agent
            logger.info("Lead %d: assigned to %s", lead.id, agent)
            return {
                "action": "assign_agent",
                "lead_id": lead.id,
                "old_agent": old_agent,
                "new_agent": agent,
            }

        if at == ActionType.SEND_OUTREACH:
            channel = action.params.get("channel", "email")
            outreach = OutreachMessage(
                lead_id=lead.id,
                channel=channel,
                subject=f"Automated outreach for {lead.company_name or 'lead'}",
                body=action.params.get(
                    "body",
                    f"Automated outreach message for lead {lead.id}",
                ),
                status="draft",
                generated_by="automation_engine",
            )
            db.add(outreach)
            logger.info("Lead %d: outreach drafted via %s", lead.id, channel)
            return {
                "action": "send_outreach",
                "lead_id": lead.id,
                "channel": channel,
            }

        if at == ActionType.ADD_NOTE:
            note = action.params.get("note", "")
            existing_notes = lead.notes or ""
            timestamp = datetime.now(tz=None).strftime("%Y-%m-%d %H:%M")
            separator = "\n" if existing_notes else ""
            lead.notes = f"{existing_notes}{separator}[{timestamp}] {note}"
            logger.info("Lead %d: note added", lead.id)
            return {"action": "add_note", "lead_id": lead.id, "note": note}

        if at == ActionType.NOTIFY:
            recipient = action.params.get("recipient", "system")
            logger.info(
                "Lead %d: notification sent to %s", lead.id, recipient
            )
            return {
                "action": "notify",
                "lead_id": lead.id,
                "recipient": recipient,
                "message": f"Lead {lead.id} ({lead.company_name}) requires attention",
            }

        if at == ActionType.TAG:
            tag = action.params.get("tag", "")
            existing_notes = lead.notes or ""
            separator = "\n" if existing_notes else ""
            lead.notes = f"{existing_notes}{separator}[TAG] {tag}"
            logger.info("Lead %d: tagged with '%s'", lead.id, tag)
            return {"action": "tag", "lead_id": lead.id, "tag": tag}

        return {"action": "unknown", "action_type": at.value}

    # -- Combined run -------------------------------------------------------

    async def run_automation(
        self, db: AsyncSession, lead_id: int
    ) -> list[dict[str, Any]]:
        """Evaluate rules for a single lead and execute matching actions."""
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if lead is None:
            return [{"error": f"Lead {lead_id} not found"}]

        # Get outreach count for the lead
        outreach_count_result = await db.scalar(
            select(func.count(OutreachMessage.id)).where(
                OutreachMessage.lead_id == lead_id
            )
        )
        lead_data = lead_to_dict(lead)
        lead_data["outreach_count"] = outreach_count_result or 0

        actions = self.evaluate_lead(lead_data)
        if not actions:
            return [{"info": "No matching rules", "lead_id": lead_id}]

        return await self.execute_actions(db, lead_id, actions)

    async def run_batch_automation(self, db: AsyncSession) -> AutomationReport:
        """Run all rules against all leads.

        Returns an AutomationReport summarising the run.
        """
        report = AutomationReport()
        start = time.monotonic()

        # Fetch all leads
        all_leads_result = await db.execute(select(Lead))
        leads = list(all_leads_result.scalars().all())
        report.total_leads_evaluated = len(leads)

        # Pre-fetch outreach counts per lead
        outreach_counts: dict[int, int] = {}
        if leads:
            oc_result = await db.execute(
                select(
                    OutreachMessage.lead_id,
                    func.count(OutreachMessage.id),
                ).group_by(OutreachMessage.lead_id)
            )
            for row in oc_result:
                outreach_counts[row[0]] = row[1]

        for lead in leads:
            try:
                lead_data = lead_to_dict(lead)
                lead_data["outreach_count"] = outreach_counts.get(lead.id, 0)

                actions = self.evaluate_lead(lead_data)
                if not actions:
                    continue

                report.rules_triggered += 1
                exec_results = await self.execute_actions(db, lead.id, actions)

                for er in exec_results:
                    if "error" in er:
                        report.errors.append(
                            f"Lead {lead.id}: {er.get('error', 'unknown')}"
                        )
                    else:
                        report.actions_executed += 1
                        action_name = er.get("action", "unknown")
                        report.by_rule.setdefault(action_name, 0)
                        report.by_rule[action_name] += 1

            except Exception as exc:
                report.errors.append(f"Lead {lead.id}: {exc}")
                logger.error("Batch automation error for lead %d: %s", lead.id, exc)

        await db.flush()

        elapsed = time.monotonic() - start
        self._stats["last_run"] = datetime.now(tz=None).isoformat()
        logger.info(
            "Batch automation complete: %d leads, %d triggered, %d actions, %.2fs",
            report.total_leads_evaluated,
            report.rules_triggered,
            report.actions_executed,
            elapsed,
        )

        return report

    # -- Stats --------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return current execution statistics."""
        return dict(self._stats)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

automation_engine = AutomationEngine(load_defaults=True)
