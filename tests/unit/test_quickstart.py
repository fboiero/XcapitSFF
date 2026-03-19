"""Tests for quickstart and notification preferences."""

from xcapitsff.selfservice.quickstart import QuickstartManager, QUICK_ACTIONS
from xcapitsff.selfservice.notifications_preferences import NotifPreferencesManager, NotifChannel, NotifFrequency


# === Quickstart ===

def test_quick_actions_exist():
    assert len(QUICK_ACTIONS) >= 8


def test_all_actions_have_endpoint():
    for a in QUICK_ACTIONS:
        assert a.api_endpoint.startswith("/api/")


def test_start_quickstart():
    qm = QuickstartManager()
    progress = qm.start("t1")
    assert progress.tenant_id == "t1"
    assert progress.completion_rate == 0


def test_complete_action():
    qm = QuickstartManager()
    qm.start("t1")
    qm.complete_action("t1", "try_scoring")
    progress = qm.get_progress("t1")
    assert "try_scoring" in progress.actions_completed
    assert progress.completion_rate > 0


def test_time_to_first_value():
    qm = QuickstartManager()
    qm.start("t1")
    qm.complete_action("t1", "try_scoring")
    progress = qm.get_progress("t1")
    assert progress.time_to_first_value_seconds is not None
    assert progress.time_to_first_value_seconds >= 0


def test_skip_action():
    qm = QuickstartManager()
    qm.start("t1")
    qm.skip_action("t1", "try_scoring")
    progress = qm.get_progress("t1")
    assert "try_scoring" in progress.actions_skipped


def test_next_action():
    qm = QuickstartManager()
    qm.start("t1")
    next_action = qm.get_next_action("t1")
    assert next_action is not None
    assert next_action.action_id == QUICK_ACTIONS[0].action_id


def test_next_action_skips_completed():
    qm = QuickstartManager()
    qm.start("t1")
    qm.complete_action("t1", QUICK_ACTIONS[0].action_id)
    next_action = qm.get_next_action("t1")
    assert next_action.action_id == QUICK_ACTIONS[1].action_id


def test_all_completed_returns_none():
    qm = QuickstartManager()
    qm.start("t1")
    for a in QUICK_ACTIONS:
        qm.complete_action("t1", a.action_id)
    assert qm.get_next_action("t1") is None
    assert qm.get_progress("t1").completion_rate == 100.0


def test_summary():
    qm = QuickstartManager()
    qm.start("t1")
    qm.complete_action("t1", "try_scoring")
    summary = qm.get_summary("t1")
    assert summary["actions_completed"] == 1
    assert summary["actions_total"] == len(QUICK_ACTIONS)


def test_filter_by_category():
    qm = QuickstartManager()
    sales_actions = qm.get_actions("sales")
    assert all(a.category == "sales" for a in sales_actions)
    assert len(sales_actions) >= 2


# === Notification Preferences ===

def test_default_preferences():
    npm = NotifPreferencesManager()
    prefs = npm.get_preferences("u1")
    assert len(prefs) >= 10


def test_update_preference():
    npm = NotifPreferencesManager()
    npm.get_preferences("u1")
    pref = npm.update_preference("u1", "ticket.urgent", channel="email", frequency="hourly")
    assert pref is not None
    assert pref.channel == NotifChannel.EMAIL
    assert pref.frequency == NotifFrequency.HOURLY_DIGEST


def test_disable_preference():
    npm = NotifPreferencesManager()
    npm.get_preferences("u1")
    pref = npm.update_preference("u1", "lead.stale", enabled=False)
    assert pref.enabled is False


def test_should_notify():
    npm = NotifPreferencesManager()
    npm.get_preferences("u1")
    enabled, channel, freq = npm.should_notify("u1", "ticket.urgent")
    assert enabled is True


def test_mute_all():
    npm = NotifPreferencesManager()
    npm.get_preferences("u1")
    npm.mute_all("u1")
    enabled, _, _ = npm.should_notify("u1", "ticket.urgent")
    assert enabled is False


def test_reset_to_defaults():
    npm = NotifPreferencesManager()
    npm.get_preferences("u1")
    npm.mute_all("u1")
    npm.reset_to_defaults("u1")
    enabled, _, _ = npm.should_notify("u1", "ticket.urgent")
    assert enabled is True


def test_unknown_event():
    npm = NotifPreferencesManager()
    enabled, _, freq = npm.should_notify("u1", "nonexistent.event")
    assert enabled is False
    assert freq == NotifFrequency.OFF
