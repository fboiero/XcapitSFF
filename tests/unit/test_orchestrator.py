"""Tests for the agent orchestrator."""

import pytest

from xcapitsff.agents.orchestrator import AgentOrchestrator, TaskStatus
from xcapitsff.core.events import Event, EventBus, EventType


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def orch(bus):
    return AgentOrchestrator(bus)


@pytest.mark.asyncio
async def test_lead_created_triggers_qualifier(bus, orch):
    await bus.emit(Event(
        type=EventType.LEAD_CREATED,
        data={"lead_id": 1, "score": 75},
    ))
    assert len(orch.task_queue) >= 1
    task = orch.task_queue[0]
    assert task.agent_name == "sales_qualifier"
    assert task.action == "qualify_lead"


@pytest.mark.asyncio
async def test_ticket_created_triggers_router_and_responder(bus, orch):
    await bus.emit(Event(
        type=EventType.TICKET_CREATED,
        data={"ticket_id": 1, "priority": "medium"},
    ))
    agents = [t.agent_name for t in orch.task_queue]
    assert "ticket_router" in agents
    assert "support_responder" in agents


@pytest.mark.asyncio
async def test_urgent_ticket_no_auto_response(bus, orch):
    """Urgent tickets should not auto-draft a response."""
    await bus.emit(Event(
        type=EventType.TICKET_CREATED,
        data={"ticket_id": 1, "priority": "urgent"},
    ))
    responder_tasks = [t for t in orch.task_queue if t.agent_name == "support_responder"]
    assert len(responder_tasks) == 0


@pytest.mark.asyncio
async def test_process_queue(bus, orch):
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={"lead_id": 1}))
    assert len(orch.task_queue) > 0

    processed = await orch.process_queue()
    assert len(processed) > 0
    assert all(t.status == TaskStatus.COMPLETED for t in processed)
    assert len(orch.task_queue) == 0


@pytest.mark.asyncio
async def test_task_history(bus, orch):
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={}))
    await orch.process_queue()

    history = orch.get_task_history()
    assert len(history) > 0
    assert history[0].status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_stats(bus, orch):
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={}))
    await bus.emit(Event(type=EventType.TICKET_CREATED, data={"priority": "low"}))
    await orch.process_queue()

    stats = orch.get_stats()
    assert stats["total_tasks_processed"] > 0
    assert stats["pending"] == 0
    assert stats["completed"] > 0


@pytest.mark.asyncio
async def test_qualified_lead_triggers_outreach(bus, orch):
    """High-score qualified leads should trigger outreach drafting."""
    await bus.emit(Event(
        type=EventType.LEAD_QUALIFIED,
        data={"lead_id": 1, "score": 80},
    ))
    outreach_tasks = [t for t in orch.task_queue if t.agent_name == "outreach_composer"]
    assert len(outreach_tasks) >= 1


@pytest.mark.asyncio
async def test_low_score_qualified_no_outreach(bus, orch):
    """Low-score qualified leads should NOT trigger outreach."""
    await bus.emit(Event(
        type=EventType.LEAD_QUALIFIED,
        data={"lead_id": 1, "score": 30},
    ))
    outreach_tasks = [t for t in orch.task_queue if t.agent_name == "outreach_composer"]
    assert len(outreach_tasks) == 0


@pytest.mark.asyncio
async def test_customer_message_triggers_response(bus, orch):
    await bus.emit(Event(
        type=EventType.TICKET_MESSAGE_ADDED,
        data={"ticket_id": 1, "sender": "customer"},
    ))
    responder_tasks = [t for t in orch.task_queue if t.action == "followup_response"]
    assert len(responder_tasks) >= 1


@pytest.mark.asyncio
async def test_agent_message_no_response(bus, orch):
    """Agent messages should NOT trigger auto-response."""
    await bus.emit(Event(
        type=EventType.TICKET_MESSAGE_ADDED,
        data={"ticket_id": 1, "sender": "agent"},
    ))
    responder_tasks = [t for t in orch.task_queue if t.action == "followup_response"]
    assert len(responder_tasks) == 0


@pytest.mark.asyncio
async def test_add_custom_rule(bus, orch):
    orch.add_rule(
        EventType.CUSTOMER_CREATED,
        agent="welcome_agent",
        action="send_welcome",
        description="Send welcome on new customer",
    )
    await bus.emit(Event(type=EventType.CUSTOMER_CREATED, data={"customer_id": 1}))
    tasks = [t for t in orch.task_queue if t.agent_name == "welcome_agent"]
    assert len(tasks) == 1
