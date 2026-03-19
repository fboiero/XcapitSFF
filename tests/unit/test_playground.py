"""Tests for Agent Playground and Workspace Health Score."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from xcapitsff.selfservice.health_score import (
    CATEGORY_WEIGHTS,
    HealthCategory,
    HealthCheck,
    HealthScoreCalculator,
    WorkspaceHealth,
)
from xcapitsff.selfservice.playground import PlaygroundManager, PlaygroundSession


# ===================================================================
# Playground — session management
# ===================================================================


class TestPlaygroundSessionStart:
    def test_start_session_creates_session(self):
        mgr = PlaygroundManager()
        session = mgr.start_session("sales_qualifier")

        assert isinstance(session, PlaygroundSession)
        assert session.agent_role == "sales_qualifier"
        assert session.session_id
        assert session.messages == []
        assert isinstance(session.started_at, datetime)

    def test_start_session_unique_ids(self):
        mgr = PlaygroundManager()
        s1 = mgr.start_session("sales_qualifier")
        s2 = mgr.start_session("sales_qualifier")
        assert s1.session_id != s2.session_id

    def test_start_session_different_roles(self):
        mgr = PlaygroundManager()
        s1 = mgr.start_session("sales_qualifier")
        s2 = mgr.start_session("outreach_composer")
        assert s1.agent_role == "sales_qualifier"
        assert s2.agent_role == "outreach_composer"


class TestPlaygroundGetSession:
    def test_get_session_returns_correct_session(self):
        mgr = PlaygroundManager()
        created = mgr.start_session("ticket_router")
        found = mgr.get_session(created.session_id)
        assert found.session_id == created.session_id
        assert found.agent_role == "ticket_router"

    def test_get_session_not_found(self):
        mgr = PlaygroundManager()
        with pytest.raises(KeyError, match="not found"):
            mgr.get_session("nonexistent-id")


class TestPlaygroundListSessions:
    def test_list_sessions_empty(self):
        mgr = PlaygroundManager()
        assert mgr.list_sessions() == []

    def test_list_sessions_returns_all(self):
        mgr = PlaygroundManager()
        mgr.start_session("sales_qualifier")
        mgr.start_session("outreach_composer")
        mgr.start_session("support_responder")

        sessions = mgr.list_sessions()
        assert len(sessions) == 3
        roles = {s.agent_role for s in sessions}
        assert roles == {"sales_qualifier", "outreach_composer", "support_responder"}


# ===================================================================
# Playground — send message (dry-run mode)
# ===================================================================


class TestPlaygroundSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_appends_to_history(self):
        mock_dispatcher = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = "Respuesta del agente"
        mock_result.backend = "dry_run"
        mock_dispatcher.dispatch = AsyncMock(return_value=mock_result)

        mgr = PlaygroundManager(dispatcher=mock_dispatcher)
        session = mgr.start_session("sales_qualifier")

        response = await mgr.send_message(session.session_id, "Hola agente")

        assert response == "Respuesta del agente"
        assert len(session.messages) == 2
        assert session.messages[0] == ("user", "Hola agente")
        assert session.messages[1] == ("agent", "Respuesta del agente")

    @pytest.mark.asyncio
    async def test_send_message_nonexistent_session(self):
        mgr = PlaygroundManager()
        with pytest.raises(KeyError, match="not found"):
            await mgr.send_message("bad-id", "Hola")

    @pytest.mark.asyncio
    async def test_send_message_updates_last_active(self):
        mock_dispatcher = AsyncMock()
        mock_result = MagicMock()
        mock_result.content = "OK"
        mock_result.backend = "dry_run"
        mock_dispatcher.dispatch = AsyncMock(return_value=mock_result)

        mgr = PlaygroundManager(dispatcher=mock_dispatcher)
        session = mgr.start_session("support_responder")
        original_time = session.last_active

        await mgr.send_message(session.session_id, "Test")
        assert session.last_active >= original_time


# ===================================================================
# Playground — sample prompts
# ===================================================================


class TestSamplePrompts:
    def test_sales_qualifier_samples(self):
        samples = PlaygroundManager.get_sample_prompts("sales_qualifier")
        assert len(samples) == 2
        assert all("label" in s and "prompt" in s for s in samples)
        assert "fintech" in samples[0]["prompt"].lower()
        assert "Iberia" in samples[1]["prompt"]

    def test_outreach_composer_samples(self):
        samples = PlaygroundManager.get_sample_prompts("outreach_composer")
        assert len(samples) == 2
        assert "email" in samples[0]["prompt"].lower()
        assert "LinkedIn" in samples[1]["prompt"]

    def test_support_responder_samples(self):
        samples = PlaygroundManager.get_sample_prompts("support_responder")
        assert len(samples) == 2
        assert "login" in samples[0]["prompt"].lower()
        assert "48 horas" in samples[1]["prompt"]

    def test_ticket_router_samples(self):
        samples = PlaygroundManager.get_sample_prompts("ticket_router")
        assert len(samples) == 2
        assert "URGENTE" in samples[0]["prompt"]
        assert "plan Pro" in samples[1]["prompt"]

    def test_unknown_role_returns_empty(self):
        samples = PlaygroundManager.get_sample_prompts("nonexistent_role")
        assert samples == []


# ===================================================================
# Health Score — grade calculation
# ===================================================================


class TestGradeCalculation:
    def test_grade_a(self):
        assert HealthScoreCalculator.get_grade(90) == "A"
        assert HealthScoreCalculator.get_grade(100) == "A"

    def test_grade_b(self):
        assert HealthScoreCalculator.get_grade(75) == "B"
        assert HealthScoreCalculator.get_grade(89) == "B"

    def test_grade_c(self):
        assert HealthScoreCalculator.get_grade(60) == "C"
        assert HealthScoreCalculator.get_grade(74) == "C"

    def test_grade_d(self):
        assert HealthScoreCalculator.get_grade(40) == "D"
        assert HealthScoreCalculator.get_grade(59) == "D"

    def test_grade_f(self):
        assert HealthScoreCalculator.get_grade(0) == "F"
        assert HealthScoreCalculator.get_grade(39) == "F"


# ===================================================================
# Health Score — health check objects
# ===================================================================


class TestHealthChecks:
    def test_health_check_creation(self):
        check = HealthCheck(
            category=HealthCategory.DATA_QUALITY,
            name="leads_with_email",
            score=85,
            status="good",
            recommendation="",
            weight=0.15,
        )
        assert check.category == HealthCategory.DATA_QUALITY
        assert check.score == 85
        assert check.status == "good"

    def test_health_check_critical(self):
        check = HealthCheck(
            category=HealthCategory.SUPPORT_EFFICIENCY,
            name="sla_compliance",
            score=20,
            status="critical",
            recommendation="Mejorar SLA",
            weight=0.20,
        )
        assert check.status == "critical"
        assert check.recommendation == "Mejorar SLA"

    def test_health_category_enum_values(self):
        assert HealthCategory.DATA_QUALITY.value == "data_quality"
        assert HealthCategory.PIPELINE_HEALTH.value == "pipeline_health"
        assert HealthCategory.SUPPORT_EFFICIENCY.value == "support_efficiency"
        assert HealthCategory.AGENT_UTILIZATION.value == "agent_utilization"
        assert HealthCategory.CONFIGURATION.value == "configuration"
        assert HealthCategory.ENGAGEMENT.value == "engagement"


# ===================================================================
# Health Score — calculate_health (mocked DB)
# ===================================================================


class TestHealthScoreCalculation:
    @pytest.mark.asyncio
    async def test_calculate_health_all_good(self):
        """Simulate a workspace where all queries return high values."""
        calc = HealthScoreCalculator()
        db = AsyncMock()

        # Make every scalar query return a large number
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        db.execute = AsyncMock(return_value=mock_result)

        health = await calc.calculate_health(db)

        assert isinstance(health, WorkspaceHealth)
        assert 0 <= health.overall_score <= 100
        assert health.grade in ("A", "B", "C", "D", "F")
        assert isinstance(health.checks, list)
        assert len(health.checks) > 0
        assert isinstance(health.last_checked, datetime)

    @pytest.mark.asyncio
    async def test_calculate_health_empty_db(self):
        """Simulate empty database — all queries return 0."""
        calc = HealthScoreCalculator()
        db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)

        health = await calc.calculate_health(db)

        assert isinstance(health, WorkspaceHealth)
        assert health.overall_score >= 0
        assert len(health.checks) > 0

    @pytest.mark.asyncio
    async def test_calculate_health_db_errors(self):
        """Simulate DB errors — should not crash, use defaults."""
        calc = HealthScoreCalculator()
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB unavailable"))

        health = await calc.calculate_health(db)

        assert isinstance(health, WorkspaceHealth)
        assert health.overall_score >= 0


# ===================================================================
# Health Score — recommendations
# ===================================================================


class TestRecommendations:
    def test_recommendations_from_critical_checks(self):
        checks = [
            HealthCheck(
                category=HealthCategory.DATA_QUALITY,
                name="leads_with_email",
                score=30,
                status="critical",
                recommendation="Agregá emails a tus leads.",
                weight=0.15,
            ),
            HealthCheck(
                category=HealthCategory.PIPELINE_HEALTH,
                name="conversion_rate",
                score=90,
                status="good",
                recommendation="",
                weight=0.25,
            ),
        ]
        recs = HealthScoreCalculator.get_recommendations_from_checks(checks)
        assert len(recs) == 1
        assert "emails" in recs[0]

    def test_recommendations_from_health_object(self):
        health = WorkspaceHealth(
            overall_score=50,
            grade="C",
            checks=[],
            recommendations=["Mejorá tu data quality.", "Activá agentes."],
        )
        recs = HealthScoreCalculator.get_recommendations(health)
        assert len(recs) == 2

    def test_no_recommendations_when_all_good(self):
        checks = [
            HealthCheck(
                category=HealthCategory.DATA_QUALITY,
                name="leads_with_email",
                score=95,
                status="good",
                recommendation="",
                weight=0.15,
            ),
        ]
        recs = HealthScoreCalculator.get_recommendations_from_checks(checks)
        assert recs == []


# ===================================================================
# Health Score — category weights
# ===================================================================


class TestCategoryWeights:
    def test_weights_sum_to_one(self):
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_all_categories_have_weights(self):
        for cat in HealthCategory:
            assert cat in CATEGORY_WEIGHTS
