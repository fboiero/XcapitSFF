"""Tests for billing, pricing, subscription lifecycle, and usage metering."""

import pytest
from datetime import timedelta, datetime, timezone

from xcapitsff.core.billing import (
    BillingManager,
    ENTERPRISE_PLAN,
    FREE_PLAN,
    PLANS,
    PRO_PLAN,
    PricingPlan,
    Subscription,
    TRACKED_METRICS,
    UsageMeter,
    _PLAN_TIER_ORDER,
)


# ---------------------------------------------------------------------------
# Plan definitions & pricing
# ---------------------------------------------------------------------------


class TestPlanDefinitions:
    """Verify plan constants are configured correctly."""

    def test_free_plan_price_is_zero(self):
        assert FREE_PLAN.price_monthly_usd == 0.0
        assert FREE_PLAN.price_annual_usd == 0.0

    def test_pro_plan_monthly_price(self):
        assert PRO_PLAN.price_monthly_usd == 99.0

    def test_pro_plan_annual_price(self):
        assert PRO_PLAN.price_annual_usd == 79.0

    def test_enterprise_plan_monthly_price(self):
        assert ENTERPRISE_PLAN.price_monthly_usd == 499.0

    def test_enterprise_plan_annual_price(self):
        assert ENTERPRISE_PLAN.price_annual_usd == 399.0

    def test_free_plan_limits(self):
        assert FREE_PLAN.limits["leads"] == 100
        assert FREE_PLAN.limits["tickets"] == 50
        assert FREE_PLAN.limits["users"] == 2
        assert FREE_PLAN.limits["api_calls"] == 1_000

    def test_pro_plan_limits(self):
        assert PRO_PLAN.limits["leads"] == 5_000
        assert PRO_PLAN.limits["tickets"] == 500
        assert PRO_PLAN.limits["users"] == 10
        assert PRO_PLAN.limits["api_calls"] == 50_000

    def test_enterprise_plan_unlimited(self):
        for key in ("leads", "tickets", "users", "api_calls"):
            assert ENTERPRISE_PLAN.limits[key] == -1

    def test_plans_dict_has_all_tiers(self):
        assert set(PLANS.keys()) == {"free", "pro", "enterprise"}

    def test_free_plan_features_include_basic_scoring(self):
        assert "basic_scoring" in FREE_PLAN.features

    def test_pro_plan_features_include_advanced_scoring(self):
        assert "advanced_scoring" in PRO_PLAN.features
        assert "crm_integration" in PRO_PLAN.features

    def test_enterprise_features_superset(self):
        """Enterprise should include every feature from free and pro."""
        for f in FREE_PLAN.features:
            assert f in ENTERPRISE_PLAN.features
        for f in PRO_PLAN.features:
            assert f in ENTERPRISE_PLAN.features

    def test_enterprise_exclusive_features(self):
        assert "dedicated_agent" in ENTERPRISE_PLAN.features
        assert "sla_guarantee" in ENTERPRISE_PLAN.features
        assert "white_label" in ENTERPRISE_PLAN.features

    def test_get_all_plans_returns_three(self):
        plans = BillingManager.get_all_plans()
        assert len(plans) == 3
        ids = [p.plan_id for p in plans]
        assert ids == ["free", "pro", "enterprise"]

    def test_plan_tier_order(self):
        assert _PLAN_TIER_ORDER["free"] < _PLAN_TIER_ORDER["pro"]
        assert _PLAN_TIER_ORDER["pro"] < _PLAN_TIER_ORDER["enterprise"]


# ---------------------------------------------------------------------------
# Subscription lifecycle
# ---------------------------------------------------------------------------


class TestSubscriptionLifecycle:
    """Create, upgrade, downgrade, cancel subscriptions."""

    def setup_method(self):
        self.bm = BillingManager()

    def test_create_subscription_with_trial(self):
        sub = self.bm.create_subscription("t1", "free", trial_days=14)
        assert sub.tenant_id == "t1"
        assert sub.plan_id == "free"
        assert sub.status == "trial"
        assert sub.trial_ends_at is not None
        diff = sub.trial_ends_at - sub.started_at
        assert diff >= timedelta(days=13)

    def test_create_subscription_no_trial(self):
        sub = self.bm.create_subscription("t2", "pro", trial_days=0)
        assert sub.status == "active"
        assert sub.trial_ends_at is None

    def test_get_subscription_returns_none_for_unknown(self):
        assert self.bm.get_subscription("unknown") is None

    def test_get_subscription_after_create(self):
        self.bm.create_subscription("t1", "pro")
        sub = self.bm.get_subscription("t1")
        assert sub is not None
        assert sub.plan_id == "pro"

    def test_upgrade_free_to_pro(self):
        self.bm.create_subscription("t1", "free")
        sub = self.bm.upgrade_plan("t1", "pro")
        assert sub.plan_id == "pro"
        assert sub.status == "active"

    def test_upgrade_pro_to_enterprise(self):
        self.bm.create_subscription("t1", "pro", trial_days=0)
        sub = self.bm.upgrade_plan("t1", "enterprise")
        assert sub.plan_id == "enterprise"

    def test_upgrade_to_same_raises(self):
        self.bm.create_subscription("t1", "pro")
        with pytest.raises(ValueError, match="not an upgrade"):
            self.bm.upgrade_plan("t1", "pro")

    def test_upgrade_to_lower_raises(self):
        self.bm.create_subscription("t1", "pro")
        with pytest.raises(ValueError, match="not an upgrade"):
            self.bm.upgrade_plan("t1", "free")

    def test_downgrade_enterprise_to_pro(self):
        self.bm.create_subscription("t1", "enterprise", trial_days=0)
        sub = self.bm.downgrade_plan("t1", "pro")
        assert sub.plan_id == "pro"

    def test_downgrade_to_higher_raises(self):
        self.bm.create_subscription("t1", "free")
        with pytest.raises(ValueError, match="not a downgrade"):
            self.bm.downgrade_plan("t1", "pro")

    def test_cancel_subscription(self):
        self.bm.create_subscription("t1", "pro")
        sub = self.bm.cancel_subscription("t1")
        assert sub.status == "cancelled"
        assert sub.cancel_at is not None

    def test_cancel_nonexistent_raises(self):
        with pytest.raises(ValueError, match="No subscription"):
            self.bm.cancel_subscription("nope")

    def test_upgrade_cancelled_raises(self):
        self.bm.create_subscription("t1", "free")
        self.bm.cancel_subscription("t1")
        with pytest.raises(ValueError, match="Cannot upgrade a cancelled"):
            self.bm.upgrade_plan("t1", "pro")

    def test_downgrade_cancelled_raises(self):
        self.bm.create_subscription("t1", "pro")
        self.bm.cancel_subscription("t1")
        with pytest.raises(ValueError, match="Cannot downgrade a cancelled"):
            self.bm.downgrade_plan("t1", "free")

    def test_create_subscription_invalid_plan_raises(self):
        with pytest.raises(ValueError, match="Unknown plan"):
            self.bm.create_subscription("t1", "platinum")

    def test_upgrade_invalid_plan_raises(self):
        self.bm.create_subscription("t1", "free")
        with pytest.raises(ValueError, match="Unknown plan"):
            self.bm.upgrade_plan("t1", "platinum")

    def test_upgrade_nonexistent_tenant_raises(self):
        with pytest.raises(ValueError, match="No subscription"):
            self.bm.upgrade_plan("ghost", "pro")


# ---------------------------------------------------------------------------
# Usage metering
# ---------------------------------------------------------------------------


class TestUsageMeter:
    """Record usage, check quotas, reset counters."""

    def setup_method(self):
        self.meter = UsageMeter()

    def test_record_and_get_usage(self):
        self.meter.record_usage("t1", "api_calls", 5)
        usage = self.meter.get_usage("t1")
        assert usage["api_calls"] == 5

    def test_incremental_recording(self):
        self.meter.record_usage("t1", "api_calls", 3)
        self.meter.record_usage("t1", "api_calls", 7)
        assert self.meter.get_usage("t1")["api_calls"] == 10

    def test_default_amount_is_one(self):
        self.meter.record_usage("t1", "leads_created")
        assert self.meter.get_usage("t1")["leads_created"] == 1

    def test_unknown_metric_raises(self):
        with pytest.raises(ValueError, match="Unknown metric"):
            self.meter.record_usage("t1", "bogus_metric")

    def test_get_usage_unknown_tenant_returns_zeros(self):
        usage = self.meter.get_usage("unknown")
        for m in TRACKED_METRICS:
            assert usage[m] == 0

    def test_check_quota_within_limit(self):
        self.meter.record_usage("t1", "api_calls", 500)
        within, used, limit = self.meter.check_quota("t1", "api_calls", FREE_PLAN)
        assert within is True
        assert used == 500
        assert limit == 1_000

    def test_check_quota_exceeded(self):
        self.meter.record_usage("t1", "api_calls", 1_001)
        within, used, limit = self.meter.check_quota("t1", "api_calls", FREE_PLAN)
        assert within is False
        assert used == 1_001
        assert limit == 1_000

    def test_check_quota_unlimited(self):
        self.meter.record_usage("t1", "api_calls", 999_999)
        within, used, limit = self.meter.check_quota(
            "t1", "api_calls", ENTERPRISE_PLAN
        )
        assert within is True
        assert limit == -1

    def test_check_quota_leads_created_maps_to_leads_limit(self):
        self.meter.record_usage("t1", "leads_created", 50)
        within, used, limit = self.meter.check_quota(
            "t1", "leads_created", FREE_PLAN
        )
        assert within is True
        assert limit == 100  # FREE_PLAN.limits["leads"]

    def test_reset_monthly_usage(self):
        self.meter.record_usage("t1", "api_calls", 500)
        self.meter.reset_monthly_usage("t1")
        usage = self.meter.get_usage("t1")
        assert usage["api_calls"] == 0

    def test_separate_tenants(self):
        self.meter.record_usage("t1", "api_calls", 10)
        self.meter.record_usage("t2", "api_calls", 20)
        assert self.meter.get_usage("t1")["api_calls"] == 10
        assert self.meter.get_usage("t2")["api_calls"] == 20

    def test_tracked_metrics_list(self):
        expected = {
            "api_calls",
            "leads_created",
            "tickets_created",
            "outreach_sent",
            "agent_calls",
            "exports",
        }
        assert set(TRACKED_METRICS) == expected

    def test_check_quota_no_plan_returns_unlimited(self):
        self.meter.record_usage("t1", "api_calls", 999)
        within, used, limit = self.meter.check_quota("t1", "api_calls")
        assert within is True
        assert limit == -1


# ---------------------------------------------------------------------------
# Feature access
# ---------------------------------------------------------------------------


class TestFeatureAccess:
    """Verify feature gating per plan."""

    def setup_method(self):
        self.bm = BillingManager()

    def test_free_has_basic_scoring(self):
        self.bm.create_subscription("t1", "free")
        assert self.bm.check_feature_access("t1", "basic_scoring") is True

    def test_free_lacks_advanced_scoring(self):
        self.bm.create_subscription("t1", "free")
        assert self.bm.check_feature_access("t1", "advanced_scoring") is False

    def test_pro_has_crm_integration(self):
        self.bm.create_subscription("t1", "pro")
        assert self.bm.check_feature_access("t1", "crm_integration") is True

    def test_enterprise_has_white_label(self):
        self.bm.create_subscription("t1", "enterprise")
        assert self.bm.check_feature_access("t1", "white_label") is True

    def test_cancelled_returns_false(self):
        self.bm.create_subscription("t1", "pro")
        self.bm.cancel_subscription("t1")
        assert self.bm.check_feature_access("t1", "advanced_scoring") is False

    def test_unknown_tenant_returns_false(self):
        assert self.bm.check_feature_access("ghost", "basic_scoring") is False

    def test_nonexistent_feature_returns_false(self):
        self.bm.create_subscription("t1", "enterprise")
        assert self.bm.check_feature_access("t1", "teleportation") is False


# ---------------------------------------------------------------------------
# Trial period logic
# ---------------------------------------------------------------------------


class TestTrialPeriod:
    """Ensure trial dates are set correctly."""

    def test_trial_ends_at_is_14_days(self):
        bm = BillingManager()
        sub = bm.create_subscription("t1", "pro", trial_days=14)
        assert sub.trial_ends_at is not None
        delta = sub.trial_ends_at - sub.started_at
        assert delta == timedelta(days=14)

    def test_trial_status(self):
        bm = BillingManager()
        sub = bm.create_subscription("t1", "pro", trial_days=7)
        assert sub.status == "trial"

    def test_no_trial_status_is_active(self):
        bm = BillingManager()
        sub = bm.create_subscription("t1", "pro", trial_days=0)
        assert sub.status == "active"
        assert sub.trial_ends_at is None

    def test_trial_upgrade_changes_status_to_active(self):
        bm = BillingManager()
        sub = bm.create_subscription("t1", "free", trial_days=14)
        assert sub.status == "trial"
        upgraded = bm.upgrade_plan("t1", "pro")
        assert upgraded.status == "active"


# ---------------------------------------------------------------------------
# Invoice preview
# ---------------------------------------------------------------------------


class TestInvoicePreview:
    """Invoice preview returns correct data."""

    def test_invoice_preview_basic(self):
        bm = BillingManager()
        bm.create_subscription("t1", "pro", trial_days=0)
        preview = bm.get_invoice_preview("t1")
        assert preview["plan"] == "pro"
        assert preview["amount_due_usd"] == 99.0
        assert preview["tenant_id"] == "t1"

    def test_invoice_preview_includes_usage(self):
        meter = UsageMeter()
        bm = BillingManager(usage_meter=meter)
        bm.create_subscription("t1", "pro", trial_days=0)
        meter.record_usage("t1", "api_calls", 42)
        preview = bm.get_invoice_preview("t1")
        assert preview["usage"]["api_calls"] == 42

    def test_invoice_preview_unknown_tenant_raises(self):
        bm = BillingManager()
        with pytest.raises(ValueError, match="No subscription"):
            bm.get_invoice_preview("ghost")

    def test_invoice_preview_free_plan_zero(self):
        bm = BillingManager()
        bm.create_subscription("t1", "free", trial_days=0)
        preview = bm.get_invoice_preview("t1")
        assert preview["amount_due_usd"] == 0.0

    def test_invoice_preview_has_period_dates(self):
        bm = BillingManager()
        bm.create_subscription("t1", "pro", trial_days=0)
        preview = bm.get_invoice_preview("t1")
        assert preview["current_period_start"] is not None
        assert preview["current_period_end"] is not None
