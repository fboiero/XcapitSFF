"""Outreach Sequence Engine — automated multi-step messaging campaigns with timing.

This module provides a system for creating and managing automated outreach
sequences that send messages across multiple channels (email, LinkedIn,
WhatsApp) on a timed schedule. Key features:

- Define sequences as ordered lists of steps with delay-based timing.
- Enroll leads into sequences and track their progress.
- Automatically process pending steps when their scheduled time arrives.
- Stop sequences when a lead replies.
- Pre-built sequences for common sales motions (cold outreach, warm nurturing,
  hot fast-track, reactivation).
- Statistics per sequence (completion rate, reply rate, avg steps before reply).

The engine uses the template system from ``outreach.py`` (Channel enum,
``compose_message``) to generate the actual message drafts for each step.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from xcapitsff.sales.outreach import Channel, compose_message

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EnrollmentStatus(str, Enum):
    """Status of a lead's enrollment in a sequence."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    REPLIED = "replied"
    BOUNCED = "bounced"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SequenceStep:
    """A single step within an outreach sequence.

    Attributes:
        step_number: Ordinal position of this step (1-based).
        delay_days: Number of days to wait before executing this step
            (relative to enrollment date for step 1, or relative to
            the previous step's execution for subsequent steps).
        channel: The outreach channel for this step.
        template_key: Template identifier from the outreach registry.
            If ``None``, the engine will auto-select based on lead data.
        condition: Optional condition string. Currently supports
            ``"no_reply"`` — only send if the lead has not replied.
    """

    step_number: int
    delay_days: int
    channel: Channel
    template_key: str | None = None
    condition: str | None = None


@dataclass
class Sequence:
    """An outreach sequence definition.

    Attributes:
        sequence_id: Unique identifier for the sequence.
        name: Human-readable name.
        description: What this sequence does and who it targets.
        steps: Ordered list of steps to execute.
        target_criteria: Dict describing which leads qualify for this
            sequence (e.g., ``{"region": "LATAM", "temperature": "cold"}``).
        is_active: Whether the sequence is available for new enrollments.
        created_at: When the sequence was created.
    """

    sequence_id: str
    name: str
    description: str
    steps: list[SequenceStep]
    target_criteria: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SequenceEnrollment:
    """Tracks a lead's progress through a sequence.

    Attributes:
        enrollment_id: Unique enrollment identifier.
        sequence_id: Which sequence this enrollment belongs to.
        lead_id: The enrolled lead's identifier.
        current_step: The step number currently being processed (starts at 0
            meaning no step has been executed yet).
        status: Current enrollment status.
        enrolled_at: When the lead was enrolled.
        last_step_at: When the last step was executed (``None`` if none yet).
        next_step_at: When the next step is scheduled (``None`` if completed
            or stopped).
    """

    enrollment_id: str
    sequence_id: str
    lead_id: str
    current_step: int = 0
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    enrolled_at: datetime = field(default_factory=datetime.now)
    last_step_at: datetime | None = None
    next_step_at: datetime | None = None


# ---------------------------------------------------------------------------
# Sequence Engine
# ---------------------------------------------------------------------------


class SequenceEngine:
    """Manages outreach sequences, enrollments, and step processing.

    This is an in-memory engine suitable for single-process deployments.
    All sequences and enrollments are stored in dictionaries keyed by their
    respective identifiers.
    """

    def __init__(self) -> None:
        self._sequences: dict[str, Sequence] = {}
        self._enrollments: dict[str, SequenceEnrollment] = {}
        self._seq_counter: int = 0
        self._enr_counter: int = 0

    # -- ID generators ------------------------------------------------------

    def _next_seq_id(self) -> str:
        self._seq_counter += 1
        return f"SEQ-{self._seq_counter:04d}"

    def _next_enr_id(self) -> str:
        self._enr_counter += 1
        return f"ENR-{self._enr_counter:04d}"

    # -- Sequence CRUD ------------------------------------------------------

    def create_sequence(
        self,
        name: str,
        steps: list[SequenceStep],
        target_criteria: dict[str, Any] | None = None,
        description: str = "",
    ) -> Sequence:
        """Create a new outreach sequence.

        Args:
            name: Human-readable sequence name.
            steps: Ordered list of ``SequenceStep`` objects.
            target_criteria: Optional dict for lead filtering.
            description: Optional description.

        Returns:
            The newly created ``Sequence``.

        Raises:
            ValueError: If no steps are provided.
        """
        if not steps:
            raise ValueError("A sequence must have at least one step")

        sequence = Sequence(
            sequence_id=self._next_seq_id(),
            name=name,
            description=description,
            steps=sorted(steps, key=lambda s: s.step_number),
            target_criteria=target_criteria or {},
        )
        self._sequences[sequence.sequence_id] = sequence
        logger.info("Sequence created: %s — %s", sequence.sequence_id, name)
        return sequence

    def get_sequence(self, sequence_id: str) -> Sequence | None:
        """Retrieve a sequence by its identifier."""
        return self._sequences.get(sequence_id)

    def list_sequences(self, active_only: bool = False) -> list[Sequence]:
        """List all sequences, optionally filtering to active ones only."""
        seqs = list(self._sequences.values())
        if active_only:
            seqs = [s for s in seqs if s.is_active]
        return sorted(seqs, key=lambda s: s.created_at, reverse=True)

    # -- Enrollment ---------------------------------------------------------

    def enroll_lead(
        self,
        sequence_id: str,
        lead_id: str,
    ) -> SequenceEnrollment:
        """Enroll a lead into a sequence.

        The first step is scheduled according to its ``delay_days``.

        Args:
            sequence_id: The sequence to enroll in.
            lead_id: Identifier of the lead to enroll.

        Returns:
            The new ``SequenceEnrollment``.

        Raises:
            ValueError: If the sequence is not found or is inactive, or if the
                lead is already actively enrolled in this sequence.
        """
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            raise ValueError(f"Sequence '{sequence_id}' not found")
        if not sequence.is_active:
            raise ValueError(f"Sequence '{sequence_id}' is not active")

        # Prevent duplicate active enrollments in the same sequence
        for enr in self._enrollments.values():
            if (
                enr.sequence_id == sequence_id
                and enr.lead_id == lead_id
                and enr.status == EnrollmentStatus.ACTIVE
            ):
                raise ValueError(
                    f"Lead '{lead_id}' is already actively enrolled in "
                    f"sequence '{sequence_id}'"
                )

        now = datetime.now()
        first_step = sequence.steps[0]
        next_step_at = now + timedelta(days=first_step.delay_days)

        enrollment = SequenceEnrollment(
            enrollment_id=self._next_enr_id(),
            sequence_id=sequence_id,
            lead_id=lead_id,
            current_step=0,
            status=EnrollmentStatus.ACTIVE,
            enrolled_at=now,
            next_step_at=next_step_at,
        )
        self._enrollments[enrollment.enrollment_id] = enrollment
        logger.info(
            "Lead %s enrolled in sequence %s (enrollment %s)",
            lead_id,
            sequence_id,
            enrollment.enrollment_id,
        )
        return enrollment

    def unenroll_lead(self, enrollment_id: str) -> SequenceEnrollment:
        """Remove a lead from a sequence by completing the enrollment.

        Args:
            enrollment_id: The enrollment to terminate.

        Returns:
            The updated ``SequenceEnrollment``.

        Raises:
            ValueError: If the enrollment is not found.
        """
        enrollment = self._enrollments.get(enrollment_id)
        if enrollment is None:
            raise ValueError(f"Enrollment '{enrollment_id}' not found")

        enrollment.status = EnrollmentStatus.COMPLETED
        enrollment.next_step_at = None
        logger.info("Enrollment %s unenrolled", enrollment_id)
        return enrollment

    def pause_enrollment(self, enrollment_id: str) -> SequenceEnrollment:
        """Pause an active enrollment.

        Args:
            enrollment_id: The enrollment to pause.

        Returns:
            The updated ``SequenceEnrollment``.

        Raises:
            ValueError: If not found or not active.
        """
        enrollment = self._enrollments.get(enrollment_id)
        if enrollment is None:
            raise ValueError(f"Enrollment '{enrollment_id}' not found")
        if enrollment.status != EnrollmentStatus.ACTIVE:
            raise ValueError(
                f"Cannot pause enrollment in status '{enrollment.status.value}'"
            )
        enrollment.status = EnrollmentStatus.PAUSED
        logger.info("Enrollment %s paused", enrollment_id)
        return enrollment

    def resume_enrollment(self, enrollment_id: str) -> SequenceEnrollment:
        """Resume a paused enrollment.

        Args:
            enrollment_id: The enrollment to resume.

        Returns:
            The updated ``SequenceEnrollment``.

        Raises:
            ValueError: If not found or not paused.
        """
        enrollment = self._enrollments.get(enrollment_id)
        if enrollment is None:
            raise ValueError(f"Enrollment '{enrollment_id}' not found")
        if enrollment.status != EnrollmentStatus.PAUSED:
            raise ValueError(
                f"Cannot resume enrollment in status '{enrollment.status.value}'"
            )
        enrollment.status = EnrollmentStatus.ACTIVE
        logger.info("Enrollment %s resumed", enrollment_id)
        return enrollment

    # -- Processing ---------------------------------------------------------

    def process_pending_steps(
        self,
        now: datetime | None = None,
        lead_data_provider: dict[str, dict[str, Any]] | None = None,
    ) -> list[dict]:
        """Find and process all enrollments whose next step is due.

        For each enrollment where ``next_step_at <= now``, the engine:
        1. Looks up the next step in the sequence.
        2. Checks any step condition (e.g., ``"no_reply"``).
        3. Generates an outreach draft using ``compose_message``.
        4. Advances the enrollment to the next step or completes it.

        Args:
            now: The current time. Defaults to ``datetime.now()`` if not
                provided (useful for testing with mocked time).
            lead_data_provider: Optional mapping of ``lead_id`` to lead data
                dicts. If not provided, minimal lead data is used.

        Returns:
            A list of dicts, one per processed step, containing enrollment
            info and the generated draft.
        """
        if now is None:
            now = datetime.now()

        if lead_data_provider is None:
            lead_data_provider = {}

        results: list[dict] = []

        for enrollment in list(self._enrollments.values()):
            if enrollment.status != EnrollmentStatus.ACTIVE:
                continue
            if enrollment.next_step_at is None:
                continue
            if enrollment.next_step_at > now:
                continue

            sequence = self._sequences.get(enrollment.sequence_id)
            if sequence is None:
                continue

            # Determine the next step to execute
            next_step_index = enrollment.current_step  # 0-based index
            if next_step_index >= len(sequence.steps):
                # All steps completed
                enrollment.status = EnrollmentStatus.COMPLETED
                enrollment.next_step_at = None
                continue

            step = sequence.steps[next_step_index]

            # Check condition
            if step.condition == "no_reply":
                # If the lead has already replied, skip
                if enrollment.status == EnrollmentStatus.REPLIED:
                    continue

            # Get lead data
            lead_data = lead_data_provider.get(enrollment.lead_id, {})

            # Generate outreach draft
            try:
                draft = compose_message(
                    lead_data,
                    step.channel,
                    template_override=step.template_key,
                )
            except (ValueError, KeyError) as exc:
                logger.warning(
                    "Failed to compose message for enrollment %s step %d: %s",
                    enrollment.enrollment_id,
                    step.step_number,
                    exc,
                )
                continue

            # Record the result
            result = {
                "enrollment_id": enrollment.enrollment_id,
                "sequence_id": enrollment.sequence_id,
                "lead_id": enrollment.lead_id,
                "step_number": step.step_number,
                "channel": step.channel.value,
                "template_key": step.template_key,
                "draft": {
                    "subject": draft.subject,
                    "body": draft.body,
                    "channel": draft.channel.value,
                    "template_used": draft.template_used,
                    "personalization_score": draft.personalization_score,
                },
            }
            results.append(result)

            # Advance the enrollment
            enrollment.current_step = next_step_index + 1
            enrollment.last_step_at = now

            # Schedule the next step or complete
            if enrollment.current_step < len(sequence.steps):
                next_step = sequence.steps[enrollment.current_step]
                enrollment.next_step_at = now + timedelta(
                    days=next_step.delay_days
                )
            else:
                enrollment.status = EnrollmentStatus.COMPLETED
                enrollment.next_step_at = None
                logger.info(
                    "Enrollment %s completed all steps",
                    enrollment.enrollment_id,
                )

        return results

    # -- Lead reply ---------------------------------------------------------

    def mark_replied(self, lead_id: str) -> list[SequenceEnrollment]:
        """Mark all active enrollments for a lead as replied.

        When a lead replies to any outreach, all their active sequences
        should stop to prevent further automated messaging.

        Args:
            lead_id: The lead that replied.

        Returns:
            List of enrollments that were stopped.
        """
        stopped: list[SequenceEnrollment] = []
        for enrollment in self._enrollments.values():
            if (
                enrollment.lead_id == lead_id
                and enrollment.status == EnrollmentStatus.ACTIVE
            ):
                enrollment.status = EnrollmentStatus.REPLIED
                enrollment.next_step_at = None
                stopped.append(enrollment)
                logger.info(
                    "Enrollment %s stopped — lead %s replied",
                    enrollment.enrollment_id,
                    lead_id,
                )
        return stopped

    # -- Status queries -----------------------------------------------------

    def get_enrollment_status(
        self, lead_id: str
    ) -> list[SequenceEnrollment]:
        """Get all enrollments for a given lead.

        Args:
            lead_id: The lead to look up.

        Returns:
            List of ``SequenceEnrollment`` objects for the lead.
        """
        return [
            enr
            for enr in self._enrollments.values()
            if enr.lead_id == lead_id
        ]

    def get_enrollment(self, enrollment_id: str) -> SequenceEnrollment | None:
        """Get a single enrollment by its identifier."""
        return self._enrollments.get(enrollment_id)

    # -- Statistics ---------------------------------------------------------

    def get_sequence_stats(self, sequence_id: str) -> dict:
        """Compute statistics for a sequence.

        Returns a dict with:
        - ``total_enrollments``: Total number of enrollments.
        - ``active``: Currently active enrollments.
        - ``completed``: Enrollments that finished all steps.
        - ``replied``: Enrollments stopped because the lead replied.
        - ``paused``: Currently paused enrollments.
        - ``bounced``: Enrollments that bounced.
        - ``completion_rate``: Percentage of enrollments that completed.
        - ``reply_rate``: Percentage of enrollments where the lead replied.
        - ``avg_steps_before_reply``: Average steps executed before a reply.

        Args:
            sequence_id: The sequence to compute stats for.

        Returns:
            A dict with the statistics.

        Raises:
            ValueError: If the sequence is not found.
        """
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            raise ValueError(f"Sequence '{sequence_id}' not found")

        enrollments = [
            e
            for e in self._enrollments.values()
            if e.sequence_id == sequence_id
        ]

        total = len(enrollments)
        active = sum(
            1 for e in enrollments if e.status == EnrollmentStatus.ACTIVE
        )
        completed = sum(
            1 for e in enrollments if e.status == EnrollmentStatus.COMPLETED
        )
        replied = sum(
            1 for e in enrollments if e.status == EnrollmentStatus.REPLIED
        )
        paused = sum(
            1 for e in enrollments if e.status == EnrollmentStatus.PAUSED
        )
        bounced = sum(
            1 for e in enrollments if e.status == EnrollmentStatus.BOUNCED
        )

        completion_rate = round(completed / total * 100, 1) if total > 0 else 0.0
        reply_rate = round(replied / total * 100, 1) if total > 0 else 0.0

        # Average steps before reply
        replied_enrollments = [
            e for e in enrollments if e.status == EnrollmentStatus.REPLIED
        ]
        if replied_enrollments:
            avg_steps = round(
                sum(e.current_step for e in replied_enrollments)
                / len(replied_enrollments),
                1,
            )
        else:
            avg_steps = 0.0

        return {
            "sequence_id": sequence_id,
            "sequence_name": sequence.name,
            "total_enrollments": total,
            "active": active,
            "completed": completed,
            "replied": replied,
            "paused": paused,
            "bounced": bounced,
            "completion_rate": completion_rate,
            "reply_rate": reply_rate,
            "avg_steps_before_reply": avg_steps,
        }


# ---------------------------------------------------------------------------
# Pre-built sequences
# ---------------------------------------------------------------------------


def _build_prebuilt_sequences(engine: SequenceEngine) -> None:
    """Register pre-built sequences on the given engine."""

    # a. cold_outreach_latam: 3 steps
    engine.create_sequence(
        name="cold_outreach_latam",
        description=(
            "3-step cold outreach for LATAM leads: email intro on day 0, "
            "LinkedIn connect on day 3, email follow-up on day 7."
        ),
        steps=[
            SequenceStep(
                step_number=1,
                delay_days=0,
                channel=Channel.EMAIL,
                template_key="email_warm_nonclevel_latam",
                condition=None,
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
        ],
        target_criteria={"region": "LATAM", "temperature": "cold"},
    )

    # b. warm_nurturing: 4 steps
    engine.create_sequence(
        name="warm_nurturing",
        description=(
            "4-step nurturing sequence for warm leads: email value prop on "
            "day 0, WhatsApp check on day 5, email case study on day 14, "
            "email final on day 30."
        ),
        steps=[
            SequenceStep(
                step_number=1,
                delay_days=0,
                channel=Channel.EMAIL,
                template_key="email_warm_nonclevel_latam",
                condition=None,
            ),
            SequenceStep(
                step_number=2,
                delay_days=5,
                channel=Channel.WHATSAPP,
                template_key="whatsapp_warm",
                condition="no_reply",
            ),
            SequenceStep(
                step_number=3,
                delay_days=14,
                channel=Channel.EMAIL,
                template_key="followup_2",
                condition="no_reply",
            ),
            SequenceStep(
                step_number=4,
                delay_days=30,
                channel=Channel.EMAIL,
                template_key="followup_3",
                condition="no_reply",
            ),
        ],
        target_criteria={"temperature": "warm"},
    )

    # c. hot_fast_track: 2 steps
    engine.create_sequence(
        name="hot_fast_track",
        description=(
            "2-step fast-track for hot leads: direct email on day 0, "
            "personal WhatsApp on day 2."
        ),
        steps=[
            SequenceStep(
                step_number=1,
                delay_days=0,
                channel=Channel.EMAIL,
                template_key="email_hot_clevel_latam",
                condition=None,
            ),
            SequenceStep(
                step_number=2,
                delay_days=2,
                channel=Channel.WHATSAPP,
                template_key="whatsapp_hot",
                condition="no_reply",
            ),
        ],
        target_criteria={"temperature": "hot"},
    )

    # d. reactivation: 3 steps
    engine.create_sequence(
        name="reactivation",
        description=(
            "3-step reactivation for dormant leads: 'we miss you' email on "
            "day 0, LinkedIn update on day 7, last chance email on day 21."
        ),
        steps=[
            SequenceStep(
                step_number=1,
                delay_days=0,
                channel=Channel.EMAIL,
                template_key="followup_1",
                condition=None,
            ),
            SequenceStep(
                step_number=2,
                delay_days=7,
                channel=Channel.LINKEDIN,
                template_key="linkedin_warm",
                condition="no_reply",
            ),
            SequenceStep(
                step_number=3,
                delay_days=21,
                channel=Channel.EMAIL,
                template_key="followup_3",
                condition="no_reply",
            ),
        ],
        target_criteria={"temperature": "cold", "reactivation": True},
    )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

sequence_engine = SequenceEngine()
_build_prebuilt_sequences(sequence_engine)
