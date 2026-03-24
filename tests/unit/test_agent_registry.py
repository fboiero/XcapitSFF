"""Tests for the Agent Registry module."""

import pytest

from xcapitsff.agents.agent_registry import (
    AgentCapability,
    AgentProfile,
    AgentRegistry,
    AgentStatus,
    ModelTier,
    agent_registry,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def registry() -> AgentRegistry:
    """Fresh registry with default agents for each test."""
    return AgentRegistry()


@pytest.fixture
def custom_agent() -> AgentProfile:
    """A custom agent profile for registration tests."""
    return AgentProfile(
        id="custom_agent",
        name="Custom Agent",
        role="custom_role",
        description="Un agente personalizado para tests.",
        capabilities=[AgentCapability.ANALYZE, AgentCapability.PLAN],
        model_tier=ModelTier.HAIKU,
        system_prompt="Sos un agente de prueba.",
        tools=["test_tool"],
        cost_per_1k_tokens=0.001,
    )


# ------------------------------------------------------------------
# Default agents
# ------------------------------------------------------------------


class TestDefaultAgents:
    def test_default_agents_count(self, registry: AgentRegistry) -> None:
        """15 agents are pre-registered by default."""
        assert len(registry.list_agents()) == 15

    def test_all_default_agents_available(self, registry: AgentRegistry) -> None:
        """All default agents start with AVAILABLE status."""
        for agent in registry.list_agents():
            assert agent.status == AgentStatus.AVAILABLE

    def test_default_agent_ids(self, registry: AgentRegistry) -> None:
        """Verify all expected default agent ids exist."""
        expected_ids = {
            "product_manager",
            "business_analyst",
            "planner",
            "spec_writer",
            "proposal_writer",
            "security_reviewer",
            "implementer",
            "code_reviewer",
            "test_runner",
            "doc_updater",
            "sales_qualifier",
            "outreach_composer",
            "support_responder",
            "ticket_router",
            "analytics_reporter",
        }
        actual_ids = {a.id for a in registry.list_agents()}
        assert actual_ids == expected_ids

    def test_opus_agents_cost(self, registry: AgentRegistry) -> None:
        """OPUS agents have cost_per_1k_tokens = 0.015."""
        opus_agents = [
            a for a in registry.list_agents() if a.model_tier == ModelTier.OPUS
        ]
        assert len(opus_agents) == 6
        for a in opus_agents:
            assert a.cost_per_1k_tokens == 0.015

    def test_sonnet_agents_cost(self, registry: AgentRegistry) -> None:
        """SONNET agents have cost_per_1k_tokens = 0.003."""
        sonnet_agents = [
            a for a in registry.list_agents() if a.model_tier == ModelTier.SONNET
        ]
        assert len(sonnet_agents) == 9
        for a in sonnet_agents:
            assert a.cost_per_1k_tokens == 0.003


# ------------------------------------------------------------------
# Register / Unregister
# ------------------------------------------------------------------


class TestRegisterUnregister:
    def test_register_new_agent(
        self, registry: AgentRegistry, custom_agent: AgentProfile
    ) -> None:
        result = registry.register(custom_agent)
        assert result is custom_agent
        assert registry.get_agent("custom_agent") is custom_agent
        assert len(registry.list_agents()) == 16

    def test_register_overwrites_existing(self, registry: AgentRegistry) -> None:
        """Registering with an existing id replaces the agent."""
        replacement = AgentProfile(
            id="planner",
            name="Super Planner",
            role="planner",
            description="Upgraded planner.",
            capabilities=[AgentCapability.PLAN],
            model_tier=ModelTier.OPUS,
            system_prompt="Sos el Super Planner.",
            tools=[],
        )
        registry.register(replacement)
        assert registry.get_agent("planner").name == "Super Planner"
        # Total count unchanged — replacement, not addition
        assert len(registry.list_agents()) == 15

    def test_unregister_existing(self, registry: AgentRegistry) -> None:
        assert registry.unregister("planner") is True
        assert registry.get_agent("planner") is None
        assert len(registry.list_agents()) == 14

    def test_unregister_nonexistent(self, registry: AgentRegistry) -> None:
        assert registry.unregister("nonexistent") is False


# ------------------------------------------------------------------
# Get agent by id / role
# ------------------------------------------------------------------


class TestGetAgent:
    def test_get_agent_by_id(self, registry: AgentRegistry) -> None:
        agent = registry.get_agent("implementer")
        assert agent is not None
        assert agent.name == "Implementer"

    def test_get_agent_not_found(self, registry: AgentRegistry) -> None:
        assert registry.get_agent("does_not_exist") is None

    def test_get_by_role(self, registry: AgentRegistry) -> None:
        agent = registry.get_by_role("security_reviewer")
        assert agent is not None
        assert agent.id == "security_reviewer"

    def test_get_by_role_not_found(self, registry: AgentRegistry) -> None:
        assert registry.get_by_role("nonexistent_role") is None


# ------------------------------------------------------------------
# Get available by capability
# ------------------------------------------------------------------


class TestGetAvailable:
    def test_get_available_analyze(self, registry: AgentRegistry) -> None:
        """Multiple agents have ANALYZE capability."""
        agents = registry.get_available(AgentCapability.ANALYZE)
        ids = {a.id for a in agents}
        assert "product_manager" in ids
        assert "business_analyst" in ids
        assert "planner" in ids
        assert "sales_qualifier" in ids
        assert "analytics_reporter" in ids
        assert len(agents) == 5

    def test_get_available_excludes_busy(self, registry: AgentRegistry) -> None:
        """Busy agents are not returned."""
        registry.mark_busy("planner", "task-1")
        agents = registry.get_available(AgentCapability.ANALYZE)
        ids = {a.id for a in agents}
        assert "planner" not in ids

    def test_get_available_no_match(self, registry: AgentRegistry) -> None:
        """Returns empty list when no agent has the capability."""
        # Mark all ANALYZE agents offline
        for agent in registry.list_agents():
            if AgentCapability.ANALYZE in agent.capabilities:
                registry.update_status(agent.id, AgentStatus.OFFLINE)
        assert registry.get_available(AgentCapability.ANALYZE) == []


# ------------------------------------------------------------------
# Status management
# ------------------------------------------------------------------


class TestStatusManagement:
    def test_mark_busy(self, registry: AgentRegistry) -> None:
        assert registry.mark_busy("implementer", "TASK-001") is True
        agent = registry.get_agent("implementer")
        assert agent.status == AgentStatus.BUSY
        assert agent.current_task_id == "TASK-001"

    def test_mark_available(self, registry: AgentRegistry) -> None:
        registry.mark_busy("implementer", "TASK-001")
        assert registry.mark_available("implementer") is True
        agent = registry.get_agent("implementer")
        assert agent.status == AgentStatus.AVAILABLE
        assert agent.current_task_id is None

    def test_update_status_offline(self, registry: AgentRegistry) -> None:
        assert registry.update_status("implementer", AgentStatus.OFFLINE) is True
        assert registry.get_agent("implementer").status == AgentStatus.OFFLINE

    def test_update_status_nonexistent(self, registry: AgentRegistry) -> None:
        assert registry.update_status("ghost", AgentStatus.BUSY) is False

    def test_mark_busy_nonexistent(self, registry: AgentRegistry) -> None:
        assert registry.mark_busy("ghost", "TASK-001") is False

    def test_mark_available_nonexistent(self, registry: AgentRegistry) -> None:
        assert registry.mark_available("ghost") is False

    def test_list_agents_by_status(self, registry: AgentRegistry) -> None:
        registry.mark_busy("implementer", "T-1")
        registry.update_status("code_reviewer", AgentStatus.OFFLINE)
        busy = registry.list_agents(status=AgentStatus.BUSY)
        assert len(busy) == 1
        assert busy[0].id == "implementer"
        offline = registry.list_agents(status=AgentStatus.OFFLINE)
        assert len(offline) == 1
        available = registry.list_agents(status=AgentStatus.AVAILABLE)
        assert len(available) == 13


# ------------------------------------------------------------------
# Record completion
# ------------------------------------------------------------------


class TestRecordCompletion:
    def test_record_single_completion(self, registry: AgentRegistry) -> None:
        registry.record_completion("implementer", duration_seconds=5.0, tokens_used=1000)
        agent = registry.get_agent("implementer")
        assert agent.tasks_completed == 1
        assert agent.avg_response_seconds == 5.0
        assert agent.total_tokens_used == 1000
        assert agent.last_active is not None

    def test_record_multiple_completions_running_average(
        self, registry: AgentRegistry
    ) -> None:
        registry.record_completion("implementer", duration_seconds=4.0, tokens_used=500)
        registry.record_completion("implementer", duration_seconds=6.0, tokens_used=700)
        agent = registry.get_agent("implementer")
        assert agent.tasks_completed == 2
        assert agent.avg_response_seconds == pytest.approx(5.0)
        assert agent.total_tokens_used == 1200

    def test_record_completion_three_tasks(self, registry: AgentRegistry) -> None:
        registry.record_completion("implementer", duration_seconds=3.0, tokens_used=100)
        registry.record_completion("implementer", duration_seconds=6.0, tokens_used=200)
        registry.record_completion("implementer", duration_seconds=9.0, tokens_used=300)
        agent = registry.get_agent("implementer")
        assert agent.tasks_completed == 3
        assert agent.avg_response_seconds == pytest.approx(6.0)
        assert agent.total_tokens_used == 600

    def test_record_completion_nonexistent(self, registry: AgentRegistry) -> None:
        """Should not raise — just no-op."""
        registry.record_completion("ghost", duration_seconds=1.0, tokens_used=100)


# ------------------------------------------------------------------
# Select best agent
# ------------------------------------------------------------------


class TestSelectBestAgent:
    def test_select_by_capability(self, registry: AgentRegistry) -> None:
        agent = registry.select_best_agent(AgentCapability.IMPLEMENT)
        assert agent is not None
        assert agent.id == "implementer"

    def test_select_with_tier_preference(self, registry: AgentRegistry) -> None:
        """Prefer OPUS tier when analyzing."""
        agent = registry.select_best_agent(
            AgentCapability.ANALYZE, prefer_tier=ModelTier.OPUS
        )
        assert agent is not None
        assert agent.model_tier == ModelTier.OPUS

    def test_select_falls_back_if_tier_unavailable(
        self, registry: AgentRegistry
    ) -> None:
        """If no HAIKU agent has the capability, pick from other tiers."""
        agent = registry.select_best_agent(
            AgentCapability.IMPLEMENT, prefer_tier=ModelTier.HAIKU
        )
        assert agent is not None
        assert agent.id == "implementer"

    def test_select_least_loaded(self, registry: AgentRegistry) -> None:
        """Among equal agents, pick the one with fewest tasks_completed."""
        # Give some ANALYZE agents work
        registry.record_completion("product_manager", 1.0, 100)
        registry.record_completion("product_manager", 1.0, 100)
        registry.record_completion("business_analyst", 1.0, 100)
        # planner, sales_qualifier, analytics_reporter have 0 tasks
        agent = registry.select_best_agent(AgentCapability.ANALYZE)
        assert agent.tasks_completed == 0

    def test_select_none_when_all_busy(self, registry: AgentRegistry) -> None:
        registry.mark_busy("implementer", "T-1")
        agent = registry.select_best_agent(AgentCapability.IMPLEMENT)
        assert agent is None

    def test_select_none_for_unmatched_capability(
        self, registry: AgentRegistry
    ) -> None:
        """No agents available if capability is not in any agent."""
        # All agents are already registered; unregister the only CLASSIFY agent
        registry.unregister("ticket_router")
        agent = registry.select_best_agent(AgentCapability.CLASSIFY)
        assert agent is None


# ------------------------------------------------------------------
# Pool stats
# ------------------------------------------------------------------


class TestPoolStats:
    def test_pool_stats_defaults(self, registry: AgentRegistry) -> None:
        stats = registry.get_pool_stats()
        assert stats["total"] == 15
        assert stats["available"] == 15
        assert stats["busy"] == 0
        assert stats["offline"] == 0
        assert stats["total_tokens"] == 0
        assert "opus" in stats["by_tier"]
        assert "sonnet" in stats["by_tier"]
        assert stats["by_tier"]["opus"] == 6
        assert stats["by_tier"]["sonnet"] == 9

    def test_pool_stats_with_busy(self, registry: AgentRegistry) -> None:
        registry.mark_busy("implementer", "T-1")
        registry.update_status("code_reviewer", AgentStatus.OFFLINE)
        stats = registry.get_pool_stats()
        assert stats["available"] == 13
        assert stats["busy"] == 1
        assert stats["offline"] == 1

    def test_pool_stats_by_capability(self, registry: AgentRegistry) -> None:
        stats = registry.get_pool_stats()
        # ANALYZE appears in product_manager, business_analyst, planner,
        # sales_qualifier, analytics_reporter = 5
        assert stats["by_capability"]["analyze"] == 5

    def test_pool_stats_total_tokens(self, registry: AgentRegistry) -> None:
        registry.record_completion("implementer", 1.0, 500)
        registry.record_completion("test_runner", 1.0, 300)
        stats = registry.get_pool_stats()
        assert stats["total_tokens"] == 800


# ------------------------------------------------------------------
# Agent stats
# ------------------------------------------------------------------


class TestAgentStats:
    def test_agent_stats(self, registry: AgentRegistry) -> None:
        registry.record_completion("implementer", 2.5, 1000)
        stats = registry.get_agent_stats("implementer")
        assert stats is not None
        assert stats["id"] == "implementer"
        assert stats["tasks_completed"] == 1
        assert stats["avg_response_seconds"] == 2.5
        assert stats["total_tokens_used"] == 1000

    def test_agent_stats_not_found(self, registry: AgentRegistry) -> None:
        assert registry.get_agent_stats("ghost") is None


# ------------------------------------------------------------------
# Multi-capability agents
# ------------------------------------------------------------------


class TestMultiCapability:
    def test_business_analyst_has_three_capabilities(
        self, registry: AgentRegistry
    ) -> None:
        agent = registry.get_agent("business_analyst")
        assert set(agent.capabilities) == {
            AgentCapability.ANALYZE,
            AgentCapability.SPEC,
            AgentCapability.PROPOSE,
        }

    def test_agent_appears_in_multiple_capability_searches(
        self, registry: AgentRegistry
    ) -> None:
        analyze_agents = registry.get_available(AgentCapability.ANALYZE)
        spec_agents = registry.get_available(AgentCapability.SPEC)
        ba_in_analyze = any(a.id == "business_analyst" for a in analyze_agents)
        ba_in_spec = any(a.id == "business_analyst" for a in spec_agents)
        assert ba_in_analyze
        assert ba_in_spec


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------


class TestSingleton:
    def test_module_singleton_exists(self) -> None:
        assert agent_registry is not None
        assert isinstance(agent_registry, AgentRegistry)
        assert len(agent_registry.list_agents()) == 15


# ------------------------------------------------------------------
# Enum values
# ------------------------------------------------------------------


class TestEnums:
    def test_capability_values(self) -> None:
        assert AgentCapability.QUALIFY.value == "qualify"
        assert AgentCapability.SECURITY.value == "security"

    def test_model_tier_values(self) -> None:
        assert ModelTier.OPUS.value == "opus"
        assert ModelTier.SONNET.value == "sonnet"
        assert ModelTier.HAIKU.value == "haiku"

    def test_agent_status_values(self) -> None:
        assert AgentStatus.AVAILABLE.value == "available"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.OFFLINE.value == "offline"
