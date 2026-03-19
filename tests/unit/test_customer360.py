"""Tests for Customer 360 scoring, risk assessment, and recommendation logic.

All tests exercise the pure-function layer (no database required) so they
run fast and deterministically.
"""

from datetime import datetime, timedelta

import pytest

from xcapitsff.core.customer360 import (
    Customer360,
    LeadInfo,
    LifetimeValue,
    OutreachSummary,
    SatisfactionIndicators,
    TicketSummary,
    _classify_lifetime_value,
    assess_churn_risk,
    calculate_engagement_score,
    generate_recommendations,
)


# -----------------------------------------------------------------------
# Helpers to build test fixtures
# -----------------------------------------------------------------------

_NOW = datetime.now(tz=None)


def _ticket(
    id: int = 1,
    subject: str = "Issue",
    status: str = "open",
    priority: str = "medium",
    created_at: datetime | None = None,
    resolved_at: datetime | None = None,
) -> TicketSummary:
    return TicketSummary(
        id=id,
        subject=subject,
        status=status,
        priority=priority,
        created_at=created_at or _NOW,
        resolved_at=resolved_at,
    )


def _outreach(
    id: int = 1,
    channel: str = "email",
    subject: str | None = "Hello",
    status: str = "sent",
    created_at: datetime | None = None,
) -> OutreachSummary:
    return OutreachSummary(
        id=id,
        channel=channel,
        subject=subject,
        status=status,
        created_at=created_at or _NOW,
    )


def _satisfaction(
    avg_hours: float | None = 12.0,
    escalations: int = 0,
    sla_breaches: int = 0,
    positive: bool = True,
) -> SatisfactionIndicators:
    return SatisfactionIndicators(
        avg_resolution_hours=avg_hours,
        escalation_count=escalations,
        sla_breach_count=sla_breaches,
        positive_signal=positive,
    )


def _c360(
    customer_id: int = 1,
    plan: str | None = "enterprise",
    tickets: list[TicketSummary] | None = None,
    outreach: list[OutreachSummary] | None = None,
    open_tickets: int = 0,
    engagement_score: float = 50.0,
    ltv: LifetimeValue = LifetimeValue.MEDIUM,
    satisfaction: SatisfactionIndicators | None = None,
    lead_info: LeadInfo | None = None,
    risk_indicators: list[str] | None = None,
) -> Customer360:
    tix = tickets or []
    out = outreach or []
    sat = satisfaction or _satisfaction()
    return Customer360(
        customer_id=customer_id,
        name="Test User",
        email="test@example.com",
        company="TestCo",
        region="LATAM",
        plan=plan,
        created_at=_NOW - timedelta(days=180),
        lead_info=lead_info,
        ticket_history=tix,
        open_tickets=open_tickets,
        total_tickets=len(tix),
        avg_resolution_hours=sat.avg_resolution_hours,
        satisfaction_indicators=sat,
        outreach_history=out,
        engagement_score=engagement_score,
        lifetime_value_indicator=ltv,
        risk_indicators=risk_indicators or [],
        recommendations=[],
    )


# -----------------------------------------------------------------------
# 1. Engagement score calculation
# -----------------------------------------------------------------------


class TestCalculateEngagementScore:
    def test_zero_with_no_data(self):
        assert calculate_engagement_score([], []) == 0.0

    def test_ticket_activity_contributes_up_to_40(self):
        tickets = [_ticket(id=i) for i in range(25)]
        score = calculate_engagement_score(tickets, [])
        # 25 tickets * 2 = 50, capped at 40; plus 20 recency bonus = 60
        assert score == 60.0

    def test_recency_bonus_adds_20_points(self):
        recent = _ticket(created_at=_NOW - timedelta(days=5))
        score = calculate_engagement_score([recent], [])
        # 1 ticket * 2 = 2 + recency 20 = 22
        assert score == 22.0

    def test_no_recency_bonus_for_old_tickets(self):
        old = _ticket(created_at=_NOW - timedelta(days=60))
        score = calculate_engagement_score([old], [])
        # 1 ticket * 2 = 2, no recency
        assert score == 2.0

    def test_outreach_replied_contributes_up_to_25(self):
        replies = [_outreach(id=i, status="replied") for i in range(10)]
        score = calculate_engagement_score([], replies)
        # 10 * 5 = 50 capped at 25
        assert score == 25.0

    def test_outreach_sent_contributes_up_to_15(self):
        sent = [_outreach(id=i, status="sent") for i in range(10)]
        score = calculate_engagement_score([], sent)
        # 10 * 3 = 30 capped at 15
        assert score == 15.0

    def test_combined_score_caps_at_100(self):
        tickets = [_ticket(id=i, created_at=_NOW) for i in range(30)]
        outreach = (
            [_outreach(id=i, status="replied") for i in range(10)]
            + [_outreach(id=100 + i, status="sent") for i in range(10)]
        )
        score = calculate_engagement_score(tickets, outreach)
        assert score == 100.0

    def test_draft_outreach_does_not_contribute(self):
        drafts = [_outreach(id=i, status="draft") for i in range(5)]
        score = calculate_engagement_score([], drafts)
        assert score == 0.0


# -----------------------------------------------------------------------
# 2. Lifetime-value classification
# -----------------------------------------------------------------------


class TestClassifyLifetimeValue:
    def test_premium_plan_is_high(self):
        assert _classify_lifetime_value("enterprise", 10.0, 1) == LifetimeValue.HIGH

    def test_pro_plan_is_high(self):
        assert _classify_lifetime_value("pro", 5.0, 0) == LifetimeValue.HIGH

    def test_mid_plan_high_engagement_is_high(self):
        assert _classify_lifetime_value("standard", 50.0, 3) == LifetimeValue.HIGH

    def test_mid_plan_low_engagement_is_medium(self):
        assert _classify_lifetime_value("growth", 20.0, 2) == LifetimeValue.MEDIUM

    def test_high_engagement_no_plan_is_medium(self):
        assert _classify_lifetime_value(None, 65.0, 5) == LifetimeValue.MEDIUM

    def test_many_tickets_moderate_engagement_is_medium(self):
        assert _classify_lifetime_value(None, 35.0, 6) == LifetimeValue.MEDIUM

    def test_low_everything_is_low(self):
        assert _classify_lifetime_value(None, 10.0, 1) == LifetimeValue.LOW

    def test_free_plan_low_engagement_is_low(self):
        assert _classify_lifetime_value("free", 5.0, 0) == LifetimeValue.LOW


# -----------------------------------------------------------------------
# 3. Churn risk assessment
# -----------------------------------------------------------------------


class TestAssessChurnRisk:
    def test_no_risk_for_healthy_customer(self):
        c = _c360(engagement_score=60.0, open_tickets=0)
        assert assess_churn_risk(c) == []

    def test_high_ticket_volume_flag(self):
        c = _c360(open_tickets=3)
        risks = assess_churn_risk(c)
        assert "high_ticket_volume" in risks

    def test_slow_resolutions_flag(self):
        c = _c360(satisfaction=_satisfaction(avg_hours=72.0))
        risks = assess_churn_risk(c)
        assert "slow_resolutions" in risks

    def test_sla_breaches_flag(self):
        c = _c360(satisfaction=_satisfaction(sla_breaches=2))
        risks = assess_churn_risk(c)
        assert "sla_breaches" in risks

    def test_frequent_escalations_flag(self):
        c = _c360(satisfaction=_satisfaction(escalations=3))
        risks = assess_churn_risk(c)
        assert "frequent_escalations" in risks

    def test_low_engagement_flag(self):
        c = _c360(plan="enterprise", engagement_score=10.0)
        risks = assess_churn_risk(c)
        assert "low_engagement" in risks

    def test_approaching_churn_flag(self):
        c = _c360(engagement_score=15.0, open_tickets=2)
        risks = assess_churn_risk(c)
        assert "approaching_churn" in risks

    def test_inactive_customer_flag(self):
        old_ticket = _ticket(created_at=_NOW - timedelta(days=365))
        c = _c360(
            engagement_score=0.0,
            tickets=[old_ticket],
            open_tickets=0,
            plan=None,
        )
        risks = assess_churn_risk(c)
        assert "inactive_customer" in risks

    def test_multiple_risks_combine(self):
        c = _c360(
            plan="enterprise",
            engagement_score=10.0,
            open_tickets=5,
            satisfaction=_satisfaction(avg_hours=100.0, escalations=3, sla_breaches=2),
        )
        risks = assess_churn_risk(c)
        assert len(risks) >= 4


# -----------------------------------------------------------------------
# 4. Recommendation generation
# -----------------------------------------------------------------------


class TestGenerateRecommendations:
    def test_no_recommendations_for_healthy_customer(self):
        c = _c360(engagement_score=50.0, open_tickets=0)
        # Ensure no risk flags
        c.risk_indicators = []
        recs = generate_recommendations(c)
        # May still get positive recs, but no risk-based ones
        for r in recs:
            assert "churn" not in r.lower()
            assert "escalat" not in r.lower()

    def test_high_ticket_volume_recommendation(self):
        c = _c360()
        c.risk_indicators = ["high_ticket_volume"]
        recs = generate_recommendations(c)
        assert any("check-in" in r.lower() for r in recs)

    def test_slow_resolutions_recommendation(self):
        c = _c360()
        c.risk_indicators = ["slow_resolutions"]
        recs = generate_recommendations(c)
        assert any("senior support" in r.lower() for r in recs)

    def test_sla_breaches_recommendation(self):
        c = _c360()
        c.risk_indicators = ["sla_breaches"]
        recs = generate_recommendations(c)
        assert any("sla" in r.lower() for r in recs)

    def test_approaching_churn_recommendation(self):
        c = _c360()
        c.risk_indicators = ["approaching_churn"]
        recs = generate_recommendations(c)
        assert any("churn" in r.lower() for r in recs)

    def test_upsell_recommendation_for_engaged_vip(self):
        c = _c360(
            ltv=LifetimeValue.HIGH,
            engagement_score=80.0,
            open_tickets=0,
        )
        c.risk_indicators = []
        recs = generate_recommendations(c)
        assert any("upsell" in r.lower() for r in recs)

    def test_case_study_recommendation_for_high_engagement(self):
        c = _c360(engagement_score=75.0, open_tickets=0)
        c.risk_indicators = []
        recs = generate_recommendations(c)
        assert any("case-study" in r.lower() or "referral" in r.lower() for r in recs)

    def test_cross_sell_for_high_affinity_lead(self):
        lead = LeadInfo(
            lead_id=1,
            score_icp=90.0,
            stage="won",
            afinidad="HIGH",
            contact_name="Ana",
            company_name="Corp",
            created_at=_NOW,
        )
        c = _c360(lead_info=lead, engagement_score=50.0)
        c.risk_indicators = []
        recs = generate_recommendations(c)
        assert any("cross-sell" in r.lower() for r in recs)


# -----------------------------------------------------------------------
# 5. Edge cases & integration of scoring pipeline
# -----------------------------------------------------------------------


class TestEdgeCases:
    def test_engagement_score_is_float(self):
        score = calculate_engagement_score([_ticket()], [_outreach(status="replied")])
        assert isinstance(score, float)

    def test_engagement_score_within_bounds(self):
        score = calculate_engagement_score(
            [_ticket(id=i) for i in range(100)],
            [_outreach(id=i, status="replied") for i in range(100)],
        )
        assert 0 <= score <= 100

    def test_customer360_dataclass_fields(self):
        c = _c360()
        assert hasattr(c, "customer_id")
        assert hasattr(c, "engagement_score")
        assert hasattr(c, "lifetime_value_indicator")
        assert hasattr(c, "risk_indicators")
        assert hasattr(c, "recommendations")

    def test_risk_then_recommendations_pipeline(self):
        """Verify that risks feed into recommendations end-to-end."""
        c = _c360(
            plan="enterprise",
            engagement_score=5.0,
            open_tickets=4,
            satisfaction=_satisfaction(avg_hours=80.0, escalations=4, sla_breaches=3),
        )
        c.risk_indicators = assess_churn_risk(c)
        c.recommendations = generate_recommendations(c)
        # Should have multiple risks and at least as many recommendations
        assert len(c.risk_indicators) >= 3
        assert len(c.recommendations) >= 3

    def test_lifetime_value_with_none_plan_and_zero_engagement(self):
        ltv = _classify_lifetime_value(None, 0.0, 0)
        assert ltv == LifetimeValue.LOW

    def test_satisfaction_positive_signal_logic(self):
        good = _satisfaction(avg_hours=10.0, escalations=0, sla_breaches=0, positive=True)
        assert good.positive_signal is True
        bad = _satisfaction(avg_hours=50.0, escalations=2, sla_breaches=1, positive=False)
        assert bad.positive_signal is False
