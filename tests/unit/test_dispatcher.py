"""Tests for agent dispatcher."""

import pytest

from xcapitsff.agents.dispatcher import AgentDispatcher


def test_dispatcher_creation():
    d = AgentDispatcher()
    stats = d.get_stats()
    assert stats["total_dispatches"] == 0


def test_default_prompts():
    d = AgentDispatcher()
    prompt = d._default_prompt("sales_qualifier")
    assert "Xcapit" in prompt
    assert "ICP" in prompt


def test_default_prompt_unknown():
    d = AgentDispatcher()
    prompt = d._default_prompt("unknown_agent")
    assert "unknown_agent" in prompt


@pytest.mark.asyncio
async def test_dispatch_falls_to_local():
    d = AgentDispatcher()
    result = await d.dispatch("sales_qualifier", "Test lead data")
    assert result.success
    assert result.backend in ("local", "dry_run")
    assert result.agent_name == "sales_qualifier"


@pytest.mark.asyncio
async def test_qualify_lead():
    d = AgentDispatcher()
    result = await d.qualify_lead({
        "company_name": "Test Corp",
        "region": "LATAM",
        "c_level": True,
        "score_icp": 75,
    })
    assert result.success
    assert result.agent_name == "sales_qualifier"


@pytest.mark.asyncio
async def test_draft_outreach():
    d = AgentDispatcher()
    result = await d.draft_outreach({
        "company_name": "Acme",
        "contact_name": "Carlos",
        "region": "LATAM",
    })
    assert result.success
    assert result.agent_name == "outreach_composer"


@pytest.mark.asyncio
async def test_handle_ticket():
    d = AgentDispatcher()
    result = await d.handle_ticket({
        "subject": "Error en la app",
        "description": "No puedo acceder",
        "category": "technical",
        "priority": "high",
    })
    assert result.success
    assert result.agent_name == "support_responder"


@pytest.mark.asyncio
async def test_classify_ticket():
    d = AgentDispatcher()
    result = await d.classify_ticket("Problema con pago", "Me cobraron doble")
    assert result.success
    assert result.agent_name == "ticket_router"


@pytest.mark.asyncio
async def test_stats_increment():
    d = AgentDispatcher()
    await d.dispatch("sales_qualifier", "test")
    stats = d.get_stats()
    assert stats["total_dispatches"] >= 1
