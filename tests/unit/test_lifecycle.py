"""Tests for the Lead Lifecycle Tracking system.

Covers:
- LeadEvent and LeadTimeline dataclasses
- Event recording and retrieval
- Timeline construction from events
- Conversion probability calculation across multiple signal combinations
- Event type enum completeness
- Stage mapping from events
- Edge cases (empty timelines, unknown stages, terminal states)
"""

from datetime import datetime, timedelta

import pytest

from xcapitsff.core.models import LeadStage
from xcapitsff.sales.lifecycle import (
    LeadEvent,
    LeadEventType,
    LeadTimeline,
    _EVENT_TO_STAGE,
    _STAGE_BASE_PROB,
    calculate_conversion_probability,
    clear_event_store,
    get_timeline,
    record_event,
)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_event_store():
    """Ensure a clean event store for every test."""
    clear_event_store()
    yield
    clear_event_store()


# -----------------------------------------------------------------------
# 1. LeadEvent dataclass
# -----------------------------------------------------------------------


class TestLeadEvent:
    def test_create_event(self):
        event = LeadEvent(
            event_type=LeadEventType.CREATED,
            lead_id=1,
            timestamp=datetime.now(),
            actor="system",
        )
        assert event.event_type == LeadEventType.CREATED
        assert event.lead_id == 1
        assert event.actor == "system"
        assert event.data is None
        assert event.notes is None

    def test_create_event_with_data_and_notes(self):
        event = LeadEvent(
            event_type=LeadEventType.SCORED,
            lead_id=42,
            timestamp=datetime.now(),
            actor="scoring_engine",
            data={"score_icp": 85.0, "previous_score": 70.0},
            notes="Score improved after engagement",
        )
        assert event.data["score_icp"] == 85.0
        assert event.notes == "Score improved after engagement"


# -----------------------------------------------------------------------
# 2. LeadTimeline dataclass
# -----------------------------------------------------------------------


class TestLeadTimeline:
    def test_default_timeline(self):
        timeline = LeadTimeline(lead_id=1)
        assert timeline.lead_id == 1
        assert timeline.events == []
        assert timeline.current_stage == "raw"
        assert timeline.days_in_pipeline == 0.0
        assert timeline.conversion_probability == 0.0


# -----------------------------------------------------------------------
# 3. Event recording
# -----------------------------------------------------------------------


class TestRecordEvent:
    def test_record_basic_event(self):
        event = record_event(
            lead_id=1,
            event_type=LeadEventType.CREATED,
            actor="importer",
        )
        assert isinstance(event, LeadEvent)
        assert event.lead_id == 1
        assert event.event_type == LeadEventType.CREATED
        assert event.actor == "importer"

    def test_record_event_with_string_type(self):
        event = record_event(
            lead_id=1,
            event_type="scored",
            actor="system",
        )
        assert event.event_type == LeadEventType.SCORED

    def test_record_event_with_data(self):
        event = record_event(
            lead_id=2,
            event_type=LeadEventType.SCORE_UPDATED,
            actor="scoring_engine",
            data={"old_score": 50.0, "new_score": 75.0},
        )
        assert event.data["old_score"] == 50.0
        assert event.data["new_score"] == 75.0

    def test_record_event_with_notes(self):
        event = record_event(
            lead_id=3,
            event_type=LeadEventType.NOTE_ADDED,
            actor="sales_rep",
            notes="Had a productive call with the CTO",
        )
        assert event.notes == "Had a productive call with the CTO"

    def test_record_event_custom_timestamp(self):
        custom_time = datetime(2025, 1, 15, 10, 30, 0)
        event = record_event(
            lead_id=1,
            event_type=LeadEventType.CREATED,
            actor="system",
            timestamp=custom_time,
        )
        assert event.timestamp == custom_time

    def test_multiple_events_for_same_lead(self):
        record_event(lead_id=10, event_type=LeadEventType.CREATED, actor="system")
        record_event(lead_id=10, event_type=LeadEventType.SCORED, actor="engine")
        record_event(lead_id=10, event_type=LeadEventType.QUALIFIED, actor="auto")

        timeline = get_timeline(10)
        assert len(timeline.events) == 3


# -----------------------------------------------------------------------
# 4. Timeline construction
# -----------------------------------------------------------------------


class TestGetTimeline:
    def test_empty_timeline(self):
        timeline = get_timeline(999)
        assert timeline.lead_id == 999
        assert timeline.events == []
        assert timeline.current_stage == "raw"

    def test_timeline_tracks_stage_progression(self):
        base = datetime.now() - timedelta(days=10)
        record_event(
            lead_id=1,
            event_type=LeadEventType.CREATED,
            actor="system",
            timestamp=base,
        )
        record_event(
            lead_id=1,
            event_type=LeadEventType.QUALIFIED,
            actor="auto",
            timestamp=base + timedelta(days=2),
        )
        record_event(
            lead_id=1,
            event_type=LeadEventType.CONTACTED,
            actor="rep",
            timestamp=base + timedelta(days=5),
        )

        timeline = get_timeline(1)
        assert timeline.current_stage == "contacted"
        assert len(timeline.events) == 3

    def test_timeline_days_in_pipeline(self):
        base = datetime.now() - timedelta(days=7)
        record_event(
            lead_id=1,
            event_type=LeadEventType.CREATED,
            actor="system",
            timestamp=base,
        )
        timeline = get_timeline(1)
        # Should be approximately 7 days
        assert 6.9 <= timeline.days_in_pipeline <= 7.1

    def test_timeline_events_sorted_chronologically(self):
        now = datetime.now()
        record_event(
            lead_id=1,
            event_type=LeadEventType.CONTACTED,
            actor="rep",
            timestamp=now,
        )
        record_event(
            lead_id=1,
            event_type=LeadEventType.CREATED,
            actor="system",
            timestamp=now - timedelta(days=5),
        )
        timeline = get_timeline(1)
        assert timeline.events[0].event_type == LeadEventType.CREATED
        assert timeline.events[1].event_type == LeadEventType.CONTACTED

    def test_timeline_won_stage(self):
        base = datetime.now() - timedelta(days=30)
        record_event(lead_id=1, event_type=LeadEventType.CREATED, actor="sys", timestamp=base)
        record_event(lead_id=1, event_type=LeadEventType.WON, actor="rep", timestamp=base + timedelta(days=28))

        timeline = get_timeline(1)
        assert timeline.current_stage == "won"
        assert timeline.conversion_probability == 1.0

    def test_timeline_lost_stage(self):
        base = datetime.now() - timedelta(days=20)
        record_event(lead_id=1, event_type=LeadEventType.CREATED, actor="sys", timestamp=base)
        record_event(lead_id=1, event_type=LeadEventType.LOST, actor="rep", timestamp=base + timedelta(days=15))

        timeline = get_timeline(1)
        assert timeline.current_stage == "lost"
        assert timeline.conversion_probability == 0.0

    def test_timeline_extracts_data_from_events(self):
        """Timeline should extract score_icp, c_level, afinidad from event data."""
        base = datetime.now() - timedelta(days=5)
        record_event(
            lead_id=1,
            event_type=LeadEventType.CREATED,
            actor="sys",
            timestamp=base,
            data={"score_icp": 80.0, "c_level": True, "afinidad": "HIGH"},
        )
        record_event(
            lead_id=1,
            event_type=LeadEventType.QUALIFIED,
            actor="auto",
            timestamp=base + timedelta(days=1),
        )

        timeline = get_timeline(1)
        # Probability should be higher because of high score + c_level + HIGH afinidad
        assert timeline.conversion_probability > 0.15


# -----------------------------------------------------------------------
# 5. Conversion probability
# -----------------------------------------------------------------------


class TestConversionProbability:
    def test_won_returns_one(self):
        assert calculate_conversion_probability({"stage": "won"}) == 1.0

    def test_lost_returns_zero(self):
        assert calculate_conversion_probability({"stage": "lost"}) == 0.0

    def test_raw_low_base(self):
        prob = calculate_conversion_probability({"stage": "raw"})
        assert 0.0 < prob < 0.30

    def test_negotiation_high_base(self):
        prob = calculate_conversion_probability({"stage": "negotiation"})
        assert prob >= 0.70

    def test_high_score_boosts_probability(self):
        low_score = calculate_conversion_probability({"stage": "qualified", "score_icp": 20})
        high_score = calculate_conversion_probability({"stage": "qualified", "score_icp": 90})
        assert high_score > low_score

    def test_interactions_boost_probability(self):
        no_interactions = calculate_conversion_probability({"stage": "contacted", "num_interactions": 0})
        many_interactions = calculate_conversion_probability({"stage": "contacted", "num_interactions": 8})
        assert many_interactions > no_interactions

    def test_c_level_bonus(self):
        no_c = calculate_conversion_probability({"stage": "meeting", "c_level": False})
        with_c = calculate_conversion_probability({"stage": "meeting", "c_level": True})
        assert with_c > no_c

    def test_afinidad_high_boost(self):
        low_af = calculate_conversion_probability({"stage": "proposal", "afinidad": "LOW"})
        high_af = calculate_conversion_probability({"stage": "proposal", "afinidad": "HIGH"})
        assert high_af > low_af

    def test_long_pipeline_penalty(self):
        short = calculate_conversion_probability({"stage": "contacted", "days_in_pipeline": 10})
        long = calculate_conversion_probability({"stage": "contacted", "days_in_pipeline": 180})
        assert short > long

    def test_probability_clamped_to_zero_one(self):
        # Even with extreme negative signals, probability stays >= 0
        prob = calculate_conversion_probability({
            "stage": "raw",
            "score_icp": 0,
            "afinidad": "LOW",
            "days_in_pipeline": 500,
            "num_interactions": 0,
            "c_level": False,
        })
        assert 0.0 <= prob <= 1.0

    def test_probability_with_stage_enum(self):
        prob = calculate_conversion_probability({"stage": LeadStage.PROPOSAL})
        assert prob >= _STAGE_BASE_PROB[LeadStage.PROPOSAL]

    def test_unknown_stage_defaults_to_raw(self):
        prob = calculate_conversion_probability({"stage": "nonexistent"})
        raw_prob = calculate_conversion_probability({"stage": "raw"})
        assert prob == raw_prob

    def test_none_score_does_not_crash(self):
        prob = calculate_conversion_probability({"stage": "qualified", "score_icp": None})
        assert 0.0 <= prob <= 1.0


# -----------------------------------------------------------------------
# 6. Event type enum
# -----------------------------------------------------------------------


class TestLeadEventType:
    def test_all_expected_types_exist(self):
        expected = {
            "created", "scored", "qualified", "contacted",
            "meeting_scheduled", "proposal_sent", "negotiation_started",
            "won", "lost", "reopened", "outreach_sent", "outreach_replied",
            "score_updated", "assigned", "note_added",
        }
        actual = {e.value for e in LeadEventType}
        assert expected == actual

    def test_event_to_stage_mapping_covers_all_types(self):
        for event_type in LeadEventType:
            assert event_type in _EVENT_TO_STAGE


# -----------------------------------------------------------------------
# 7. Reopened leads
# -----------------------------------------------------------------------


class TestReopenedLeads:
    def test_reopen_after_lost(self):
        base = datetime.now() - timedelta(days=30)
        record_event(lead_id=1, event_type=LeadEventType.CREATED, actor="sys", timestamp=base)
        record_event(lead_id=1, event_type=LeadEventType.LOST, actor="rep", timestamp=base + timedelta(days=10))
        record_event(lead_id=1, event_type=LeadEventType.REOPENED, actor="mgr", timestamp=base + timedelta(days=20))

        timeline = get_timeline(1)
        assert timeline.current_stage == "raw"
        # Should have non-zero probability since it's back to raw
        assert timeline.conversion_probability > 0.0
