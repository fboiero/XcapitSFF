"""Tests for notification center."""

from datetime import datetime, timedelta

from xcapitsff.core.notification_center import (
    Notification,
    NotificationCenter,
    NotificationType,
)


def _make_center() -> NotificationCenter:
    return NotificationCenter()


# --- Basic operations ---


def test_notify_creates_notification():
    nc = _make_center()
    n = nc.notify("t1", "u1", NotificationType.INFO, "Hello", "World")
    assert isinstance(n, Notification)
    assert n.tenant_id == "t1"
    assert n.user_id == "u1"
    assert n.type == NotificationType.INFO
    assert n.title == "Hello"
    assert n.message == "World"
    assert n.read is False
    assert n.archived is False
    assert n.id  # uuid assigned


def test_notify_with_link_and_metadata():
    nc = _make_center()
    n = nc.notify(
        "t1", "u1", NotificationType.LEAD_HOT, "Hot!", "Check it",
        link="/leads/42", metadata={"score": 95},
    )
    assert n.link == "/leads/42"
    assert n.metadata["score"] == 95


def test_notify_all_creates_for_all_users():
    nc = _make_center()
    # Register users by sending them individual notifications first
    nc.notify("t1", "u1", NotificationType.INFO, "a", "b")
    nc.notify("t1", "u2", NotificationType.INFO, "a", "b")
    nc.notify("t1", "u3", NotificationType.INFO, "a", "b")

    results = nc.notify_all("t1", NotificationType.SYSTEM, "Downtime", "Scheduled")
    assert len(results) == 3
    user_ids = {n.user_id for n in results}
    assert user_ids == {"u1", "u2", "u3"}


def test_notify_all_empty_tenant():
    nc = _make_center()
    results = nc.notify_all("empty_tenant", NotificationType.INFO, "a", "b")
    assert results == []


# --- Retrieval ---


def test_get_notifications_returns_newest_first():
    nc = _make_center()
    nc.notify("t1", "u1", NotificationType.INFO, "First", "1")
    nc.notify("t1", "u1", NotificationType.INFO, "Second", "2")
    nc.notify("t1", "u1", NotificationType.INFO, "Third", "3")

    notifs = nc.get_notifications("t1", "u1")
    assert len(notifs) == 3
    assert notifs[0].title == "Third"
    assert notifs[2].title == "First"


def test_get_unread_only():
    nc = _make_center()
    n1 = nc.notify("t1", "u1", NotificationType.INFO, "Read", "r")
    nc.notify("t1", "u1", NotificationType.INFO, "Unread", "u")
    nc.mark_read(n1.id)

    unread = nc.get_notifications("t1", "u1", unread_only=True)
    assert len(unread) == 1
    assert unread[0].title == "Unread"


def test_get_notifications_with_limit_and_offset():
    nc = _make_center()
    for i in range(10):
        nc.notify("t1", "u1", NotificationType.INFO, f"N{i}", "body")

    page1 = nc.get_notifications("t1", "u1", limit=3, offset=0)
    page2 = nc.get_notifications("t1", "u1", limit=3, offset=3)

    assert len(page1) == 3
    assert len(page2) == 3
    # No overlap
    ids_1 = {n.id for n in page1}
    ids_2 = {n.id for n in page2}
    assert ids_1.isdisjoint(ids_2)


# --- Mark read ---


def test_mark_read():
    nc = _make_center()
    n = nc.notify("t1", "u1", NotificationType.INFO, "X", "Y")
    assert nc.mark_read(n.id) is True

    notifs = nc.get_notifications("t1", "u1")
    assert notifs[0].read is True
    assert notifs[0].read_at is not None


def test_mark_read_nonexistent():
    nc = _make_center()
    assert nc.mark_read("nonexistent-id") is False


def test_mark_all_read():
    nc = _make_center()
    nc.notify("t1", "u1", NotificationType.INFO, "A", "a")
    nc.notify("t1", "u1", NotificationType.WARNING, "B", "b")
    nc.notify("t1", "u1", NotificationType.ERROR, "C", "c")

    count = nc.mark_all_read("t1", "u1")
    assert count == 3
    assert nc.get_unread_count("t1", "u1") == 0


def test_mark_all_read_returns_zero_when_all_read():
    nc = _make_center()
    nc.notify("t1", "u1", NotificationType.INFO, "A", "a")
    nc.mark_all_read("t1", "u1")

    count = nc.mark_all_read("t1", "u1")
    assert count == 0


# --- Archive ---


def test_archive():
    nc = _make_center()
    n = nc.notify("t1", "u1", NotificationType.INFO, "X", "Y")
    assert nc.archive(n.id) is True

    notifs = nc.get_notifications("t1", "u1")
    assert len(notifs) == 0  # archived notifications are excluded


def test_archive_nonexistent():
    nc = _make_center()
    assert nc.archive("nonexistent-id") is False


# --- Unread count ---


def test_unread_count():
    nc = _make_center()
    nc.notify("t1", "u1", NotificationType.INFO, "A", "a")
    nc.notify("t1", "u1", NotificationType.INFO, "B", "b")
    n3 = nc.notify("t1", "u1", NotificationType.INFO, "C", "c")

    assert nc.get_unread_count("t1", "u1") == 3
    nc.mark_read(n3.id)
    assert nc.get_unread_count("t1", "u1") == 2


def test_unread_count_excludes_archived():
    nc = _make_center()
    n = nc.notify("t1", "u1", NotificationType.INFO, "A", "a")
    nc.archive(n.id)
    assert nc.get_unread_count("t1", "u1") == 0


# --- Feed grouping ---


def test_notification_feed_grouping():
    nc = _make_center()
    now = datetime.now()

    # Today
    n_today = nc.notify("t1", "u1", NotificationType.INFO, "Today", "t")
    n_today.created_at = now

    # Yesterday
    n_yesterday = nc.notify("t1", "u1", NotificationType.INFO, "Yesterday", "y")
    n_yesterday.created_at = now - timedelta(days=1)

    # Earlier this week (3 days ago — may land in this_week or yesterday depending on day)
    n_week = nc.notify("t1", "u1", NotificationType.INFO, "Week", "w")
    n_week.created_at = now - timedelta(days=5)

    # Older (30 days ago)
    n_old = nc.notify("t1", "u1", NotificationType.INFO, "Older", "o")
    n_old.created_at = now - timedelta(days=30)

    feed = nc.get_notification_feed("t1", "u1")
    assert "today" in feed
    assert "yesterday" in feed
    assert "this_week" in feed
    assert "older" in feed

    # Older should definitely have the 30-day-old one
    older_titles = [n.title for n in feed["older"]]
    assert "Older" in older_titles


# --- Cleanup ---


def test_delete_old():
    nc = _make_center()
    now = datetime.now()

    n_recent = nc.notify("t1", "u1", NotificationType.INFO, "Recent", "r")
    n_recent.created_at = now - timedelta(days=10)

    n_old = nc.notify("t1", "u1", NotificationType.INFO, "Old", "o")
    n_old.created_at = now - timedelta(days=100)

    deleted = nc.delete_old(days=90)
    assert deleted == 1

    notifs = nc.get_notifications("t1", "u1")
    assert len(notifs) == 1
    assert notifs[0].title == "Recent"


# --- Multi-tenant isolation ---


def test_multi_tenant_isolation():
    nc = _make_center()
    nc.notify("tenant_a", "u1", NotificationType.INFO, "A-msg", "a")
    nc.notify("tenant_b", "u1", NotificationType.INFO, "B-msg", "b")

    a_notifs = nc.get_notifications("tenant_a", "u1")
    b_notifs = nc.get_notifications("tenant_b", "u1")

    assert len(a_notifs) == 1
    assert a_notifs[0].title == "A-msg"
    assert len(b_notifs) == 1
    assert b_notifs[0].title == "B-msg"


def test_unread_count_tenant_isolated():
    nc = _make_center()
    nc.notify("t_x", "u1", NotificationType.INFO, "X", "x")
    nc.notify("t_y", "u1", NotificationType.INFO, "Y", "y")

    assert nc.get_unread_count("t_x", "u1") == 1
    assert nc.get_unread_count("t_y", "u1") == 1


# --- Notification types ---


def test_all_notification_types():
    nc = _make_center()
    for nt in NotificationType:
        n = nc.notify("t1", "u1", nt, f"Title-{nt.value}", "msg")
        assert n.type == nt
