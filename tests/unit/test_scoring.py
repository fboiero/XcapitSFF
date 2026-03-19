"""Tests for the ICP scoring engine (multi-factor weighted model).

Covers:
- All per-factor scoring functions (region, c_level, afinidad, engagement, company_fit)
- Composite scoring via score_lead
- Classification thresholds and confidence
- Batch scoring with statistics
- Score recalculation (EMA)
- Backward-compatible calculate_icp_score wrapper
- Edge cases (missing data, boundary values, custom weights)
"""

import math

from xcapitsff.sales.scoring import (
    BatchScoringResult,
    FactorBreakdown,
    ScoringResult,
    WEIGHTS,
    calculate_icp_score,
    classify_lead,
    recalculate_score,
    score_afinidad,
    score_c_level,
    score_company_fit,
    score_engagement,
    score_lead,
    score_leads_batch,
    score_region,
    segment_leads,
    should_auto_qualify,
)


# -----------------------------------------------------------------------
# 1. score_region
# -----------------------------------------------------------------------


class TestScoreRegion:
    def test_latam_highest(self):
        assert score_region("LATAM") == 90.0

    def test_iberia_mid(self):
        assert score_region("Iberia") == 60.0

    def test_iberia_case_insensitive(self):
        assert score_region("iberia") == 60.0

    def test_other_region_baseline(self):
        assert score_region("North America") == 30.0

    def test_empty_string(self):
        assert score_region("") == 30.0

    def test_whitespace_handling(self):
        assert score_region("  LATAM  ") == 90.0


# -----------------------------------------------------------------------
# 2. score_c_level
# -----------------------------------------------------------------------


class TestScoreCLevel:
    def test_c_level_true(self):
        assert score_c_level(True) == 100.0

    def test_c_level_false(self):
        assert score_c_level(False) == 30.0


# -----------------------------------------------------------------------
# 3. score_afinidad
# -----------------------------------------------------------------------


class TestScoreAfinidad:
    def test_high(self):
        assert score_afinidad("HIGH") == 100.0

    def test_medium(self):
        assert score_afinidad("MEDIUM") == 50.0

    def test_low(self):
        assert score_afinidad("LOW") == 10.0

    def test_unknown_defaults_to_low(self):
        assert score_afinidad("UNKNOWN") == 10.0

    def test_case_insensitive(self):
        assert score_afinidad("high") == 100.0


# -----------------------------------------------------------------------
# 4. score_engagement
# -----------------------------------------------------------------------


class TestScoreEngagement:
    def test_zero_interactions_unknown_days(self):
        """No interactions and unknown recency -> 0 * 0.5 = 0."""
        assert score_engagement(0, None) == 0.0

    def test_max_interactions_recent(self):
        """10+ interactions, contacted today -> 100."""
        assert score_engagement(15, 0) == 100.0

    def test_moderate_interactions_no_decay(self):
        """5 interactions, contacted today -> 50."""
        assert score_engagement(5, 0) == 50.0

    def test_decay_applies(self):
        """5 interactions, 23 days ago -> half-life decay ~0.50."""
        result = score_engagement(5, 23)
        expected = 50.0 * math.exp(-0.03 * 23)
        assert abs(result - round(expected, 2)) < 0.01

    def test_very_stale_lead(self):
        """Even with many interactions, 200 days of silence kills the score."""
        result = score_engagement(10, 200)
        assert result < 1.0

    def test_negative_interactions_clamped(self):
        """Negative interaction count treated as zero."""
        assert score_engagement(-5, 0) == 0.0

    def test_days_since_last_none_moderate_penalty(self):
        """When days_since_last is None, decay factor is 0.5."""
        result = score_engagement(10, None)
        assert result == 50.0  # 100 * 0.5


# -----------------------------------------------------------------------
# 5. score_company_fit
# -----------------------------------------------------------------------


class TestScoreCompanyFit:
    def test_none_returns_midpoint(self):
        assert score_company_fit(None) == 50.0

    def test_normal_value(self):
        assert score_company_fit(75.0) == 75.0

    def test_clamp_above_100(self):
        assert score_company_fit(120.0) == 100.0

    def test_clamp_below_0(self):
        assert score_company_fit(-10.0) == 0.0

    def test_zero(self):
        assert score_company_fit(0.0) == 0.0

    def test_boundary_100(self):
        assert score_company_fit(100.0) == 100.0


# -----------------------------------------------------------------------
# 6. classify_lead
# -----------------------------------------------------------------------


class TestClassifyLead:
    def test_hot_boundary(self):
        assert classify_lead(70) == "hot"

    def test_hot_above(self):
        assert classify_lead(100) == "hot"

    def test_warm_boundary(self):
        assert classify_lead(45) == "warm"

    def test_warm_upper(self):
        assert classify_lead(69.9) == "warm"

    def test_cool_boundary(self):
        assert classify_lead(25) == "cool"

    def test_cool_upper(self):
        assert classify_lead(44.9) == "cool"

    def test_cold(self):
        assert classify_lead(24.9) == "cold"

    def test_cold_zero(self):
        assert classify_lead(0) == "cold"


# -----------------------------------------------------------------------
# 7. score_lead (composite scoring)
# -----------------------------------------------------------------------


class TestScoreLead:
    def test_returns_scoring_result(self):
        result = score_lead(region="LATAM", c_level=True, afinidad="HIGH")
        assert isinstance(result, ScoringResult)

    def test_ideal_lead_is_hot(self):
        """LATAM, C-level, HIGH affinity, good engagement, high manual score."""
        result = score_lead(
            region="LATAM",
            c_level=True,
            afinidad="HIGH",
            interactions=10,
            days_since_last=1,
            score_icp_manual=95,
        )
        assert result.classification == "hot"
        assert result.score >= 70

    def test_weak_lead_is_cold(self):
        """Other region, not C-level, LOW affinity, no engagement, no fit."""
        result = score_lead(
            region="Other",
            c_level=False,
            afinidad="LOW",
            interactions=0,
            days_since_last=None,
            score_icp_manual=None,
        )
        assert result.classification == "cold"
        assert result.score < 25

    def test_factor_breakdown_has_five_factors(self):
        result = score_lead()
        assert len(result.factor_breakdown) == 5
        factor_names = {fb.factor for fb in result.factor_breakdown}
        assert factor_names == {"region", "c_level", "afinidad", "engagement", "company_fit"}

    def test_weighted_scores_sum_to_composite(self):
        result = score_lead(region="LATAM", c_level=True, afinidad="HIGH")
        total = sum(fb.weighted_score for fb in result.factor_breakdown)
        assert abs(result.score - round(total, 1)) <= 0.1

    def test_score_clamped_to_100(self):
        """Even with all-max factors, score should not exceed 100."""
        result = score_lead(
            region="LATAM",
            c_level=True,
            afinidad="HIGH",
            interactions=20,
            days_since_last=0,
            score_icp_manual=100,
        )
        assert result.score <= 100.0

    def test_confidence_increases_with_data(self):
        """More data -> higher confidence."""
        minimal = score_lead(region="LATAM", c_level=False, afinidad="LOW")
        full = score_lead(
            region="LATAM",
            c_level=True,
            afinidad="HIGH",
            interactions=5,
            days_since_last=3,
            score_icp_manual=80,
        )
        assert full.confidence > minimal.confidence

    def test_recommendations_present(self):
        result = score_lead()
        assert len(result.recommendations) > 0

    def test_custom_weights(self):
        """Using custom weights should change the composite score."""
        default_result = score_lead(region="LATAM", c_level=True, afinidad="HIGH")
        custom_weights = {
            "region": 0.50,
            "c_level": 0.10,
            "afinidad": 0.10,
            "engagement": 0.10,
            "company_fit": 0.20,
        }
        custom_result = score_lead(
            region="LATAM", c_level=True, afinidad="HIGH", weights=custom_weights
        )
        # Scores should differ because region is heavily weighted
        assert default_result.score != custom_result.score


# -----------------------------------------------------------------------
# 8. Batch scoring
# -----------------------------------------------------------------------


class TestScoreLeadsBatch:
    def test_empty_batch(self):
        result = score_leads_batch([])
        assert isinstance(result, BatchScoringResult)
        assert result.total == 0
        assert result.mean_score == 0.0

    def test_single_lead_batch(self):
        leads = [{"region": "LATAM", "c_level": True, "afinidad": "HIGH"}]
        result = score_leads_batch(leads)
        assert result.total == 1
        assert result.mean_score == result.median_score
        assert result.std_dev == 0.0

    def test_multiple_leads_statistics(self):
        leads = [
            {"region": "LATAM", "c_level": True, "afinidad": "HIGH"},
            {"region": "Other", "c_level": False, "afinidad": "LOW"},
            {"region": "Iberia", "c_level": False, "afinidad": "MEDIUM"},
        ]
        result = score_leads_batch(leads)
        assert result.total == 3
        assert result.mean_score > 0
        assert result.std_dev > 0
        assert sum(result.distribution.values()) == 3

    def test_distribution_buckets(self):
        leads = [
            {"region": "LATAM", "c_level": True, "afinidad": "HIGH",
             "interactions": 10, "days_since_last": 0, "score_icp_manual": 90},
            {"region": "Other", "c_level": False, "afinidad": "LOW"},
        ]
        result = score_leads_batch(leads)
        # First should be hot, second cold
        assert result.distribution["hot"] >= 1
        assert result.distribution["cold"] >= 1


# -----------------------------------------------------------------------
# 9. Score recalculation (EMA)
# -----------------------------------------------------------------------


class TestRecalculateScore:
    def test_blends_existing_and_new(self):
        """EMA should blend old and new scores."""
        result = recalculate_score(
            existing_score=80.0,
            new_data={"region": "Other", "c_level": False, "afinidad": "LOW"},
            alpha=0.4,
        )
        # New score would be low; blended should be between new and 80
        assert result.score < 80.0
        assert result.score > 0.0

    def test_alpha_1_ignores_existing(self):
        """Alpha=1 means fully trust new data."""
        new_data = {"region": "LATAM", "c_level": True, "afinidad": "HIGH"}
        pure_new = score_lead(**new_data)
        result = recalculate_score(existing_score=10.0, new_data=new_data, alpha=1.0)
        assert result.score == pure_new.score

    def test_alpha_0_keeps_existing(self):
        """Alpha=0 means fully trust existing score."""
        result = recalculate_score(
            existing_score=75.0,
            new_data={"region": "Other", "c_level": False, "afinidad": "LOW"},
            alpha=0.0,
        )
        assert result.score == 75.0

    def test_returns_scoring_result(self):
        result = recalculate_score(
            existing_score=50.0,
            new_data={"region": "LATAM", "c_level": False, "afinidad": "MEDIUM"},
        )
        assert isinstance(result, ScoringResult)
        assert result.classification in ("hot", "warm", "cool", "cold")


# -----------------------------------------------------------------------
# 10. Backward-compatible calculate_icp_score
# -----------------------------------------------------------------------


class TestCalculateIcpScoreBackcompat:
    def test_basic_call_returns_float(self):
        score = calculate_icp_score(region="LATAM", c_level=True, afinidad="HIGH")
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_with_existing_score_blends(self):
        """When existing_score is provided, result should be blended."""
        without = calculate_icp_score(region="LATAM", c_level=True, afinidad="HIGH")
        with_existing = calculate_icp_score(
            region="LATAM", c_level=True, existing_score=50.0, afinidad="HIGH"
        )
        # Blended result should differ from pure new score
        assert with_existing != without

    def test_existing_score_zero_treated_as_absent(self):
        """existing_score=0 should not trigger blending (matches legacy)."""
        no_existing = calculate_icp_score(region="LATAM", c_level=True, afinidad="HIGH")
        zero_existing = calculate_icp_score(
            region="LATAM", c_level=True, existing_score=0, afinidad="HIGH"
        )
        assert no_existing == zero_existing

    def test_defaults(self):
        """Calling with defaults should not raise."""
        score = calculate_icp_score(region="LATAM", c_level=False)
        assert isinstance(score, float)


# -----------------------------------------------------------------------
# 11. WEIGHTS configuration
# -----------------------------------------------------------------------


class TestWeightsConfig:
    def test_weights_sum_to_one(self):
        assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9

    def test_all_weights_positive(self):
        for k, v in WEIGHTS.items():
            assert v > 0, f"Weight for {k} should be positive"


# -----------------------------------------------------------------------
# 12. Edge cases
# -----------------------------------------------------------------------


class TestEdgeCases:
    def test_score_lead_all_defaults(self):
        """score_lead with no arguments should not raise."""
        result = score_lead()
        assert 0 <= result.score <= 100

    def test_very_high_interactions_saturates(self):
        """Interaction score saturates at 100 (before decay)."""
        assert score_engagement(1000, 0) == 100.0

    def test_engagement_with_zero_days(self):
        """days_since_last=0 means contacted today, no decay."""
        assert score_engagement(10, 0) == 100.0

    def test_factor_breakdown_is_frozen(self):
        """FactorBreakdown instances are immutable (frozen dataclass)."""
        fb = FactorBreakdown(factor="test", raw_score=50, weight=0.2, weighted_score=10)
        try:
            fb.factor = "changed"  # type: ignore[misc]
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass  # Expected
