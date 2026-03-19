"""Tests for feature flags."""

from xcapitsff.core.feature_flags import FeatureFlagManager, FeatureStatus


def test_free_plan_basic_features():
    fm = FeatureFlagManager()
    assert fm.is_enabled("icp_scoring", "free") is True
    assert fm.is_enabled("ticket_routing", "free") is True
    assert fm.is_enabled("knowledge_base", "free") is True
    assert fm.is_enabled("api_access", "free") is True


def test_free_plan_no_advanced():
    fm = FeatureFlagManager()
    assert fm.is_enabled("advanced_scoring", "free") is False
    assert fm.is_enabled("outreach_sequences", "free") is False
    assert fm.is_enabled("ai_agents", "free") is False
    assert fm.is_enabled("crm_integration", "free") is False


def test_pro_plan_includes_advanced():
    fm = FeatureFlagManager()
    assert fm.is_enabled("advanced_scoring", "pro") is True
    assert fm.is_enabled("outreach_sequences", "pro") is True
    assert fm.is_enabled("ab_testing", "pro") is True
    assert fm.is_enabled("ai_agents", "pro") is True
    assert fm.is_enabled("crm_integration", "pro") is True


def test_enterprise_includes_all():
    fm = FeatureFlagManager()
    assert fm.is_enabled("territory_management", "enterprise") is True
    assert fm.is_enabled("predictive_analytics", "enterprise") is True
    assert fm.is_enabled("compliance_reports", "enterprise") is True
    assert fm.is_enabled("white_label", "enterprise") is True


def test_beta_feature():
    fm = FeatureFlagManager()
    # Beta feature without tenant_id should be disabled
    assert fm.is_enabled("argentor_backend", "enterprise") is False
    # With beta tenant
    fm.add_beta_tenant("argentor_backend", "tenant-123")
    assert fm.is_enabled("argentor_backend", "enterprise", tenant_id="tenant-123") is True
    assert fm.is_enabled("argentor_backend", "enterprise", tenant_id="tenant-456") is False


def test_override():
    fm = FeatureFlagManager()
    assert fm.is_enabled("territory_management", "free") is False
    fm.set_override("special-tenant", "territory_management", True)
    assert fm.is_enabled("territory_management", "free", tenant_id="special-tenant") is True


def test_clear_override():
    fm = FeatureFlagManager()
    fm.set_override("t1", "ab_testing", False)
    assert fm.is_enabled("ab_testing", "pro", tenant_id="t1") is False
    fm.clear_override("t1", "ab_testing")
    assert fm.is_enabled("ab_testing", "pro", tenant_id="t1") is True


def test_unknown_feature():
    fm = FeatureFlagManager()
    assert fm.is_enabled("nonexistent_feature", "enterprise") is False


def test_get_features_for_plan():
    fm = FeatureFlagManager()
    free_features = fm.get_features_for_plan("free")
    pro_features = fm.get_features_for_plan("pro")
    assert len(pro_features) > len(free_features)


def test_get_all_features():
    fm = FeatureFlagManager()
    all_features = fm.get_all_features()
    assert len(all_features) >= 20
