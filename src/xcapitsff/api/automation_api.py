"""API endpoints for Pipeline Automation Engine."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.sales.automation import (
    Action,
    ActionType,
    AutomationEngine,
    AutomationRule,
    Condition,
    Operator,
    TriggerType,
    automation_engine,
)

router = APIRouter(prefix="/automation", tags=["Automation"])


# ---------------------------------------------------------------------------
# Pydantic schemas for request/response
# ---------------------------------------------------------------------------


class ConditionSchema(BaseModel):
    field: str
    operator: str
    value: object


class ActionSchema(BaseModel):
    action_type: str
    params: dict = Field(default_factory=dict)


class RuleCreateSchema(BaseModel):
    rule_id: str
    name: str
    trigger: str = "condition"
    conditions: list[ConditionSchema]
    actions: list[ActionSchema]
    is_active: bool = True
    priority: int = 0
    cooldown_minutes: int = 60


class RuleToggleSchema(BaseModel):
    is_active: bool


class RuleResponseSchema(BaseModel):
    rule_id: str
    name: str
    trigger: str
    conditions: list[ConditionSchema]
    actions: list[ActionSchema]
    is_active: bool
    priority: int
    cooldown_minutes: int


class AutomationReportSchema(BaseModel):
    total_leads_evaluated: int
    rules_triggered: int
    actions_executed: int
    by_rule: dict[str, int]
    errors: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rule_to_response(rule: AutomationRule) -> dict:
    """Convert an AutomationRule to a JSON-safe dict."""
    return {
        "rule_id": rule.rule_id,
        "name": rule.name,
        "trigger": rule.trigger.value if hasattr(rule.trigger, "value") else str(rule.trigger),
        "conditions": [
            {
                "field": c.field,
                "operator": c.operator.value if hasattr(c.operator, "value") else str(c.operator),
                "value": c.value,
            }
            for c in rule.conditions
        ],
        "actions": [
            {
                "action_type": a.action_type.value
                if hasattr(a.action_type, "value")
                else str(a.action_type),
                "params": a.params,
            }
            for a in rule.actions
        ],
        "is_active": rule.is_active,
        "priority": rule.priority,
        "cooldown_minutes": rule.cooldown_minutes,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/rules", response_model=list[RuleResponseSchema])
async def list_rules():
    """List all registered automation rules ordered by priority."""
    rules = automation_engine.get_rules()
    return [_rule_to_response(r) for r in rules]


@router.post("/rules", response_model=RuleResponseSchema, status_code=201)
async def create_rule(data: RuleCreateSchema):
    """Register a new custom automation rule."""
    # Validate enums
    try:
        trigger = TriggerType(data.trigger)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger type: {data.trigger}. "
            f"Valid: {[t.value for t in TriggerType]}",
        )

    conditions = []
    for c in data.conditions:
        try:
            op = Operator(c.operator)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operator: {c.operator}. "
                f"Valid: {[o.value for o in Operator]}",
            )
        conditions.append(Condition(field=c.field, operator=op, value=c.value))

    actions = []
    for a in data.actions:
        try:
            at = ActionType(a.action_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action type: {a.action_type}. "
                f"Valid: {[t.value for t in ActionType]}",
            )
        actions.append(Action(action_type=at, params=a.params))

    rule = AutomationRule(
        rule_id=data.rule_id,
        name=data.name,
        trigger=trigger,
        conditions=conditions,
        actions=actions,
        is_active=data.is_active,
        priority=data.priority,
        cooldown_minutes=data.cooldown_minutes,
    )

    automation_engine.register_rule(rule)
    return _rule_to_response(rule)


@router.patch("/rules/{rule_id}", response_model=RuleResponseSchema)
async def toggle_rule(rule_id: str, data: RuleToggleSchema):
    """Activate or deactivate a rule."""
    rule = automation_engine.get_rule(rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    if data.is_active:
        automation_engine.activate_rule(rule_id)
    else:
        automation_engine.deactivate_rule(rule_id)

    return _rule_to_response(rule)


@router.post("/run", response_model=AutomationReportSchema)
async def run_batch_automation(db: AsyncSession = Depends(get_db)):
    """Trigger automation run on all eligible leads."""
    report = await automation_engine.run_batch_automation(db)
    return {
        "total_leads_evaluated": report.total_leads_evaluated,
        "rules_triggered": report.rules_triggered,
        "actions_executed": report.actions_executed,
        "by_rule": report.by_rule,
        "errors": report.errors,
    }


@router.post("/run/{lead_id}")
async def run_lead_automation(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Run automation on a specific lead."""
    results = await automation_engine.run_automation(db, lead_id)
    return {"lead_id": lead_id, "results": results}


@router.get("/stats")
async def get_automation_stats():
    """Return automation execution statistics."""
    return automation_engine.get_stats()
