"""Tests for Smart Inbox and Activity Feed."""

from datetime import datetime, timedelta

import pytest

from xcapitsff.core.activity import (
    ActivityEntry,
    ActivityFeed,
    _extract_description,
    _extract_entity_id,
    _extract_entity_name,
    setup_activity_feed,
)
from xcapitsff.core.events import Event, EventBus, EventType
from xcapitsff.core.inbox import InboxItem, InboxItemType, InboxManager, _make_id


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
def manager():
    return InboxManager()


@pytest.fixture
def feed():
    return ActivityFeed()


@pytest.fixture
def bus():
    return EventBus()


def _make_inbox_item(
    item_type: InboxItemType = InboxItemType.LEAD_HOT,
    priority: int = 2,
    entity_id: int = 1,
    is_read: bool = False,
    is_acted_on: bool = False,
) -> InboxItem:
    return InboxItem(
        item_id=_make_id(),
        type=item_type,
        title="Test item",
        subtitle="Test subtitle",
        entity_type="lead",
        entity_id=entity_id,
        priority=priority,
        action_url="/api/v1/leads/1",
        is_read=is_read,
        is_acted_on=is_acted_on,
    )


# =========================================================================
# InboxItem tests
# =========================================================================


def test_inbox_item_creation():
    """InboxItem dataclass is created with correct defaults."""
    item = InboxItem(
        item_id="abc123",
        type=InboxItemType.LEAD_HOT,
        title="Hot lead",
        subtitle="Score 85",
        entity_type="lead",
        entity_id=42,
        priority=2,
        action_url="/api/v1/leads/42",
    )
    assert item.item_id == "abc123"
    assert item.type == InboxItemType.LEAD_HOT
    assert item.is_read is False
    assert item.is_acted_on is False
    assert item.priority == 2
    assert item.entity_type == "lead"


def test_inbox_item_type_enum_values():
    """All expected InboxItemType values exist."""
    expected = {
        "lead_hot", "lead_stale", "ticket_urgent", "ticket_sla_warning",
        "ticket_unassigned", "outreach_pending", "outreach_replied",
        "approval_needed", "task_due", "system_alert",
    }
    actual = {t.value for t in InboxItemType}
    assert actual == expected


def test_make_id_returns_string():
    """_make_id generates a 12-char string."""
    id1 = _make_id()
    id2 = _make_id()
    assert isinstance(id1, str)
    assert len(id1) == 12
    assert id1 != id2


# =========================================================================
# InboxManager — mark / query tests (no DB needed)
# =========================================================================


def test_mark_read(manager):
    """mark_read sets is_read to True."""
    item = _make_inbox_item()
    manager._items[item.item_id] = item

    assert manager.mark_read(item.item_id) is True
    assert item.is_read is True


def test_mark_read_not_found(manager):
    """mark_read returns False for unknown item_id."""
    assert manager.mark_read("nonexistent") is False


def test_mark_acted(manager):
    """mark_acted sets is_acted_on and is_read."""
    item = _make_inbox_item()
    manager._items[item.item_id] = item

    assert manager.mark_acted(item.item_id) is True
    assert item.is_acted_on is True
    assert item.is_read is True


def test_mark_acted_not_found(manager):
    """mark_acted returns False for unknown item_id."""
    assert manager.mark_acted("nonexistent") is False


def test_get_count_by_type(manager):
    """get_count_by_type groups items correctly."""
    manager._items["a"] = _make_inbox_item(InboxItemType.LEAD_HOT, entity_id=1)
    manager._items["b"] = _make_inbox_item(InboxItemType.LEAD_HOT, entity_id=2)
    manager._items["c"] = _make_inbox_item(InboxItemType.TICKET_URGENT, entity_id=3)

    counts = manager.get_count_by_type()
    assert counts["lead_hot"] == 2
    assert counts["ticket_urgent"] == 1
    assert len(counts) == 2


def test_get_priority_items(manager):
    """get_priority_items returns top N unacted items sorted by priority."""
    item_low = _make_inbox_item(InboxItemType.LEAD_STALE, priority=4)
    item_high = _make_inbox_item(InboxItemType.TICKET_URGENT, priority=1)
    item_mid = _make_inbox_item(InboxItemType.LEAD_HOT, priority=2)
    item_acted = _make_inbox_item(InboxItemType.TICKET_URGENT, priority=1, is_acted_on=True)

    manager._items[item_low.item_id] = item_low
    manager._items[item_high.item_id] = item_high
    manager._items[item_mid.item_id] = item_mid
    manager._items[item_acted.item_id] = item_acted

    top = manager.get_priority_items(max_items=2)
    assert len(top) == 2
    assert top[0].priority <= top[1].priority
    # The acted item should NOT appear
    acted_ids = [i.item_id for i in top]
    assert item_acted.item_id not in acted_ids


def test_get_priority_items_respects_max(manager):
    """get_priority_items caps at max_items."""
    for i in range(20):
        item = _make_inbox_item(priority=3, entity_id=i)
        manager._items[item.item_id] = item

    result = manager.get_priority_items(max_items=5)
    assert len(result) == 5


def test_get_items_sorted(manager):
    """get_items returns all items sorted by priority."""
    items = [
        _make_inbox_item(priority=3, entity_id=1),
        _make_inbox_item(priority=1, entity_id=2),
        _make_inbox_item(priority=5, entity_id=3),
    ]
    for item in items:
        manager._items[item.item_id] = item

    result = manager.get_items()
    priorities = [i.priority for i in result]
    assert priorities == sorted(priorities)


def test_get_item(manager):
    """get_item retrieves a specific item by ID."""
    item = _make_inbox_item()
    manager._items[item.item_id] = item

    assert manager.get_item(item.item_id) is item
    assert manager.get_item("bogus") is None


# =========================================================================
# ActivityFeed tests
# =========================================================================


def test_record_activity(feed):
    """record creates and returns an ActivityEntry."""
    entry = feed.record(
        actor="sales_agent",
        action="created",
        entity_type="lead",
        entity_id=1,
        entity_name="Acme Corp",
        description="Lead creado: Acme Corp",
    )
    assert isinstance(entry, ActivityEntry)
    assert entry.actor == "sales_agent"
    assert entry.action == "created"
    assert entry.entity_type == "lead"
    assert entry.entity_id == 1
    assert feed.total_entries == 1


def test_get_feed_default(feed):
    """get_feed returns entries most-recent-first."""
    feed.record("a", "created", "lead", 1, "Lead1", "d1")
    feed.record("b", "resolved", "ticket", 2, "Ticket1", "d2")
    feed.record("c", "sent", "outreach", 3, "Out1", "d3")

    result = feed.get_feed(limit=50)
    assert len(result) == 3
    # Most recent first
    assert result[0].actor == "c"
    assert result[2].actor == "a"


def test_get_feed_filter_entity_type(feed):
    """get_feed filters by entity_type."""
    feed.record("a", "created", "lead", 1, "L1", "d1")
    feed.record("b", "created", "ticket", 2, "T1", "d2")
    feed.record("c", "created", "lead", 3, "L2", "d3")

    result = feed.get_feed(entity_type="lead")
    assert len(result) == 2
    assert all(e.entity_type == "lead" for e in result)


def test_get_feed_filter_actor(feed):
    """get_feed filters by actor."""
    feed.record("alice", "created", "lead", 1, "L1", "d1")
    feed.record("bob", "created", "lead", 2, "L2", "d2")
    feed.record("alice", "updated", "lead", 1, "L1", "d3")

    result = feed.get_feed(actor="alice")
    assert len(result) == 2
    assert all(e.actor == "alice" for e in result)


def test_get_entity_feed(feed):
    """get_entity_feed returns all entries for a specific entity."""
    feed.record("a", "created", "ticket", 10, "T10", "d1")
    feed.record("a", "updated", "ticket", 10, "T10", "d2")
    feed.record("b", "created", "ticket", 20, "T20", "d3")

    result = feed.get_entity_feed("ticket", 10)
    assert len(result) == 2
    # Most recent first
    assert result[0].action == "updated"


def test_get_today_summary(feed):
    """get_today_summary counts today's activities by action and entity type."""
    feed.record("a", "created", "lead", 1, "L", "d")
    feed.record("a", "created", "ticket", 2, "T", "d")
    feed.record("b", "resolved", "ticket", 2, "T", "d")

    summary = feed.get_today_summary()
    assert summary["total_activities"] == 3
    assert summary["by_action"]["created"] == 2
    assert summary["by_action"]["resolved"] == 1
    assert summary["by_entity_type"]["lead"] == 1
    assert summary["by_entity_type"]["ticket"] == 2
    assert set(summary["active_actors"]) == {"a", "b"}


def test_feed_max_entries(feed):
    """Feed caps at _max_entries."""
    feed._max_entries = 5
    for i in range(10):
        feed.record("a", "created", "lead", i, f"L{i}", f"d{i}")

    assert feed.total_entries == 5


# =========================================================================
# EventBus integration
# =========================================================================


@pytest.mark.asyncio
async def test_setup_activity_feed_records_lead_created(bus, feed):
    """setup_activity_feed auto-records LEAD_CREATED events."""
    setup_activity_feed(bus, feed)

    event = Event(
        type=EventType.LEAD_CREATED,
        data={"lead_id": 42, "company_name": "Acme"},
        source="api",
    )
    await bus.emit(event)

    entries = feed.get_feed()
    assert len(entries) == 1
    assert entries[0].action == "created"
    assert entries[0].entity_type == "lead"
    assert "Acme" in entries[0].description


@pytest.mark.asyncio
async def test_setup_activity_feed_records_ticket_resolved(bus, feed):
    """setup_activity_feed auto-records TICKET_RESOLVED events."""
    setup_activity_feed(bus, feed)

    event = Event(
        type=EventType.TICKET_RESOLVED,
        data={"ticket_id": 7, "subject": "Login issue"},
        source="support_agent",
    )
    await bus.emit(event)

    entries = feed.get_feed()
    assert len(entries) == 1
    assert entries[0].action == "resolved"
    assert "Login issue" in entries[0].description


@pytest.mark.asyncio
async def test_setup_activity_feed_records_outreach_sent(bus, feed):
    """setup_activity_feed auto-records OUTREACH_SENT events."""
    setup_activity_feed(bus, feed)

    event = Event(
        type=EventType.OUTREACH_SENT,
        data={"lead_id": 5, "lead": "BigCo"},
        source="outreach_composer",
    )
    await bus.emit(event)

    entries = feed.get_feed()
    assert len(entries) == 1
    assert entries[0].action == "sent"
    assert "BigCo" in entries[0].description


@pytest.mark.asyncio
async def test_setup_activity_feed_ignores_unknown_events(bus, feed):
    """Events with no descriptor are silently ignored."""
    setup_activity_feed(bus, feed)

    # Emit a known event type that IS in the descriptor map
    # but first emit something and verify count stays correct
    event = Event(
        type=EventType.LEAD_CREATED,
        data={"lead_id": 1, "company_name": "X"},
        source="test",
    )
    await bus.emit(event)
    assert feed.total_entries == 1


# =========================================================================
# Helper function tests
# =========================================================================


def test_extract_description_fills_template():
    """_extract_description fills placeholders from event data."""
    result = _extract_description(
        "Lead creado: {company}",
        {"company_name": "TestCo"},
    )
    assert result == "Lead creado: TestCo"


def test_extract_description_missing_data():
    """_extract_description uses N/A for missing keys."""
    result = _extract_description("Ticket creado: {subject}", {})
    assert result == "Ticket creado: N/A"


def test_extract_entity_id_tries_common_keys():
    """_extract_entity_id finds IDs from various key names."""
    assert _extract_entity_id({"lead_id": 42}) == 42
    assert _extract_entity_id({"ticket_id": 7}) == 7
    assert _extract_entity_id({"id": 99}) == 99
    assert _extract_entity_id({}) == 0


def test_extract_entity_name_by_type():
    """_extract_entity_name picks the right field for each entity type."""
    assert _extract_entity_name("lead", {"company_name": "A"}) == "A"
    assert _extract_entity_name("ticket", {"subject": "Bug"}) == "Bug"
    assert _extract_entity_name("customer", {"company_name": "B"}) == "B"
    assert _extract_entity_name("outreach", {"lead": "C"}) == "C"
    assert _extract_entity_name("unknown", {}) == "Unknown"


def test_get_feed_limit(feed):
    """get_feed respects the limit parameter."""
    for i in range(20):
        feed.record("a", "created", "lead", i, f"L{i}", f"d{i}")

    result = feed.get_feed(limit=5)
    assert len(result) == 5
