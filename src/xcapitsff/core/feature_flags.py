"""Feature Flags — control feature rollout per tenant and plan.

Features can be toggled globally, per plan, or per tenant.
This enables gradual rollout, A/B feature testing, and plan-based access control.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class FeatureStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    BETA = "beta"  # enabled for specific tenants only


@dataclass
class FeatureFlag:
    key: str
    name: str
    description: str
    status: FeatureStatus = FeatureStatus.DISABLED
    plans: list[str] = field(default_factory=list)  # plans where it's available
    beta_tenants: list[str] = field(default_factory=list)  # tenant_ids with beta access
    created_at: datetime = field(default_factory=datetime.now)


# All features in the system
FEATURES: dict[str, FeatureFlag] = {
    # Sales features
    "icp_scoring": FeatureFlag("icp_scoring", "ICP Scoring", "Multi-factor lead scoring", FeatureStatus.ENABLED, ["free", "pro", "enterprise"]),
    "advanced_scoring": FeatureFlag("advanced_scoring", "Advanced Scoring", "Engagement + company fit factors", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "pipeline_automation": FeatureFlag("pipeline_automation", "Pipeline Automation", "Auto-advance leads based on rules", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "outreach_sequences": FeatureFlag("outreach_sequences", "Outreach Sequences", "Multi-step automated outreach", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "ab_testing": FeatureFlag("ab_testing", "A/B Testing", "Test message variants", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "lead_enrichment": FeatureFlag("lead_enrichment", "Lead Enrichment", "Auto-infer company data", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "territory_management": FeatureFlag("territory_management", "Territory Management", "Geographic lead assignment", FeatureStatus.ENABLED, ["enterprise"]),
    "predictive_analytics": FeatureFlag("predictive_analytics", "Predictive Analytics", "Forecast pipeline and churn", FeatureStatus.ENABLED, ["enterprise"]),
    "crm_integration": FeatureFlag("crm_integration", "CRM Integration", "Salesforce/HubSpot sync", FeatureStatus.ENABLED, ["pro", "enterprise"]),

    # Support features
    "ticket_routing": FeatureFlag("ticket_routing", "Smart Routing", "AI-powered ticket classification", FeatureStatus.ENABLED, ["free", "pro", "enterprise"]),
    "sla_monitoring": FeatureFlag("sla_monitoring", "SLA Monitoring", "Breach detection and alerts", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "knowledge_base": FeatureFlag("knowledge_base", "Knowledge Base", "Self-service articles", FeatureStatus.ENABLED, ["free", "pro", "enterprise"]),
    "escalation_workflow": FeatureFlag("escalation_workflow", "Escalation Workflow", "L1-L4 structured escalation", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "csat_nps": FeatureFlag("csat_nps", "CSAT/NPS", "Customer satisfaction tracking", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "response_templates": FeatureFlag("response_templates", "Response Templates", "Pre-built ticket responses", FeatureStatus.ENABLED, ["free", "pro", "enterprise"]),

    # Agent features
    "ai_agents": FeatureFlag("ai_agents", "AI Agents", "AI-powered sales and support agents", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "agent_orchestration": FeatureFlag("agent_orchestration", "Agent Orchestration", "Multi-agent task automation", FeatureStatus.ENABLED, ["enterprise"]),
    "argentor_backend": FeatureFlag("argentor_backend", "Argentor Backend", "Production agent runtime", FeatureStatus.BETA, ["enterprise"]),

    # Platform features
    "webhooks": FeatureFlag("webhooks", "Webhooks", "Inbound/outbound webhooks", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "api_access": FeatureFlag("api_access", "API Access", "REST API access", FeatureStatus.ENABLED, ["free", "pro", "enterprise"]),
    "export_csv": FeatureFlag("export_csv", "CSV Export", "Export data to CSV", FeatureStatus.ENABLED, ["free", "pro", "enterprise"]),
    "export_json": FeatureFlag("export_json", "JSON Export", "Export data to JSON", FeatureStatus.ENABLED, ["pro", "enterprise"]),
    "compliance_reports": FeatureFlag("compliance_reports", "Compliance Reports", "GDPR/ISO audit reports", FeatureStatus.ENABLED, ["enterprise"]),
    "white_label": FeatureFlag("white_label", "White Label", "Custom branding", FeatureStatus.ENABLED, ["enterprise"]),
    "custom_agents": FeatureFlag("custom_agents", "Custom Agents", "Create custom AI agent profiles", FeatureStatus.BETA, ["enterprise"]),
}


class FeatureFlagManager:
    """Check feature availability for tenants."""

    def __init__(self):
        self._overrides: dict[str, dict[str, bool]] = {}  # tenant_id → {feature → enabled}

    def is_enabled(self, feature_key: str, tenant_plan: str = "free", tenant_id: str | None = None) -> bool:
        """Check if a feature is enabled for a tenant."""
        flag = FEATURES.get(feature_key)
        if not flag:
            return False

        # Check tenant-specific override
        if tenant_id and tenant_id in self._overrides:
            override = self._overrides[tenant_id].get(feature_key)
            if override is not None:
                return override

        if flag.status == FeatureStatus.DISABLED:
            return False

        if flag.status == FeatureStatus.BETA:
            return tenant_id in flag.beta_tenants if tenant_id else False

        # ENABLED — check plan
        return tenant_plan in flag.plans

    def set_override(self, tenant_id: str, feature_key: str, enabled: bool) -> None:
        if tenant_id not in self._overrides:
            self._overrides[tenant_id] = {}
        self._overrides[tenant_id][feature_key] = enabled

    def clear_override(self, tenant_id: str, feature_key: str) -> None:
        if tenant_id in self._overrides:
            self._overrides[tenant_id].pop(feature_key, None)

    def get_features_for_plan(self, plan: str) -> list[FeatureFlag]:
        return [f for f in FEATURES.values() if plan in f.plans and f.status != FeatureStatus.DISABLED]

    def get_all_features(self) -> list[FeatureFlag]:
        return list(FEATURES.values())

    def get_feature(self, key: str) -> FeatureFlag | None:
        return FEATURES.get(key)

    def add_beta_tenant(self, feature_key: str, tenant_id: str) -> bool:
        flag = FEATURES.get(feature_key)
        if not flag:
            return False
        if tenant_id not in flag.beta_tenants:
            flag.beta_tenants.append(tenant_id)
        return True


# Singleton
feature_flags = FeatureFlagManager()
