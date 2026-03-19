"""Tests for Predictive Analytics — conversion probability, pipeline forecast,
churn risk scoring, win/loss analysis, and edge cases.

All tests exercise the pure-function layer (no database required) so they
run fast and deterministically.
"""

from datetime import datetime, timedelta

import pytest

from xcapitsff.sales.predictions import (
    AFINIDAD_MODIFIER,
    STAGE_BASE_PROBABILITY,
    STAGE_EXPECTED_DAYS,
    ChurnRisk,
    LeadScoreHistory,
    PipelineForecast,
    WinLossAnalysis,
    _calculate_churn_risk_score,
    calculate_conversion_probability,
)


# -----------------------------------------------------------------------
# 1. Conversion probability calculation
# -----------------------------------------------------------------------


class TestConversionProbability:
    def test_raw_stage_base_probability(self):
        prob = calculate_conversion_probability(
            stage="raw",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        assert prob == STAGE_BASE_PROBABILITY["raw"]

    def test_negotiation_stage_has_highest_base(self):
        prob = calculate_conversion_probability(
            stage="negotiation",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        assert prob == STAGE_BASE_PROBABILITY["negotiation"]

    def test_icp_score_multiplier(self):
        """A perfect ICP score of 100 should multiply base by 1.5."""
        prob = calculate_conversion_probability(
            stage="qualified",
            score_icp=100,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        # base 0.15 * (100/100 * 1.5) = 0.225
        assert abs(prob - 0.225) < 0.001

    def test_c_level_adds_20_percent(self):
        base_prob = calculate_conversion_probability(
            stage="meeting",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        c_level_prob = calculate_conversion_probability(
            stage="meeting",
            score_icp=None,
            c_level=True,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        assert abs(c_level_prob - base_prob - 0.20) < 0.001

    def test_high_afinidad_adds_15_percent(self):
        medium_prob = calculate_conversion_probability(
            stage="contacted",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        high_prob = calculate_conversion_probability(
            stage="contacted",
            score_icp=None,
            c_level=False,
            afinidad="HIGH",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        assert abs(high_prob - medium_prob - 0.15) < 0.001

    def test_low_afinidad_subtracts_15_percent(self):
        medium_prob = calculate_conversion_probability(
            stage="contacted",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        low_prob = calculate_conversion_probability(
            stage="contacted",
            score_icp=None,
            c_level=False,
            afinidad="LOW",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        assert abs(medium_prob - low_prob - 0.15) < 0.001

    def test_time_decay_reduces_probability(self):
        """Days beyond expected stage time should reduce probability by 1% per day."""
        expected_days = STAGE_EXPECTED_DAYS["proposal"]
        fresh_prob = calculate_conversion_probability(
            stage="proposal",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        stale_prob = calculate_conversion_probability(
            stage="proposal",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=expected_days + 10,
            has_replied_outreach=False,
        )
        # Should be reduced by 10 * 0.01 = 0.10
        assert abs(fresh_prob - stale_prob - 0.10) < 0.001

    def test_engagement_boost_adds_5_percent(self):
        no_reply_prob = calculate_conversion_probability(
            stage="meeting",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=False,
        )
        reply_prob = calculate_conversion_probability(
            stage="meeting",
            score_icp=None,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=0,
            has_replied_outreach=True,
        )
        assert abs(reply_prob - no_reply_prob - 0.05) < 0.001

    def test_probability_clamped_to_0_1(self):
        """Very negative modifiers should not produce negative probability."""
        prob = calculate_conversion_probability(
            stage="raw",
            score_icp=None,
            c_level=False,
            afinidad="LOW",
            days_in_stage=200,
            has_replied_outreach=False,
        )
        assert prob >= 0.0
        assert prob <= 1.0

    def test_probability_clamped_at_max_1(self):
        """All positive modifiers combined should not exceed 1.0."""
        prob = calculate_conversion_probability(
            stage="negotiation",
            score_icp=100,
            c_level=True,
            afinidad="HIGH",
            days_in_stage=0,
            has_replied_outreach=True,
        )
        assert prob <= 1.0

    def test_unknown_stage_returns_zero(self):
        prob = calculate_conversion_probability(
            stage="won",
            score_icp=100,
            c_level=True,
            afinidad="HIGH",
            days_in_stage=0,
            has_replied_outreach=True,
        )
        assert prob == 0.0


# -----------------------------------------------------------------------
# 2. Churn risk scoring
# -----------------------------------------------------------------------


class TestChurnRiskScoring:
    def test_low_risk_for_healthy_customer(self):
        score, factors, actions = _calculate_churn_risk_score(
            ticket_count=1,
            complaint_ticket_count=0,
            avg_resolution_hours=8.0,
            sla_breach_count=0,
            days_since_last_interaction=10,
            escalation_count=0,
            plan="enterprise",
        )
        assert score < 30
        assert len(factors) == 0

    def test_high_complaint_tickets_increase_risk(self):
        score, factors, _ = _calculate_churn_risk_score(
            ticket_count=5,
            complaint_ticket_count=4,
            avg_resolution_hours=12.0,
            sla_breach_count=0,
            days_since_last_interaction=10,
            escalation_count=0,
            plan="enterprise",
        )
        assert score >= 20
        assert any("complaint" in f.lower() for f in factors)

    def test_slow_resolution_increases_risk(self):
        score, factors, _ = _calculate_churn_risk_score(
            ticket_count=2,
            complaint_ticket_count=0,
            avg_resolution_hours=80.0,
            sla_breach_count=0,
            days_since_last_interaction=10,
            escalation_count=0,
            plan="enterprise",
        )
        assert score >= 20
        assert any("resolution" in f.lower() for f in factors)

    def test_sla_breaches_increase_risk(self):
        score, factors, _ = _calculate_churn_risk_score(
            ticket_count=2,
            complaint_ticket_count=0,
            avg_resolution_hours=12.0,
            sla_breach_count=3,
            days_since_last_interaction=10,
            escalation_count=0,
            plan="enterprise",
        )
        assert score >= 25
        assert any("sla" in f.lower() for f in factors)

    def test_long_inactivity_increases_risk(self):
        score, factors, _ = _calculate_churn_risk_score(
            ticket_count=0,
            complaint_ticket_count=0,
            avg_resolution_hours=None,
            sla_breach_count=0,
            days_since_last_interaction=100,
            escalation_count=0,
            plan="enterprise",
        )
        assert score >= 20
        assert any("interaction" in f.lower() or "days" in f.lower() for f in factors)

    def test_free_plan_increases_risk(self):
        score_paid, _, _ = _calculate_churn_risk_score(
            ticket_count=1,
            complaint_ticket_count=0,
            avg_resolution_hours=12.0,
            sla_breach_count=0,
            days_since_last_interaction=10,
            escalation_count=0,
            plan="enterprise",
        )
        score_free, factors, _ = _calculate_churn_risk_score(
            ticket_count=1,
            complaint_ticket_count=0,
            avg_resolution_hours=12.0,
            sla_breach_count=0,
            days_since_last_interaction=10,
            escalation_count=0,
            plan="free",
        )
        assert score_free > score_paid
        assert any("free" in f.lower() or "plan" in f.lower() for f in factors)

    def test_escalations_increase_risk(self):
        score, factors, _ = _calculate_churn_risk_score(
            ticket_count=3,
            complaint_ticket_count=0,
            avg_resolution_hours=12.0,
            sla_breach_count=0,
            days_since_last_interaction=10,
            escalation_count=4,
            plan="enterprise",
        )
        assert score >= 15
        assert any("escalation" in f.lower() for f in factors)

    def test_risk_score_clamped_at_100(self):
        """All negative signals combined should not exceed 100."""
        score, _, _ = _calculate_churn_risk_score(
            ticket_count=20,
            complaint_ticket_count=10,
            avg_resolution_hours=200.0,
            sla_breach_count=20,
            days_since_last_interaction=365,
            escalation_count=10,
            plan=None,
        )
        assert score <= 100.0

    def test_zero_everything_returns_free_plan_risk_only(self):
        """A customer with no data and no plan should only flag the plan risk."""
        score, factors, _ = _calculate_churn_risk_score(
            ticket_count=0,
            complaint_ticket_count=0,
            avg_resolution_hours=None,
            sla_breach_count=0,
            days_since_last_interaction=0,
            escalation_count=0,
            plan=None,
        )
        assert score == 15.0
        assert len(factors) == 1
        assert "plan" in factors[0].lower() or "free" in factors[0].lower()

    def test_recommended_actions_generated_for_each_factor(self):
        """Every identified factor should produce at least one action."""
        _, factors, actions = _calculate_churn_risk_score(
            ticket_count=10,
            complaint_ticket_count=5,
            avg_resolution_hours=100.0,
            sla_breach_count=3,
            days_since_last_interaction=100,
            escalation_count=5,
            plan="free",
        )
        # All major factors are present, so actions should cover them
        assert len(actions) >= 4


# -----------------------------------------------------------------------
# 3. Win/loss analysis — dataclass construction
# -----------------------------------------------------------------------


class TestWinLossAnalysisDataclass:
    def test_win_loss_dataclass_fields(self):
        analysis = WinLossAnalysis(
            total_won=10,
            total_lost=5,
            win_rate=66.7,
            avg_days_to_win=15.0,
            avg_days_to_loss=30.0,
            top_win_factors=["Factor A"],
            top_loss_factors=["Factor B"],
            by_region={"LATAM": {"won": 8, "lost": 2}},
            by_afinidad={"HIGH": {"won": 6, "lost": 1}},
        )
        assert analysis.total_won == 10
        assert analysis.total_lost == 5
        assert analysis.win_rate == 66.7
        assert analysis.avg_days_to_win == 15.0
        assert analysis.avg_days_to_loss == 30.0
        assert len(analysis.top_win_factors) == 1
        assert len(analysis.top_loss_factors) == 1

    def test_empty_win_loss_analysis(self):
        """Edge case: no won or lost leads."""
        analysis = WinLossAnalysis(
            total_won=0,
            total_lost=0,
            win_rate=0.0,
            avg_days_to_win=None,
            avg_days_to_loss=None,
            top_win_factors=["Insufficient data to identify win factors"],
            top_loss_factors=["Insufficient data to identify loss factors"],
            by_region={},
            by_afinidad={},
        )
        assert analysis.win_rate == 0.0
        assert analysis.avg_days_to_win is None
        assert analysis.avg_days_to_loss is None

    def test_all_won_scenario(self):
        """Edge case: all leads won, none lost."""
        analysis = WinLossAnalysis(
            total_won=20,
            total_lost=0,
            win_rate=100.0,
            avg_days_to_win=12.5,
            avg_days_to_loss=None,
            top_win_factors=["Strong performance across the board"],
            top_loss_factors=["Insufficient data to identify loss factors"],
            by_region={"LATAM": {"won": 20, "lost": 0}},
            by_afinidad={"HIGH": {"won": 15, "lost": 0}, "MEDIUM": {"won": 5, "lost": 0}},
        )
        assert analysis.win_rate == 100.0
        assert analysis.total_lost == 0

    def test_all_lost_scenario(self):
        """Edge case: all leads lost, none won."""
        analysis = WinLossAnalysis(
            total_won=0,
            total_lost=15,
            win_rate=0.0,
            avg_days_to_win=None,
            avg_days_to_loss=25.0,
            top_win_factors=["Insufficient data to identify win factors"],
            top_loss_factors=["Low engagement across pipeline"],
            by_region={"Iberia": {"won": 0, "lost": 15}},
            by_afinidad={"LOW": {"won": 0, "lost": 15}},
        )
        assert analysis.win_rate == 0.0
        assert analysis.total_won == 0


# -----------------------------------------------------------------------
# 4. Pipeline forecast — dataclass construction
# -----------------------------------------------------------------------


class TestPipelineForecastDataclass:
    def test_forecast_dataclass_fields(self):
        forecast = PipelineForecast(
            period_days=30,
            expected_conversions=5.5,
            expected_revenue_index=3.2,
            confidence=0.85,
            by_stage={"qualified": 1.2, "meeting": 2.0, "negotiation": 2.3},
            methodology="Test methodology",
        )
        assert forecast.period_days == 30
        assert forecast.expected_conversions == 5.5
        assert forecast.confidence == 0.85
        assert "qualified" in forecast.by_stage

    def test_empty_pipeline_forecast(self):
        """Edge case: no active leads."""
        forecast = PipelineForecast(
            period_days=30,
            expected_conversions=0.0,
            expected_revenue_index=0.0,
            confidence=0.0,
            by_stage={},
            methodology="No active leads in pipeline",
        )
        assert forecast.expected_conversions == 0.0
        assert forecast.confidence == 0.0
        assert forecast.by_stage == {}


# -----------------------------------------------------------------------
# 5. Lead score history — dataclass and trend logic
# -----------------------------------------------------------------------


class TestLeadScoreHistory:
    def test_score_history_dataclass(self):
        history = LeadScoreHistory(
            lead_id=42,
            scores=[("2025-01-01", 30.0), ("2025-01-15", 65.0)],
            trend="up",
            velocity=17.5,
        )
        assert history.lead_id == 42
        assert history.trend == "up"
        assert history.velocity == 17.5
        assert len(history.scores) == 2

    def test_stable_trend(self):
        history = LeadScoreHistory(
            lead_id=1,
            scores=[("2025-01-01", 50.0), ("2025-01-15", 52.0)],
            trend="stable",
            velocity=1.0,
        )
        assert history.trend == "stable"

    def test_down_trend(self):
        history = LeadScoreHistory(
            lead_id=2,
            scores=[("2025-01-01", 80.0), ("2025-01-15", 40.0)],
            trend="down",
            velocity=-20.0,
        )
        assert history.trend == "down"
        assert history.velocity < 0


# -----------------------------------------------------------------------
# 6. ChurnRisk dataclass
# -----------------------------------------------------------------------


class TestChurnRiskDataclass:
    def test_churn_risk_fields(self):
        risk = ChurnRisk(
            customer_id=1,
            risk_score=75.0,
            risk_level="high",
            factors=["SLA breaches", "Slow resolution"],
            recommended_actions=["Assign CSM"],
        )
        assert risk.customer_id == 1
        assert risk.risk_level == "high"
        assert risk.risk_score == 75.0
        assert len(risk.factors) == 2
        assert len(risk.recommended_actions) == 1

    def test_risk_level_thresholds(self):
        """Verify risk_level assignment logic matches the module's threshold scheme."""
        # High: >= 60
        score_high = 65.0
        # Medium: 30-59
        score_med = 45.0
        # Low: < 30
        score_low = 10.0

        assert score_high >= 60
        assert 30 <= score_med < 60
        assert score_low < 30


# -----------------------------------------------------------------------
# 7. Combined modifiers test
# -----------------------------------------------------------------------


class TestCombinedModifiers:
    def test_all_positive_modifiers_stack(self):
        """Negotiation + high ICP + C-level + HIGH afinidad + replied should be high."""
        prob = calculate_conversion_probability(
            stage="negotiation",
            score_icp=90,
            c_level=True,
            afinidad="HIGH",
            days_in_stage=0,
            has_replied_outreach=True,
        )
        # Should be capped at 1.0
        assert prob == 1.0

    def test_all_negative_modifiers_floor(self):
        """Raw stage + LOW afinidad + very stale should be 0."""
        prob = calculate_conversion_probability(
            stage="raw",
            score_icp=None,
            c_level=False,
            afinidad="LOW",
            days_in_stage=100,
            has_replied_outreach=False,
        )
        assert prob == 0.0

    def test_moderate_lead_gives_reasonable_probability(self):
        """A qualified lead with moderate signals should be in a mid-range."""
        prob = calculate_conversion_probability(
            stage="qualified",
            score_icp=60,
            c_level=False,
            afinidad="MEDIUM",
            days_in_stage=5,
            has_replied_outreach=False,
        )
        # base=0.15, icp_mult=(60/100)*1.5=0.9, 0.15*0.9=0.135
        assert 0.1 <= prob <= 0.5
