"""Tests for agent runner (dry run mode)."""

from xcapitsff.agents.conversation import ConversationMemory
from xcapitsff.agents.runner import AgentRunner


def test_qualify_lead_dry_run():
    mem = ConversationMemory()
    runner = AgentRunner(memory=mem)
    result = runner.qualify_lead({
        "id": 1,
        "company_name": "Test Corp",
        "region": "LATAM",
        "c_level": True,
        "score_icp": 75,
        "afinidad": "HIGH",
    })
    assert result.success
    assert "DRY RUN" in result.response
    assert result.agent_name == "sales_qualifier"
    assert result.conversation_id.startswith("conv-")


def test_draft_outreach_dry_run():
    mem = ConversationMemory()
    runner = AgentRunner(memory=mem)
    result = runner.draft_outreach({
        "id": 2,
        "company_name": "Acme",
        "contact_name": "Carlos",
        "region": "LATAM",
    })
    assert result.success
    assert result.agent_name == "outreach_composer"


def test_handle_ticket_dry_run():
    mem = ConversationMemory()
    runner = AgentRunner(memory=mem)
    result = runner.handle_ticket({
        "id": 10,
        "subject": "No puedo acceder",
        "description": "Mi cuenta está bloqueada",
        "category": "account",
        "priority": "high",
    })
    assert result.success
    assert result.agent_name == "support_responder"


def test_conversation_persists_across_calls():
    mem = ConversationMemory()
    runner = AgentRunner(memory=mem)

    runner.qualify_lead({"id": 1, "company_name": "Test"})
    runner.qualify_lead({"id": 1, "company_name": "Test"})

    # Should reuse same conversation
    conv = mem.find_by_context("sales_qualifier", "lead", 1)
    assert conv is not None
    assert conv.message_count == 4  # 2 user + 2 assistant


def test_different_contexts_different_conversations():
    mem = ConversationMemory()
    runner = AgentRunner(memory=mem)

    runner.qualify_lead({"id": 1})
    runner.qualify_lead({"id": 2})

    assert len(mem.list_conversations()) == 2


def test_run_unknown_agent():
    mem = ConversationMemory()
    runner = AgentRunner(memory=mem)
    runner._dry_run = False  # Force real mode to test unknown agent path

    result = runner.run_agent("unknown_agent", "test", "context")
    assert not result.success
    assert "not found" in result.error


def test_tokens_in_dry_run():
    mem = ConversationMemory()
    runner = AgentRunner(memory=mem)
    result = runner.qualify_lead({"id": 1})
    assert result.tokens_used["input_tokens"] == 0
    assert result.tokens_used["output_tokens"] == 0
