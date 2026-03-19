"""Tests for Pipeline Automation Engine — conditions, rules, actions, batch."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from xcapitsff.core.database import Base
from xcapitsff.core.models import Lead, LeadStage, Afinidad, Region, OutreachMessage
from xcapitsff.sales.automation import (
    Action,
    ActionType,
    AutomationEngine,
    AutomationReport,
    AutomationRule,
    Condition,
    Operator,
    TriggerType,
    evaluate_condition,
    evaluate_conditions,
    lead_to_dict,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _TestSession() as session:
        yield session
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _make_lead(**overrides) -> Lead:
    """Create a Lead instance with sensible defaults."""
    defaults = {
        "company_name": "TestCo",
        "contact_name": "Jane Doe",
        "contact_email": "jane@testco.com",
        "region": Region.LATAM,
        "c_level": False,
        "score_icp": 50.0,
        "afinidad": Afinidad.MEDIUM,
        "stage": LeadStage.RAW,
        "notes": None,
        "assigned_agent": None,
    }
    defaults.update(overrides)
    return Lead(**defaults)


# ---------------------------------------------------------------------------
# 1-8: Condition evaluation (all operators)
# ---------------------------------------------------------------------------


class TestConditionEvaluation:
    def test_eq_operator_match(self):
        cond = Condition(field="stage", operator=Operator.EQ, value="raw")
        assert evaluate_condition(cond, {"stage": "raw"}) is True

    def test_eq_operator_no_match(self):
        cond = Condition(field="stage", operator=Operator.EQ, value="raw")
        assert evaluate_condition(cond, {"stage": "qualified"}) is False

    def test_ne_operator(self):
        cond = Condition(field="stage", operator=Operator.NE, value="won")
        assert evaluate_condition(cond, {"stage": "raw"}) is True
        assert evaluate_condition(cond, {"stage": "won"}) is False

    def test_gt_operator(self):
        cond = Condition(field="score_icp", operator=Operator.GT, value=70)
        assert evaluate_condition(cond, {"score_icp": 80}) is True
        assert evaluate_condition(cond, {"score_icp": 70}) is False
        assert evaluate_condition(cond, {"score_icp": 50}) is False

    def test_lt_operator(self):
        cond = Condition(field="score_icp", operator=Operator.LT, value=50)
        assert evaluate_condition(cond, {"score_icp": 30}) is True
        assert evaluate_condition(cond, {"score_icp": 50}) is False

    def test_gte_operator(self):
        cond = Condition(field="score_icp", operator=Operator.GTE, value=70)
        assert evaluate_condition(cond, {"score_icp": 70}) is True
        assert evaluate_condition(cond, {"score_icp": 71}) is True
        assert evaluate_condition(cond, {"score_icp": 69}) is False

    def test_lte_operator(self):
        cond = Condition(field="score_icp", operator=Operator.LTE, value=50)
        assert evaluate_condition(cond, {"score_icp": 50}) is True
        assert evaluate_condition(cond, {"score_icp": 49}) is True
        assert evaluate_condition(cond, {"score_icp": 51}) is False

    def test_in_operator(self):
        cond = Condition(field="stage", operator=Operator.IN, value=["raw", "qualified"])
        assert evaluate_condition(cond, {"stage": "raw"}) is True
        assert evaluate_condition(cond, {"stage": "qualified"}) is True
        assert evaluate_condition(cond, {"stage": "won"}) is False

    def test_contains_operator(self):
        cond = Condition(field="notes", operator=Operator.CONTAINS, value="urgent")
        assert evaluate_condition(cond, {"notes": "This is urgent!"}) is True
        assert evaluate_condition(cond, {"notes": "Nothing special"}) is False

    def test_missing_field_returns_false(self):
        cond = Condition(field="nonexistent", operator=Operator.EQ, value=True)
        assert evaluate_condition(cond, {"stage": "raw"}) is False

    def test_condition_string_operator_coercion(self):
        """Condition accepts operator as a string and coerces to Operator enum."""
        cond = Condition(field="score_icp", operator="gte", value=70)
        assert cond.operator == Operator.GTE
        assert evaluate_condition(cond, {"score_icp": 75}) is True


# ---------------------------------------------------------------------------
# 9-10: Multiple conditions (AND logic)
# ---------------------------------------------------------------------------


class TestMultipleConditions:
    def test_all_conditions_must_pass(self):
        conditions = [
            Condition(field="score_icp", operator=Operator.GTE, value=70),
            Condition(field="c_level", operator=Operator.EQ, value=True),
            Condition(field="stage", operator=Operator.EQ, value="raw"),
        ]
        # All match
        data = {"score_icp": 80, "c_level": True, "stage": "raw"}
        assert evaluate_conditions(conditions, data) is True

    def test_one_failing_condition_rejects(self):
        conditions = [
            Condition(field="score_icp", operator=Operator.GTE, value=70),
            Condition(field="c_level", operator=Operator.EQ, value=True),
        ]
        # c_level is False
        data = {"score_icp": 80, "c_level": False}
        assert evaluate_conditions(conditions, data) is False


# ---------------------------------------------------------------------------
# 11-14: Rule matching and action generation
# ---------------------------------------------------------------------------


class TestRuleMatching:
    def test_engine_evaluate_lead_returns_actions(self):
        engine = AutomationEngine(load_defaults=False)
        rule = AutomationRule(
            rule_id="test_rule",
            name="Test",
            trigger=TriggerType.CONDITION,
            conditions=[
                Condition(field="score_icp", operator=Operator.GTE, value=70),
            ],
            actions=[
                Action(action_type=ActionType.ADVANCE_STAGE, params={"target_stage": "qualified"}),
            ],
            priority=10,
        )
        engine.register_rule(rule)
        actions = engine.evaluate_lead({"score_icp": 80, "stage": "raw"})
        assert len(actions) == 1
        assert actions[0].action_type == ActionType.ADVANCE_STAGE

    def test_no_matching_rules_returns_empty(self):
        engine = AutomationEngine(load_defaults=False)
        rule = AutomationRule(
            rule_id="test_rule",
            name="Test",
            trigger=TriggerType.CONDITION,
            conditions=[
                Condition(field="score_icp", operator=Operator.GTE, value=90),
            ],
            actions=[
                Action(action_type=ActionType.NOTIFY, params={"recipient": "admin"}),
            ],
        )
        engine.register_rule(rule)
        actions = engine.evaluate_lead({"score_icp": 50})
        assert actions == []

    def test_multiple_rules_match(self):
        engine = AutomationEngine(load_defaults=False)
        engine.register_rule(
            AutomationRule(
                rule_id="r1",
                name="R1",
                trigger=TriggerType.CONDITION,
                conditions=[Condition(field="score_icp", operator=Operator.GTE, value=70)],
                actions=[Action(action_type=ActionType.NOTIFY, params={"recipient": "A"})],
                priority=10,
            )
        )
        engine.register_rule(
            AutomationRule(
                rule_id="r2",
                name="R2",
                trigger=TriggerType.CONDITION,
                conditions=[Condition(field="c_level", operator=Operator.EQ, value=True)],
                actions=[Action(action_type=ActionType.ASSIGN_AGENT, params={"agent": "B"})],
                priority=5,
            )
        )
        actions = engine.evaluate_lead({"score_icp": 80, "c_level": True})
        assert len(actions) == 2

    def test_inactive_rule_skipped(self):
        engine = AutomationEngine(load_defaults=False)
        rule = AutomationRule(
            rule_id="inactive",
            name="Inactive",
            trigger=TriggerType.CONDITION,
            conditions=[Condition(field="score_icp", operator=Operator.GTE, value=0)],
            actions=[Action(action_type=ActionType.NOTIFY, params={})],
            is_active=False,
        )
        engine.register_rule(rule)
        actions = engine.evaluate_lead({"score_icp": 99})
        assert actions == []


# ---------------------------------------------------------------------------
# 15-17: Pre-configured rules behaviour
# ---------------------------------------------------------------------------


class TestPreConfiguredRules:
    def test_auto_qualify_hot_rule(self):
        engine = AutomationEngine(load_defaults=True)
        lead_data = {
            "score_icp": 75,
            "c_level": True,
            "stage": "raw",
            "afinidad": "MEDIUM",
            "days_in_stage": 0,
            "outreach_count": 1,
        }
        actions = engine.evaluate_lead(lead_data)
        action_types = [a.action_type for a in actions]
        assert ActionType.ADVANCE_STAGE in action_types

    def test_auto_qualify_high_afinidad_rule(self):
        engine = AutomationEngine(load_defaults=True)
        lead_data = {
            "score_icp": 65,
            "c_level": False,
            "stage": "raw",
            "afinidad": "HIGH",
            "days_in_stage": 0,
            "outreach_count": 1,
        }
        actions = engine.evaluate_lead(lead_data)
        action_types = [a.action_type for a in actions]
        assert ActionType.ADVANCE_STAGE in action_types

    def test_escalate_high_value_rule(self):
        engine = AutomationEngine(load_defaults=True)
        lead_data = {
            "score_icp": 95,
            "c_level": True,
            "stage": "qualified",
            "afinidad": "HIGH",
            "days_in_stage": 5,
            "outreach_count": 1,
        }
        actions = engine.evaluate_lead(lead_data)
        action_types = [a.action_type for a in actions]
        # escalate_high_value fires NOTIFY
        assert ActionType.NOTIFY in action_types
        # assign_top_leads fires ASSIGN_AGENT (score >= 80)
        assert ActionType.ASSIGN_AGENT in action_types


# ---------------------------------------------------------------------------
# 18-20: Action execution via DB
# ---------------------------------------------------------------------------


class TestActionExecution:
    @pytest.mark.asyncio
    async def test_advance_stage_action(self, db: AsyncSession):
        lead = _make_lead(stage=LeadStage.RAW, score_icp=80)
        db.add(lead)
        await db.flush()
        await db.refresh(lead)

        engine = AutomationEngine(load_defaults=False)
        actions = [Action(action_type=ActionType.ADVANCE_STAGE, params={"target_stage": "qualified"})]
        results = await engine.execute_actions(db, lead.id, actions)
        assert results[0]["action"] == "advance_stage"
        assert results[0]["new_stage"] == "qualified"

        await db.refresh(lead)
        stage_val = lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage)
        assert stage_val == "qualified"

    @pytest.mark.asyncio
    async def test_assign_agent_action(self, db: AsyncSession):
        lead = _make_lead()
        db.add(lead)
        await db.flush()
        await db.refresh(lead)

        engine = AutomationEngine(load_defaults=False)
        actions = [Action(action_type=ActionType.ASSIGN_AGENT, params={"agent": "senior_sales"})]
        results = await engine.execute_actions(db, lead.id, actions)
        assert results[0]["action"] == "assign_agent"
        assert results[0]["new_agent"] == "senior_sales"

        await db.refresh(lead)
        assert lead.assigned_agent == "senior_sales"

    @pytest.mark.asyncio
    async def test_add_note_action(self, db: AsyncSession):
        lead = _make_lead()
        db.add(lead)
        await db.flush()
        await db.refresh(lead)

        engine = AutomationEngine(load_defaults=False)
        actions = [Action(action_type=ActionType.ADD_NOTE, params={"note": "Lead estancado, revisar"})]
        results = await engine.execute_actions(db, lead.id, actions)
        assert results[0]["action"] == "add_note"

        await db.refresh(lead)
        assert "Lead estancado, revisar" in (lead.notes or "")

    @pytest.mark.asyncio
    async def test_send_outreach_action(self, db: AsyncSession):
        lead = _make_lead()
        db.add(lead)
        await db.flush()
        await db.refresh(lead)

        engine = AutomationEngine(load_defaults=False)
        actions = [Action(action_type=ActionType.SEND_OUTREACH, params={"channel": "email"})]
        results = await engine.execute_actions(db, lead.id, actions)
        assert results[0]["action"] == "send_outreach"
        assert results[0]["channel"] == "email"

    @pytest.mark.asyncio
    async def test_notify_action(self, db: AsyncSession):
        lead = _make_lead()
        db.add(lead)
        await db.flush()
        await db.refresh(lead)

        engine = AutomationEngine(load_defaults=False)
        actions = [Action(action_type=ActionType.NOTIFY, params={"recipient": "VP Sales"})]
        results = await engine.execute_actions(db, lead.id, actions)
        assert results[0]["action"] == "notify"
        assert results[0]["recipient"] == "VP Sales"

    @pytest.mark.asyncio
    async def test_tag_action(self, db: AsyncSession):
        lead = _make_lead()
        db.add(lead)
        await db.flush()
        await db.refresh(lead)

        engine = AutomationEngine(load_defaults=False)
        actions = [Action(action_type=ActionType.TAG, params={"tag": "high_priority"})]
        results = await engine.execute_actions(db, lead.id, actions)
        assert results[0]["action"] == "tag"
        assert results[0]["tag"] == "high_priority"

        await db.refresh(lead)
        assert "high_priority" in (lead.notes or "")

    @pytest.mark.asyncio
    async def test_execute_actions_on_missing_lead(self, db: AsyncSession):
        engine = AutomationEngine(load_defaults=False)
        actions = [Action(action_type=ActionType.NOTIFY, params={})]
        results = await engine.execute_actions(db, 99999, actions)
        assert results[0]["action"] == "error"


# ---------------------------------------------------------------------------
# 21-22: Batch automation
# ---------------------------------------------------------------------------


class TestBatchAutomation:
    @pytest.mark.asyncio
    async def test_batch_automation_processes_all_leads(self, db: AsyncSession):
        # Create leads: one hot C-level raw, one cold
        hot_lead = _make_lead(
            company_name="HotCo",
            score_icp=85,
            c_level=True,
            stage=LeadStage.RAW,
        )
        cold_lead = _make_lead(
            company_name="ColdCo",
            score_icp=20,
            c_level=False,
            stage=LeadStage.RAW,
            afinidad=Afinidad.LOW,
        )
        db.add_all([hot_lead, cold_lead])
        await db.flush()

        engine = AutomationEngine(load_defaults=True)
        report = await engine.run_batch_automation(db)
        assert report.total_leads_evaluated == 2
        assert report.actions_executed >= 1  # at least the hot lead triggers actions

    @pytest.mark.asyncio
    async def test_batch_automation_report_structure(self, db: AsyncSession):
        engine = AutomationEngine(load_defaults=True)
        report = await engine.run_batch_automation(db)
        assert isinstance(report, AutomationReport)
        assert isinstance(report.total_leads_evaluated, int)
        assert isinstance(report.rules_triggered, int)
        assert isinstance(report.actions_executed, int)
        assert isinstance(report.by_rule, dict)
        assert isinstance(report.errors, list)


# ---------------------------------------------------------------------------
# 23: Stats tracking
# ---------------------------------------------------------------------------


class TestStatsTracking:
    def test_stats_update_on_evaluation(self):
        engine = AutomationEngine(load_defaults=False)
        engine.register_rule(
            AutomationRule(
                rule_id="s1",
                name="Stats test",
                trigger=TriggerType.CONDITION,
                conditions=[Condition(field="score_icp", operator=Operator.GTE, value=50)],
                actions=[Action(action_type=ActionType.NOTIFY, params={})],
            )
        )
        engine.evaluate_lead({"score_icp": 60})
        engine.evaluate_lead({"score_icp": 60})
        engine.evaluate_lead({"score_icp": 10})

        stats = engine.get_stats()
        assert stats["total_evaluations"] == 3
        assert stats["total_rules_triggered"] == 2
        assert stats["by_rule"]["s1"] == 2


# ---------------------------------------------------------------------------
# 24-25: Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_engine_with_no_rules(self):
        engine = AutomationEngine(load_defaults=False)
        actions = engine.evaluate_lead({"score_icp": 100, "c_level": True})
        assert actions == []

    def test_all_rules_match_returns_all_actions(self):
        engine = AutomationEngine(load_defaults=False)
        for i in range(5):
            engine.register_rule(
                AutomationRule(
                    rule_id=f"r{i}",
                    name=f"Rule {i}",
                    trigger=TriggerType.CONDITION,
                    conditions=[
                        Condition(field="score_icp", operator=Operator.GTE, value=0),
                    ],
                    actions=[
                        Action(action_type=ActionType.NOTIFY, params={"n": i}),
                    ],
                )
            )
        actions = engine.evaluate_lead({"score_icp": 50})
        assert len(actions) == 5

    def test_activate_deactivate_rule(self):
        engine = AutomationEngine(load_defaults=False)
        rule = AutomationRule(
            rule_id="toggle",
            name="Toggle test",
            trigger=TriggerType.CONDITION,
            conditions=[Condition(field="x", operator=Operator.EQ, value=1)],
            actions=[Action(action_type=ActionType.NOTIFY, params={})],
        )
        engine.register_rule(rule)

        # Initially active
        assert len(engine.evaluate_lead({"x": 1})) == 1

        # Deactivate
        engine.deactivate_rule("toggle")
        assert len(engine.evaluate_lead({"x": 1})) == 0

        # Re-activate
        engine.activate_rule("toggle")
        assert len(engine.evaluate_lead({"x": 1})) == 1

    def test_deactivate_nonexistent_rule(self):
        engine = AutomationEngine(load_defaults=False)
        assert engine.deactivate_rule("nope") is False

    def test_rules_sorted_by_priority(self):
        engine = AutomationEngine(load_defaults=False)
        engine.register_rule(
            AutomationRule(
                rule_id="low",
                name="Low",
                trigger=TriggerType.CONDITION,
                conditions=[],
                actions=[],
                priority=1,
            )
        )
        engine.register_rule(
            AutomationRule(
                rule_id="high",
                name="High",
                trigger=TriggerType.CONDITION,
                conditions=[],
                actions=[],
                priority=100,
            )
        )
        rules = engine.get_rules()
        assert rules[0].rule_id == "high"
        assert rules[1].rule_id == "low"

    @pytest.mark.asyncio
    async def test_run_automation_for_missing_lead(self, db: AsyncSession):
        engine = AutomationEngine(load_defaults=True)
        results = await engine.run_automation(db, 99999)
        assert any("not found" in str(r) for r in results)

    def test_lead_to_dict_helper(self):
        lead = _make_lead(score_icp=72, c_level=True, stage=LeadStage.QUALIFIED)
        data = lead_to_dict(lead)
        assert data["score_icp"] == 72
        assert data["c_level"] is True
        assert data["stage"] == "qualified"
        assert "days_in_stage" in data

    def test_condition_type_error_returns_false(self):
        """Non-numeric comparison with gt/lt should return False, not raise."""
        cond = Condition(field="score_icp", operator=Operator.GT, value=50)
        assert evaluate_condition(cond, {"score_icp": "not_a_number"}) is False

    def test_eq_with_boolean(self):
        cond = Condition(field="c_level", operator=Operator.EQ, value=True)
        assert evaluate_condition(cond, {"c_level": True}) is True
        assert evaluate_condition(cond, {"c_level": False}) is False
