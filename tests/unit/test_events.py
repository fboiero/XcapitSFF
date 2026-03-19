"""Tests for the event bus system."""

import pytest

from xcapitsff.core.events import Event, EventBus, EventType


@pytest.fixture
def bus():
    return EventBus()


@pytest.mark.asyncio
async def test_emit_and_handle(bus):
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(EventType.LEAD_CREATED, handler)
    event = Event(type=EventType.LEAD_CREATED, data={"lead_id": 1})
    await bus.emit(event)

    assert len(received) == 1
    assert received[0].data["lead_id"] == 1


@pytest.mark.asyncio
async def test_multiple_handlers(bus):
    results = []

    async def handler_a(event):
        results.append("a")

    async def handler_b(event):
        results.append("b")

    bus.subscribe(EventType.TICKET_CREATED, handler_a)
    bus.subscribe(EventType.TICKET_CREATED, handler_b)
    await bus.emit(Event(type=EventType.TICKET_CREATED, data={}))

    assert results == ["a", "b"]


@pytest.mark.asyncio
async def test_unsubscribe(bus):
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(EventType.LEAD_CREATED, handler)
    bus.unsubscribe(EventType.LEAD_CREATED, handler)
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={}))

    assert len(received) == 0


@pytest.mark.asyncio
async def test_global_handler(bus):
    received = []

    async def handler(event):
        received.append(event.type)

    bus.subscribe_all(handler)
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={}))
    await bus.emit(Event(type=EventType.TICKET_CREATED, data={}))

    assert len(received) == 2
    assert EventType.LEAD_CREATED in received
    assert EventType.TICKET_CREATED in received


@pytest.mark.asyncio
async def test_event_log(bus):
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={"id": 1}))
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={"id": 2}))
    await bus.emit(Event(type=EventType.TICKET_CREATED, data={"id": 3}))

    events = bus.get_recent_events()
    assert len(events) == 3

    lead_events = bus.get_recent_events(event_type=EventType.LEAD_CREATED)
    assert len(lead_events) == 2


@pytest.mark.asyncio
async def test_event_counts(bus):
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={}))
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={}))
    await bus.emit(Event(type=EventType.TICKET_CREATED, data={}))

    counts = bus.get_event_counts()
    assert counts["lead.created"] == 2
    assert counts["ticket.created"] == 1


@pytest.mark.asyncio
async def test_handler_error_doesnt_crash(bus):
    """A failing handler should not crash the bus."""
    async def bad_handler(event):
        raise RuntimeError("boom")

    async def good_handler(event):
        event.data["handled"] = True

    bus.subscribe(EventType.LEAD_CREATED, bad_handler)
    bus.subscribe(EventType.LEAD_CREATED, good_handler)

    event = Event(type=EventType.LEAD_CREATED, data={})
    await bus.emit(event)
    assert event.data.get("handled") is True


def test_event_has_id():
    event = Event(type=EventType.LEAD_CREATED, data={})
    assert event.event_id != ""
    assert len(event.event_id) == 8


@pytest.mark.asyncio
async def test_event_log_max_size():
    bus = EventBus()
    bus._max_log_size = 5
    for i in range(10):
        await bus.emit(Event(type=EventType.LEAD_CREATED, data={"i": i}))
    assert len(bus._event_log) == 5
    assert bus._event_log[0].data["i"] == 5
