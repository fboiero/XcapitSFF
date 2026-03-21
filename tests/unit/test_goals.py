"""Tests for Goals & OKR Tracking System."""

import pytest
from datetime import datetime, timedelta

from xcapitsff.core.goals import (
    Goal,
    GoalManager,
    GoalPeriod,
    GoalStatus,
    GoalType,
    KeyResult,
    _compute_status,
)


# --- Fixtures ---


@pytest.fixture
def manager():
    return GoalManager()


@pytest.fixture
def period_dates():
    """Return start/end dates for a period that is ~50% elapsed."""
    now = datetime.now(tz=None)
    start = (now - timedelta(days=15)).isoformat()
    end = (now + timedelta(days=15)).isoformat()
    return start, end


@pytest.fixture
def future_period():
    """Return a period entirely in the future."""
    now = datetime.now(tz=None)
    start = (now + timedelta(days=1)).isoformat()
    end = (now + timedelta(days=31)).isoformat()
    return start, end


@pytest.fixture
def past_period():
    """Return a period entirely in the past."""
    now = datetime.now(tz=None)
    start = (now - timedelta(days=60)).isoformat()
    end = (now - timedelta(days=30)).isoformat()
    return start, end


# --- Goal CRUD ---


def test_create_goal(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Q1 Revenue", type=GoalType.REVENUE,
        target_value=100000, unit="$", period=GoalPeriod.QUARTERLY,
        period_start=start, period_end=end,
    )
    assert goal.id.startswith("GOAL-")
    assert goal.title == "Q1 Revenue"
    assert goal.type == GoalType.REVENUE
    assert goal.target_value == 100000
    assert goal.current_value == 0.0
    assert goal.unit == "$"
    assert goal.period == GoalPeriod.QUARTERLY
    assert goal.tenant_id == "t1"
    assert goal.user_id is None


def test_create_goal_with_string_enums(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Leads Target", type="leads",
        target_value=50, unit="leads", period="monthly",
        period_start=start, period_end=end,
    )
    assert goal.type == GoalType.LEADS
    assert goal.period == GoalPeriod.MONTHLY


def test_create_goal_with_user(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Personal Deals", type=GoalType.DEALS_WON,
        target_value=10, unit="deals", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end, user_id="user-1",
    )
    assert goal.user_id == "user-1"


def test_create_goal_with_parent(manager, period_dates):
    start, end = period_dates
    parent = manager.create(
        tenant_id="t1", title="Team Revenue", type=GoalType.REVENUE,
        target_value=500000, unit="$", period=GoalPeriod.YEARLY,
        period_start=start, period_end=end,
    )
    child = manager.create(
        tenant_id="t1", title="My Revenue", type=GoalType.REVENUE,
        target_value=100000, unit="$", period=GoalPeriod.QUARTERLY,
        period_start=start, period_end=end, user_id="user-1",
        parent_goal_id=parent.id,
    )
    assert child.parent_goal_id == parent.id


def test_create_goal_invalid_parent(manager, period_dates):
    start, end = period_dates
    with pytest.raises(ValueError, match="Parent goal"):
        manager.create(
            tenant_id="t1", title="Orphan", type=GoalType.CUSTOM,
            target_value=10, unit="items", period=GoalPeriod.MONTHLY,
            period_start=start, period_end=end, parent_goal_id="nonexistent",
        )


def test_get_goal(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Test", type=GoalType.LEADS,
        target_value=50, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    fetched = manager.get(goal.id)
    assert fetched is not None
    assert fetched.id == goal.id


def test_get_nonexistent_goal(manager):
    assert manager.get("GOAL-nonexistent") is None


def test_update_goal(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Old Title", type=GoalType.LEADS,
        target_value=50, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    updated = manager.update(goal.id, title="New Title", target_value=100)
    assert updated.title == "New Title"
    assert updated.target_value == 100


def test_update_immutable_fields(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Test", type=GoalType.LEADS,
        target_value=50, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    with pytest.raises(ValueError, match="Cannot update field"):
        manager.update(goal.id, id="new-id")


def test_update_nonexistent_goal(manager):
    with pytest.raises(ValueError, match="not found"):
        manager.update("GOAL-nope", title="X")


def test_delete_goal(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Delete Me", type=GoalType.CUSTOM,
        target_value=10, unit="items", period=GoalPeriod.WEEKLY,
        period_start=start, period_end=end,
    )
    # Add a key result too
    kr = manager.add_key_result(goal.id, "KR1", 5, "items")
    assert manager.delete(goal.id) is True
    assert manager.get(goal.id) is None
    # Key results should also be removed — updating the KR should fail
    with pytest.raises(ValueError, match="not found"):
        manager.update_key_result(kr.id, 3)


def test_delete_nonexistent_goal(manager):
    assert manager.delete("GOAL-nope") is False


def test_list_goals(manager, period_dates):
    start, end = period_dates
    manager.create(tenant_id="t1", title="G1", type=GoalType.REVENUE,
                   target_value=100, unit="$", period=GoalPeriod.MONTHLY,
                   period_start=start, period_end=end)
    manager.create(tenant_id="t1", title="G2", type=GoalType.LEADS,
                   target_value=50, unit="leads", period=GoalPeriod.QUARTERLY,
                   period_start=start, period_end=end)
    manager.create(tenant_id="t2", title="G3", type=GoalType.REVENUE,
                   target_value=200, unit="$", period=GoalPeriod.MONTHLY,
                   period_start=start, period_end=end)

    t1_goals = manager.list_goals("t1")
    assert len(t1_goals) == 2

    t2_goals = manager.list_goals("t2")
    assert len(t2_goals) == 1


def test_list_goals_filter_period(manager, period_dates):
    start, end = period_dates
    manager.create(tenant_id="t1", title="Monthly", type=GoalType.LEADS,
                   target_value=50, unit="leads", period=GoalPeriod.MONTHLY,
                   period_start=start, period_end=end)
    manager.create(tenant_id="t1", title="Quarterly", type=GoalType.LEADS,
                   target_value=150, unit="leads", period=GoalPeriod.QUARTERLY,
                   period_start=start, period_end=end)

    monthly = manager.list_goals("t1", period=GoalPeriod.MONTHLY)
    assert len(monthly) == 1
    assert monthly[0].title == "Monthly"


def test_list_goals_filter_type(manager, period_dates):
    start, end = period_dates
    manager.create(tenant_id="t1", title="Rev", type=GoalType.REVENUE,
                   target_value=100, unit="$", period=GoalPeriod.MONTHLY,
                   period_start=start, period_end=end)
    manager.create(tenant_id="t1", title="Leads", type=GoalType.LEADS,
                   target_value=50, unit="leads", period=GoalPeriod.MONTHLY,
                   period_start=start, period_end=end)

    rev_goals = manager.list_goals("t1", type=GoalType.REVENUE)
    assert len(rev_goals) == 1
    assert rev_goals[0].title == "Rev"


# --- Progress tracking ---


def test_update_progress(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Revenue", type=GoalType.REVENUE,
        target_value=100, unit="$", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    updated = manager.update_progress(goal.id, 50)
    assert updated.current_value == 50
    assert updated.progress_pct == 50.0


def test_increment_progress(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Deals", type=GoalType.DEALS_WON,
        target_value=10, unit="deals", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    manager.increment_progress(goal.id, 3)
    manager.increment_progress(goal.id, 2)
    assert goal.current_value == 5
    assert goal.progress_pct == 50.0


def test_progress_pct_zero_target(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Zero", type=GoalType.CUSTOM,
        target_value=0, unit="x", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    assert goal.progress_pct == 0.0
    manager.update_progress(goal.id, 5)
    assert goal.progress_pct == 100.0


# --- Status computation ---


def test_status_achieved(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Done", type=GoalType.REVENUE,
        target_value=100, unit="$", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    manager.update_progress(goal.id, 100)
    assert manager.get_status(goal.id) == GoalStatus.ACHIEVED


def test_status_exceeded(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Over", type=GoalType.REVENUE,
        target_value=100, unit="$", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    manager.update_progress(goal.id, 115)
    assert manager.get_status(goal.id) == GoalStatus.EXCEEDED


def test_status_on_track_future_period(manager, future_period):
    start, end = future_period
    goal = manager.create(
        tenant_id="t1", title="Future", type=GoalType.LEADS,
        target_value=50, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    # 0 progress but period hasn't started yet — on track
    assert goal.status == GoalStatus.ON_TRACK


def test_status_behind(manager, past_period):
    start, end = past_period
    goal = manager.create(
        tenant_id="t1", title="Behind", type=GoalType.LEADS,
        target_value=100, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    # Period is fully elapsed but 0% progress
    assert goal.status == GoalStatus.BEHIND


def test_compute_status_direct():
    """Test the _compute_status helper directly."""
    now = datetime.now(tz=None)
    start = (now - timedelta(days=50)).isoformat()
    end = (now + timedelta(days=50)).isoformat()
    # ~50% elapsed, 45% progress => on_track (within 10%)
    assert _compute_status(45, start, end) == GoalStatus.ON_TRACK
    # ~50% elapsed, 20% progress => behind (>25% gap)
    assert _compute_status(20, start, end) == GoalStatus.BEHIND
    # 100% done
    assert _compute_status(100, start, end) == GoalStatus.ACHIEVED
    # 115% done
    assert _compute_status(115, start, end) == GoalStatus.EXCEEDED


# --- Key Results / OKR ---


def test_add_key_result(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Revenue", type=GoalType.REVENUE,
        target_value=100000, unit="$", period=GoalPeriod.QUARTERLY,
        period_start=start, period_end=end,
    )
    kr = manager.add_key_result(goal.id, "Close 10 deals", 10, "deals")
    assert kr.id.startswith("KR-")
    assert kr.goal_id == goal.id
    assert kr.target_value == 10
    assert kr.weight == 1.0


def test_update_key_result(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Revenue", type=GoalType.REVENUE,
        target_value=100000, unit="$", period=GoalPeriod.QUARTERLY,
        period_start=start, period_end=end,
    )
    kr = manager.add_key_result(goal.id, "Meetings", 20, "meetings")
    updated = manager.update_key_result(kr.id, 12)
    assert updated.current_value == 12


def test_update_nonexistent_key_result(manager):
    with pytest.raises(ValueError, match="not found"):
        manager.update_key_result("KR-nope", 5)


def test_get_key_results(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Q1", type=GoalType.REVENUE,
        target_value=100000, unit="$", period=GoalPeriod.QUARTERLY,
        period_start=start, period_end=end,
    )
    manager.add_key_result(goal.id, "KR1", 10, "deals")
    manager.add_key_result(goal.id, "KR2", 20, "meetings")
    krs = manager.get_key_results(goal.id)
    assert len(krs) == 2


def test_okr_score_no_key_results(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Simple", type=GoalType.LEADS,
        target_value=100, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    manager.update_progress(goal.id, 75)
    score = manager.get_okr_score(goal.id)
    assert score == 0.75


def test_okr_score_with_key_results(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Revenue", type=GoalType.REVENUE,
        target_value=100000, unit="$", period=GoalPeriod.QUARTERLY,
        period_start=start, period_end=end,
    )
    kr1 = manager.add_key_result(goal.id, "Deals", 10, "deals", weight=2.0)
    kr2 = manager.add_key_result(goal.id, "Meetings", 20, "meetings", weight=1.0)
    manager.update_key_result(kr1.id, 8)   # 80%
    manager.update_key_result(kr2.id, 10)  # 50%

    # Weighted: (0.8 * 2 + 0.5 * 1) / (2 + 1) = 2.1 / 3 = 0.7
    score = manager.get_okr_score(goal.id)
    assert abs(score - 0.7) < 0.01


def test_okr_score_capped_at_1(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Over", type=GoalType.REVENUE,
        target_value=100, unit="$", period=GoalPeriod.MONTHLY,
        period_start=start, period_end=end,
    )
    kr = manager.add_key_result(goal.id, "KR1", 10, "deals")
    manager.update_key_result(kr.id, 20)  # 200% but capped at 1.0
    score = manager.get_okr_score(goal.id)
    assert score == 1.0


# --- Reporting ---


def test_team_scorecard(manager, period_dates):
    start, end = period_dates
    # Team goal
    g1 = manager.create(tenant_id="t1", title="Team Revenue", type=GoalType.REVENUE,
                        target_value=100000, unit="$", period=GoalPeriod.QUARTERLY,
                        period_start=start, period_end=end)
    manager.update_progress(g1.id, 50000)

    # User goals
    g2 = manager.create(tenant_id="t1", title="Alice Deals", type=GoalType.DEALS_WON,
                        target_value=10, unit="deals", period=GoalPeriod.QUARTERLY,
                        period_start=start, period_end=end, user_id="alice")
    manager.update_progress(g2.id, 8)

    g3 = manager.create(tenant_id="t1", title="Bob Leads", type=GoalType.LEADS,
                        target_value=50, unit="leads", period=GoalPeriod.QUARTERLY,
                        period_start=start, period_end=end, user_id="bob")
    manager.update_progress(g3.id, 20)

    scorecard = manager.get_team_scorecard("t1")
    assert len(scorecard) == 3  # team (None) + alice + bob

    # Sorted by score descending — alice (0.8) > team (0.5) > bob (0.4)
    assert scorecard[0]["user_id"] == "alice"
    assert scorecard[0]["avg_okr_score"] == 0.8


def test_goal_tree(manager, period_dates):
    start, end = period_dates
    parent = manager.create(
        tenant_id="t1", title="Company Revenue", type=GoalType.REVENUE,
        target_value=500000, unit="$", period=GoalPeriod.YEARLY,
        period_start=start, period_end=end,
    )
    child1 = manager.create(
        tenant_id="t1", title="Team A", type=GoalType.REVENUE,
        target_value=250000, unit="$", period=GoalPeriod.YEARLY,
        period_start=start, period_end=end, parent_goal_id=parent.id,
    )
    child2 = manager.create(
        tenant_id="t1", title="Team B", type=GoalType.REVENUE,
        target_value=250000, unit="$", period=GoalPeriod.YEARLY,
        period_start=start, period_end=end, parent_goal_id=parent.id,
    )

    tree = manager.get_goal_tree(parent.id)
    assert tree["parent"] is None
    assert len(tree["children"]) == 2
    assert tree["goal"]["title"] == "Company Revenue"

    child_tree = manager.get_goal_tree(child1.id)
    assert child_tree["parent"]["id"] == parent.id
    assert len(child_tree["children"]) == 0


def test_get_trending(manager, past_period, period_dates):
    start_past, end_past = past_period
    start_current, end_current = period_dates

    # This one is behind (past period, 0 progress)
    g1 = manager.create(
        tenant_id="t1", title="Overdue", type=GoalType.LEADS,
        target_value=100, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start_past, period_end=end_past,
    )

    # This one is fine (current period, on track)
    g2 = manager.create(
        tenant_id="t1", title="OnTrack", type=GoalType.LEADS,
        target_value=100, unit="leads", period=GoalPeriod.MONTHLY,
        period_start=start_current, period_end=end_current,
    )
    manager.update_progress(g2.id, 50)

    trending = manager.get_trending("t1")
    trending_ids = [g.id for g in trending]
    assert g1.id in trending_ids
    assert g2.id not in trending_ids


def test_delete_removes_key_results(manager, period_dates):
    start, end = period_dates
    goal = manager.create(
        tenant_id="t1", title="Deletable", type=GoalType.CUSTOM,
        target_value=10, unit="items", period=GoalPeriod.WEEKLY,
        period_start=start, period_end=end,
    )
    kr = manager.add_key_result(goal.id, "KR", 5, "items")
    manager.delete(goal.id)
    with pytest.raises(ValueError, match="not found"):
        manager.update_key_result(kr.id, 3)


def test_goal_all_types(manager, period_dates):
    start, end = period_dates
    for gt in GoalType:
        goal = manager.create(
            tenant_id="t1", title=f"{gt.value} goal", type=gt,
            target_value=10, unit="x", period=GoalPeriod.MONTHLY,
            period_start=start, period_end=end,
        )
        assert goal.type == gt
