"""Tests for the Outreach Sequence Engine.

Covers:
- Sequence creation with steps
- Lead enrollment
- Duplicate enrollment prevention
- Unenroll lead
- Process pending steps (with mocked time)
- Mark replied stops sequence
- Sequence stats (completion rate, reply rate, avg steps)
- Pre-built sequences exist and are valid
- Enrollment status tracking
- Pause and resume enrollment
- Step conditions (no_reply)
- Invalid operations (missing sequence, inactive sequence, etc.)
- Multiple leads and sequences
- Edge cases (empty engine, no pending steps, etc.)
"""

from datetime import datetime, timedelta

import pytest

from xcapitsff.sales.outreach import Channel
from xcapitsff.sales.sequences import (
    EnrollmentStatus,
    Sequence,
    SequenceEngine,
    SequenceEnrollment,
    SequenceStep,
    sequence_engine as global_engine,
)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def engine():
    """Return a fresh SequenceEngine with no pre-built sequences."""
    return SequenceEngine()


@pytest.fixture
def sample_steps():
    """Return a 3-step sequence definition."""
    return [
        SequenceStep(
            step_number=1,
            delay_days=0,
            channel=Channel.EMAIL,
            template_key="email_warm_nonclevel_latam",
        ),
        SequenceStep(
            step_number=2,
            delay_days=3,
            channel=Channel.LINKEDIN,
            template_key="linkedin_cool",
            condition="no_reply",
        ),
        SequenceStep(
            step_number=3,
            delay_days=7,
            channel=Channel.EMAIL,
            template_key="followup_1",
            condition="no_reply",
        ),
    ]


@pytest.fixture
def engine_with_sequence(engine, sample_steps):
    """Return an engine with one sequence already created."""
    seq = engine.create_sequence(
        name="Test Sequence",
        steps=sample_steps,
        target_criteria={"region": "LATAM"},
        description="A test sequence",
    )
    return engine, seq


@pytest.fixture
def lead_data():
    """Sample lead data for message composition."""
    return {
        "contact_name": "Maria Garcia",
        "company_name": "FinCorp SA",
        "region": "LATAM",
        "c_level": False,
        "classification": "warm",
    }


# -----------------------------------------------------------------------
# 1. Sequence creation
# -----------------------------------------------------------------------


class TestCreateSequence:
    def test_create_basic_sequence(self, engine, sample_steps):
        seq = engine.create_sequence(
            name="My Sequence",
            steps=sample_steps,
        )
        assert isinstance(seq, Sequence)
        assert seq.name == "My Sequence"
        assert len(seq.steps) == 3
        assert seq.is_active is True
        assert seq.sequence_id.startswith("SEQ-")

    def test_create_sequence_with_criteria(self, engine, sample_steps):
        seq = engine.create_sequence(
            name="LATAM Outreach",
            steps=sample_steps,
            target_criteria={"region": "LATAM", "temperature": "cold"},
            description="Cold outreach for LATAM",
        )
        assert seq.target_criteria == {"region": "LATAM", "temperature": "cold"}
        assert seq.description == "Cold outreach for LATAM"

    def test_create_sequence_no_steps_raises(self, engine):
        with pytest.raises(ValueError, match="at least one step"):
            engine.create_sequence(name="Empty", steps=[])

    def test_steps_sorted_by_step_number(self, engine):
        steps = [
            SequenceStep(step_number=3, delay_days=7, channel=Channel.EMAIL),
            SequenceStep(step_number=1, delay_days=0, channel=Channel.EMAIL),
            SequenceStep(step_number=2, delay_days=3, channel=Channel.LINKEDIN),
        ]
        seq = engine.create_sequence(name="Sorted", steps=steps)
        assert [s.step_number for s in seq.steps] == [1, 2, 3]

    def test_list_sequences(self, engine, sample_steps):
        engine.create_sequence(name="Seq A", steps=sample_steps)
        engine.create_sequence(name="Seq B", steps=sample_steps)
        seqs = engine.list_sequences()
        assert len(seqs) == 2

    def test_get_sequence(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        found = engine.get_sequence(seq.sequence_id)
        assert found is not None
        assert found.name == "Test Sequence"

    def test_get_sequence_not_found(self, engine):
        assert engine.get_sequence("SEQ-9999") is None


# -----------------------------------------------------------------------
# 2. Enrollment
# -----------------------------------------------------------------------


class TestEnrollment:
    def test_enroll_lead(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")
        assert isinstance(enr, SequenceEnrollment)
        assert enr.lead_id == "lead-001"
        assert enr.sequence_id == seq.sequence_id
        assert enr.status == EnrollmentStatus.ACTIVE
        assert enr.current_step == 0
        assert enr.next_step_at is not None

    def test_enroll_duplicate_raises(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        engine.enroll_lead(seq.sequence_id, "lead-001")
        with pytest.raises(ValueError, match="already actively enrolled"):
            engine.enroll_lead(seq.sequence_id, "lead-001")

    def test_enroll_in_unknown_sequence_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.enroll_lead("SEQ-9999", "lead-001")

    def test_enroll_in_inactive_sequence_raises(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        seq.is_active = False
        with pytest.raises(ValueError, match="not active"):
            engine.enroll_lead(seq.sequence_id, "lead-001")

    def test_unenroll_lead(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")
        result = engine.unenroll_lead(enr.enrollment_id)
        assert result.status == EnrollmentStatus.COMPLETED
        assert result.next_step_at is None

    def test_unenroll_unknown_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.unenroll_lead("ENR-9999")


# -----------------------------------------------------------------------
# 3. Process pending steps (mocked time)
# -----------------------------------------------------------------------


class TestProcessPending:
    def test_process_immediate_step(self, engine_with_sequence, lead_data):
        """Step with delay_days=0 should process immediately."""
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        # Process at current time — step 1 has delay_days=0
        now = datetime.now()
        results = engine.process_pending_steps(
            now=now,
            lead_data_provider={"lead-001": lead_data},
        )
        assert len(results) == 1
        assert results[0]["step_number"] == 1
        assert results[0]["lead_id"] == "lead-001"
        assert results[0]["channel"] == "email"
        assert "draft" in results[0]

    def test_process_advances_enrollment(self, engine_with_sequence, lead_data):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        now = datetime.now()
        engine.process_pending_steps(
            now=now, lead_data_provider={"lead-001": lead_data}
        )

        # Enrollment should have advanced
        updated = engine.get_enrollment(enr.enrollment_id)
        assert updated.current_step == 1
        assert updated.last_step_at == now
        # Next step should be scheduled 3 days out
        assert updated.next_step_at is not None

    def test_process_second_step_after_delay(self, engine_with_sequence, lead_data):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        now = datetime.now()
        # Process step 1
        engine.process_pending_steps(
            now=now, lead_data_provider={"lead-001": lead_data}
        )

        # Process step 2 after 3 days
        future = now + timedelta(days=4)
        results = engine.process_pending_steps(
            now=future, lead_data_provider={"lead-001": lead_data}
        )
        assert len(results) == 1
        assert results[0]["step_number"] == 2
        assert results[0]["channel"] == "linkedin"

    def test_no_pending_steps_returns_empty(self, engine_with_sequence, lead_data):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        now = datetime.now()
        # Process step 1
        engine.process_pending_steps(
            now=now, lead_data_provider={"lead-001": lead_data}
        )

        # Try processing immediately — step 2 is 3 days away
        results = engine.process_pending_steps(
            now=now, lead_data_provider={"lead-001": lead_data}
        )
        assert len(results) == 0

    def test_process_completes_after_all_steps(self, engine, lead_data):
        """A 1-step sequence should complete after processing."""
        step = SequenceStep(
            step_number=1, delay_days=0, channel=Channel.EMAIL
        )
        seq = engine.create_sequence(name="One Step", steps=[step])
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        now = datetime.now()
        results = engine.process_pending_steps(
            now=now, lead_data_provider={"lead-001": lead_data}
        )
        assert len(results) == 1

        updated = engine.get_enrollment(enr.enrollment_id)
        assert updated.status == EnrollmentStatus.COMPLETED
        assert updated.next_step_at is None

    def test_process_with_no_lead_data(self, engine_with_sequence):
        """Processing without lead data should still work (uses defaults)."""
        engine, seq = engine_with_sequence
        engine.enroll_lead(seq.sequence_id, "lead-001")

        now = datetime.now()
        results = engine.process_pending_steps(now=now)
        assert len(results) == 1

    def test_process_empty_engine(self, engine):
        results = engine.process_pending_steps()
        assert results == []


# -----------------------------------------------------------------------
# 4. Mark replied
# -----------------------------------------------------------------------


class TestMarkReplied:
    def test_mark_replied_stops_sequence(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        stopped = engine.mark_replied("lead-001")
        assert len(stopped) == 1
        assert stopped[0].status == EnrollmentStatus.REPLIED
        assert stopped[0].next_step_at is None

    def test_mark_replied_stops_multiple_sequences(self, engine, sample_steps):
        seq1 = engine.create_sequence(name="Seq 1", steps=sample_steps)
        seq2 = engine.create_sequence(name="Seq 2", steps=sample_steps)

        engine.enroll_lead(seq1.sequence_id, "lead-001")
        engine.enroll_lead(seq2.sequence_id, "lead-001")

        stopped = engine.mark_replied("lead-001")
        assert len(stopped) == 2
        for enr in stopped:
            assert enr.status == EnrollmentStatus.REPLIED

    def test_mark_replied_does_not_affect_other_leads(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        engine.enroll_lead(seq.sequence_id, "lead-001")
        engine.enroll_lead(seq.sequence_id, "lead-002")

        engine.mark_replied("lead-001")

        statuses = engine.get_enrollment_status("lead-002")
        assert all(e.status == EnrollmentStatus.ACTIVE for e in statuses)

    def test_mark_replied_no_enrollments_returns_empty(self, engine):
        stopped = engine.mark_replied("lead-nonexistent")
        assert stopped == []

    def test_replied_prevents_further_processing(
        self, engine_with_sequence, lead_data
    ):
        engine, seq = engine_with_sequence
        engine.enroll_lead(seq.sequence_id, "lead-001")

        engine.mark_replied("lead-001")

        now = datetime.now() + timedelta(days=100)
        results = engine.process_pending_steps(
            now=now, lead_data_provider={"lead-001": lead_data}
        )
        assert len(results) == 0


# -----------------------------------------------------------------------
# 5. Sequence stats
# -----------------------------------------------------------------------


class TestSequenceStats:
    def test_stats_empty_sequence(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        stats = engine.get_sequence_stats(seq.sequence_id)
        assert stats["total_enrollments"] == 0
        assert stats["completion_rate"] == 0.0
        assert stats["reply_rate"] == 0.0

    def test_stats_with_enrollments(self, engine_with_sequence, lead_data):
        engine, seq = engine_with_sequence

        # Enroll 3 leads
        engine.enroll_lead(seq.sequence_id, "lead-001")
        engine.enroll_lead(seq.sequence_id, "lead-002")
        engine.enroll_lead(seq.sequence_id, "lead-003")

        stats = engine.get_sequence_stats(seq.sequence_id)
        assert stats["total_enrollments"] == 3
        assert stats["active"] == 3

    def test_stats_reply_rate(self, engine_with_sequence):
        engine, seq = engine_with_sequence

        engine.enroll_lead(seq.sequence_id, "lead-001")
        engine.enroll_lead(seq.sequence_id, "lead-002")

        # Process step 1 for both
        now = datetime.now()
        engine.process_pending_steps(now=now)

        # One lead replies
        engine.mark_replied("lead-001")

        stats = engine.get_sequence_stats(seq.sequence_id)
        assert stats["replied"] == 1
        assert stats["reply_rate"] == 50.0

    def test_stats_avg_steps_before_reply(self, engine, lead_data):
        steps = [
            SequenceStep(step_number=1, delay_days=0, channel=Channel.EMAIL),
            SequenceStep(step_number=2, delay_days=1, channel=Channel.EMAIL),
        ]
        seq = engine.create_sequence(name="Two Step", steps=steps)

        engine.enroll_lead(seq.sequence_id, "lead-001")
        engine.enroll_lead(seq.sequence_id, "lead-002")

        now = datetime.now()
        # Process step 1 for both
        engine.process_pending_steps(
            now=now, lead_data_provider={
                "lead-001": lead_data, "lead-002": lead_data
            }
        )

        # lead-001 replies after step 1
        engine.mark_replied("lead-001")

        # Process step 2 for lead-002
        engine.process_pending_steps(
            now=now + timedelta(days=2),
            lead_data_provider={"lead-002": lead_data},
        )
        engine.mark_replied("lead-002")

        stats = engine.get_sequence_stats(seq.sequence_id)
        assert stats["replied"] >= 1
        assert stats["avg_steps_before_reply"] >= 1.0

    def test_stats_unknown_sequence_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.get_sequence_stats("SEQ-9999")


# -----------------------------------------------------------------------
# 6. Pre-built sequences
# -----------------------------------------------------------------------


class TestPrebuiltSequences:
    def test_prebuilt_sequences_exist(self):
        sequences = global_engine.list_sequences()
        names = {s.name for s in sequences}
        assert "cold_outreach_latam" in names
        assert "warm_nurturing" in names
        assert "hot_fast_track" in names
        assert "reactivation" in names

    def test_cold_outreach_latam_has_3_steps(self):
        sequences = global_engine.list_sequences()
        cold = next(s for s in sequences if s.name == "cold_outreach_latam")
        assert len(cold.steps) == 3

    def test_warm_nurturing_has_4_steps(self):
        sequences = global_engine.list_sequences()
        warm = next(s for s in sequences if s.name == "warm_nurturing")
        assert len(warm.steps) == 4

    def test_hot_fast_track_has_2_steps(self):
        sequences = global_engine.list_sequences()
        hot = next(s for s in sequences if s.name == "hot_fast_track")
        assert len(hot.steps) == 2

    def test_reactivation_has_3_steps(self):
        sequences = global_engine.list_sequences()
        react = next(s for s in sequences if s.name == "reactivation")
        assert len(react.steps) == 3

    def test_all_prebuilt_are_active(self):
        sequences = global_engine.list_sequences()
        for seq in sequences:
            assert seq.is_active is True

    def test_prebuilt_steps_have_valid_channels(self):
        sequences = global_engine.list_sequences()
        for seq in sequences:
            for step in seq.steps:
                assert isinstance(step.channel, Channel)


# -----------------------------------------------------------------------
# 7. Enrollment status tracking
# -----------------------------------------------------------------------


class TestEnrollmentStatus:
    def test_get_enrollment_status(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        engine.enroll_lead(seq.sequence_id, "lead-001")

        statuses = engine.get_enrollment_status("lead-001")
        assert len(statuses) == 1
        assert statuses[0].status == EnrollmentStatus.ACTIVE

    def test_get_enrollment_status_empty(self, engine):
        statuses = engine.get_enrollment_status("lead-nonexistent")
        assert statuses == []

    def test_enrollment_tracks_multiple_sequences(self, engine, sample_steps):
        seq1 = engine.create_sequence(name="Seq 1", steps=sample_steps)
        seq2 = engine.create_sequence(name="Seq 2", steps=sample_steps)

        engine.enroll_lead(seq1.sequence_id, "lead-001")
        engine.enroll_lead(seq2.sequence_id, "lead-001")

        statuses = engine.get_enrollment_status("lead-001")
        assert len(statuses) == 2


# -----------------------------------------------------------------------
# 8. Pause and resume
# -----------------------------------------------------------------------


class TestPauseResume:
    def test_pause_active_enrollment(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        result = engine.pause_enrollment(enr.enrollment_id)
        assert result.status == EnrollmentStatus.PAUSED

    def test_resume_paused_enrollment(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        engine.pause_enrollment(enr.enrollment_id)
        result = engine.resume_enrollment(enr.enrollment_id)
        assert result.status == EnrollmentStatus.ACTIVE

    def test_pause_non_active_raises(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")
        engine.mark_replied("lead-001")

        with pytest.raises(ValueError, match="Cannot pause"):
            engine.pause_enrollment(enr.enrollment_id)

    def test_resume_non_paused_raises(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")

        with pytest.raises(ValueError, match="Cannot resume"):
            engine.resume_enrollment(enr.enrollment_id)

    def test_paused_enrollment_not_processed(
        self, engine_with_sequence, lead_data
    ):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")
        engine.pause_enrollment(enr.enrollment_id)

        now = datetime.now() + timedelta(days=100)
        results = engine.process_pending_steps(
            now=now, lead_data_provider={"lead-001": lead_data}
        )
        assert len(results) == 0

    def test_pause_unknown_enrollment_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.pause_enrollment("ENR-9999")

    def test_resume_unknown_enrollment_raises(self, engine):
        with pytest.raises(ValueError, match="not found"):
            engine.resume_enrollment("ENR-9999")


# -----------------------------------------------------------------------
# 9. SequenceStep dataclass
# -----------------------------------------------------------------------


class TestSequenceStep:
    def test_step_defaults(self):
        step = SequenceStep(
            step_number=1, delay_days=0, channel=Channel.EMAIL
        )
        assert step.template_key is None
        assert step.condition is None

    def test_step_with_all_fields(self):
        step = SequenceStep(
            step_number=2,
            delay_days=5,
            channel=Channel.WHATSAPP,
            template_key="whatsapp_warm",
            condition="no_reply",
        )
        assert step.step_number == 2
        assert step.delay_days == 5
        assert step.channel == Channel.WHATSAPP
        assert step.template_key == "whatsapp_warm"
        assert step.condition == "no_reply"


# -----------------------------------------------------------------------
# 10. Re-enrollment after completion
# -----------------------------------------------------------------------


class TestReenrollment:
    def test_can_reenroll_after_completion(self, engine_with_sequence):
        engine, seq = engine_with_sequence
        enr = engine.enroll_lead(seq.sequence_id, "lead-001")
        engine.unenroll_lead(enr.enrollment_id)

        # Should be able to re-enroll since old enrollment is completed
        new_enr = engine.enroll_lead(seq.sequence_id, "lead-001")
        assert new_enr.enrollment_id != enr.enrollment_id
        assert new_enr.status == EnrollmentStatus.ACTIVE
