"""Lead Lifecycle Tracking — records every significant event in a lead's journey.

This module provides a complete lifecycle tracking system that:
- Records timestamped events for every lead interaction and status change.
- Builds a full timeline view of a lead's journey through the pipeline.
- Calculates ML-lite conversion probability based on multiple signals.
- Identifies leads that need human attention.
- Computes pipeline velocity metrics to find bottlenecks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead, LeadStage, OutreachMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


class LeadEventType(str, Enum):
    """All significant events in a lead's lifecycle."""

    CREATED = "created"
    SCORED = "scored"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    MEETING_SCHEDULED = "meeting_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION_STARTED = "negotiation_started"
    WON = "won"
    LOST = "lost"
    REOPENED = "reopened"
    OUTREACH_SENT = "outreach_sent"
    OUTREACH_REPLIED = "outreach_replied"
    SCORE_UPDATED = "score_updated"
    ASSIGNED = "assigned"
    NOTE_ADDED = "note_added"


# Mapping from LeadEventType to the pipeline stage it represents (if any).
_EVENT_TO_STAGE: dict[LeadEventType, LeadStage | None] = {
    LeadEventType.CREATED: LeadStage.RAW,
    LeadEventType.SCORED: None,
    LeadEventType.QUALIFIED: LeadStage.QUALIFIED,
    LeadEventType.CONTACTED: LeadStage.CONTACTED,
    LeadEventType.MEETING_SCHEDULED: LeadStage.MEETING,
    LeadEventType.PROPOSAL_SENT: LeadStage.PROPOSAL,
    LeadEventType.NEGOTIATION_STARTED: LeadStage.NEGOTIATION,
    LeadEventType.WON: LeadStage.WON,
    LeadEventType.LOST: LeadStage.LOST,
    LeadEventType.REOPENED: LeadStage.RAW,
    LeadEventType.OUTREACH_SENT: None,
    LeadEventType.OUTREACH_REPLIED: None,
    LeadEventType.SCORE_UPDATED: None,
    LeadEventType.ASSIGNED: None,
    LeadEventType.NOTE_ADDED: None,
}

# Ordered stages for probability and velocity calculations.
_STAGE_ORDER: list[LeadStage] = [
    LeadStage.RAW,
    LeadStage.QUALIFIED,
    LeadStage.CONTACTED,
    LeadStage.MEETING,
    LeadStage.PROPOSAL,
    LeadStage.NEGOTIATION,
    LeadStage.WON,
]

_STAGE_INDEX: dict[LeadStage, int] = {s: i for i, s in enumerate(_STAGE_ORDER)}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LeadEvent:
    """A single lifecycle event for a lead."""

    event_type: LeadEventType
    lead_id: int
    timestamp: datetime
    actor: str
    data: dict[str, Any] | None = None
    notes: str | None = None


@dataclass
class LeadTimeline:
    """The complete timeline and current status of a lead."""

    lead_id: int
    events: list[LeadEvent] = field(default_factory=list)
    current_stage: str = "raw"
    days_in_pipeline: float = 0.0
    days_in_current_stage: float = 0.0
    conversion_probability: float = 0.0


# ---------------------------------------------------------------------------
# In-memory event store
# ---------------------------------------------------------------------------

# Keyed by lead_id, each value is a list of LeadEvent in chronological order.
_event_store: dict[int, list[LeadEvent]] = {}


def _get_events(lead_id: int) -> list[LeadEvent]:
    """Return the event list for a given lead, creating it if needed."""
    if lead_id not in _event_store:
        _event_store[lead_id] = []
    return _event_store[lead_id]


def clear_event_store() -> None:
    """Clear all events (useful for testing)."""
    _event_store.clear()


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def record_event(
    lead_id: int,
    event_type: LeadEventType | str,
    actor: str = "system",
    data: dict[str, Any] | None = None,
    notes: str | None = None,
    timestamp: datetime | None = None,
) -> LeadEvent:
    """Record a lifecycle event for a lead.

    Args:
        lead_id: The lead's database identifier.
        event_type: The type of event being recorded.
        actor: Who or what triggered this event.
        data: Optional structured data associated with the event.
        notes: Optional free-text notes.
        timestamp: Override for event time (defaults to now).

    Returns:
        The created ``LeadEvent``.
    """
    if isinstance(event_type, str):
        event_type = LeadEventType(event_type)

    event = LeadEvent(
        event_type=event_type,
        lead_id=lead_id,
        timestamp=timestamp or datetime.now(),
        actor=actor,
        data=data,
        notes=notes,
    )

    events = _get_events(lead_id)
    events.append(event)

    logger.info(
        "Lifecycle event recorded: lead=%d type=%s actor=%s",
        lead_id,
        event_type.value,
        actor,
    )
    return event


def get_timeline(lead_id: int) -> LeadTimeline:
    """Build a full timeline for a lead from recorded events.

    Args:
        lead_id: The lead's database identifier.

    Returns:
        A ``LeadTimeline`` with events, stage info, and conversion probability.
    """
    events = list(_get_events(lead_id))
    if not events:
        return LeadTimeline(lead_id=lead_id)

    # Sort chronologically
    events.sort(key=lambda e: e.timestamp)

    # Determine current stage from the most recent stage-changing event
    current_stage = LeadStage.RAW
    last_stage_change_time = events[0].timestamp

    for event in events:
        mapped_stage = _EVENT_TO_STAGE.get(event.event_type)
        if mapped_stage is not None:
            current_stage = mapped_stage
            last_stage_change_time = event.timestamp

    now = datetime.now()
    first_event_time = events[0].timestamp
    days_in_pipeline = (now - first_event_time).total_seconds() / 86400
    days_in_current_stage = (now - last_stage_change_time).total_seconds() / 86400

    # Count interactions for probability
    interaction_types = {
        LeadEventType.CONTACTED,
        LeadEventType.MEETING_SCHEDULED,
        LeadEventType.PROPOSAL_SENT,
        LeadEventType.OUTREACH_SENT,
        LeadEventType.OUTREACH_REPLIED,
    }
    num_interactions = sum(1 for e in events if e.event_type in interaction_types)

    # Build a minimal lead-like dict for probability calculation
    lead_proxy = {
        "stage": current_stage,
        "score_icp": None,
        "c_level": False,
        "afinidad": "MEDIUM",
        "num_interactions": num_interactions,
        "days_in_pipeline": days_in_pipeline,
    }

    # Try to extract richer data from events
    for event in reversed(events):
        if event.data:
            if "score_icp" in event.data and lead_proxy["score_icp"] is None:
                lead_proxy["score_icp"] = event.data["score_icp"]
            if "c_level" in event.data:
                lead_proxy["c_level"] = event.data["c_level"]
            if "afinidad" in event.data:
                lead_proxy["afinidad"] = event.data["afinidad"]

    probability = calculate_conversion_probability(lead_proxy)

    return LeadTimeline(
        lead_id=lead_id,
        events=events,
        current_stage=current_stage.value,
        days_in_pipeline=round(days_in_pipeline, 2),
        days_in_current_stage=round(days_in_current_stage, 2),
        conversion_probability=probability,
    )


# ---------------------------------------------------------------------------
# Conversion probability
# ---------------------------------------------------------------------------

# Base probability per stage (later stages have higher base probability).
_STAGE_BASE_PROB: dict[LeadStage, float] = {
    LeadStage.RAW: 0.05,
    LeadStage.QUALIFIED: 0.15,
    LeadStage.CONTACTED: 0.25,
    LeadStage.MEETING: 0.40,
    LeadStage.PROPOSAL: 0.55,
    LeadStage.NEGOTIATION: 0.70,
    LeadStage.WON: 1.0,
    LeadStage.LOST: 0.0,
}


def calculate_conversion_probability(lead: dict[str, Any]) -> float:
    """Calculate an ML-lite conversion probability for a lead.

    The probability is computed from multiple signals:
    - **Stage** — later pipeline stages have higher base probability.
    - **ICP score** — high scores boost probability.
    - **Interactions** — more touchpoints increase likelihood (saturates).
    - **Time in pipeline** — very long stays decrease probability.
    - **C-level** — executive contacts get a bonus.
    - **Afinidad** — high affinity boosts probability.

    Args:
        lead: A dict-like object with keys: ``stage``, ``score_icp``,
            ``c_level``, ``afinidad``, ``num_interactions``, ``days_in_pipeline``.

    Returns:
        A float between 0.0 and 1.0.
    """
    stage = lead.get("stage", LeadStage.RAW)
    if isinstance(stage, str):
        try:
            stage = LeadStage(stage)
        except ValueError:
            stage = LeadStage.RAW

    # Terminal stages
    if stage == LeadStage.WON:
        return 1.0
    if stage == LeadStage.LOST:
        return 0.0

    # Base from stage
    prob = _STAGE_BASE_PROB.get(stage, 0.05)

    # ICP score boost (0 to +0.15)
    score_icp = lead.get("score_icp")
    if score_icp is not None:
        try:
            score_val = float(score_icp)
            prob += min(score_val / 100.0, 1.0) * 0.15
        except (TypeError, ValueError):
            pass

    # Interaction count boost (0 to +0.10, saturates at 10 interactions)
    num_interactions = lead.get("num_interactions", 0)
    try:
        interactions = int(num_interactions)
        prob += min(interactions / 10.0, 1.0) * 0.10
    except (TypeError, ValueError):
        pass

    # Time decay — penalise leads stuck too long (> 60 days)
    days = lead.get("days_in_pipeline", 0)
    try:
        days_val = float(days)
        if days_val > 60:
            penalty = min((days_val - 60) / 120.0, 0.15)
            prob -= penalty
    except (TypeError, ValueError):
        pass

    # C-level bonus (+0.05)
    if lead.get("c_level"):
        prob += 0.05

    # Afinidad bonus
    afinidad = str(lead.get("afinidad", "MEDIUM")).upper()
    if afinidad == "HIGH":
        prob += 0.05
    elif afinidad == "LOW":
        prob -= 0.03

    # Clamp to [0, 1]
    return round(min(max(prob, 0.0), 1.0), 4)


# ---------------------------------------------------------------------------
# Leads needing attention
# ---------------------------------------------------------------------------


async def get_leads_needing_attention(db: AsyncSession) -> list[dict[str, Any]]:
    """Find leads that need human intervention.

    Criteria:
    - Hot leads (score >= 70) with no outreach in the last 7 days.
    - Leads in contacted/meeting stage with no activity for 14 days.
    - Leads whose score has declined (updated_at recent but score dropped).

    Args:
        db: Async database session.

    Returns:
        A list of dicts, each describing a lead and the reason it needs attention.
    """
    results: list[dict[str, Any]] = []
    now = datetime.now()

    # 1. Hot leads with no recent outreach (7 days)
    seven_days_ago = now - timedelta(days=7)
    hot_leads_q = await db.execute(
        select(Lead).where(
            Lead.score_icp >= 70,
            Lead.stage.notin_([LeadStage.WON.value, LeadStage.LOST.value]),
        )
    )
    hot_leads = list(hot_leads_q.scalars().all())

    for lead in hot_leads:
        # Check most recent outreach
        latest_outreach = await db.execute(
            select(func.max(OutreachMessage.created_at)).where(
                OutreachMessage.lead_id == lead.id
            )
        )
        last_outreach_time = latest_outreach.scalar_one_or_none()

        if last_outreach_time is None or last_outreach_time < seven_days_ago:
            days_since = (
                (now - last_outreach_time).days if last_outreach_time else None
            )
            results.append({
                "lead_id": lead.id,
                "company_name": lead.company_name,
                "stage": lead.stage if isinstance(lead.stage, str) else lead.stage.value,
                "score_icp": lead.score_icp,
                "reason": "hot_lead_no_recent_outreach",
                "days_since_outreach": days_since,
            })

    # 2. Leads in contacted/meeting with no activity for 14 days
    fourteen_days_ago = now - timedelta(days=14)
    stale_q = await db.execute(
        select(Lead).where(
            Lead.stage.in_([LeadStage.CONTACTED.value, LeadStage.MEETING.value]),
            Lead.updated_at < fourteen_days_ago,
        )
    )
    for lead in stale_q.scalars().all():
        results.append({
            "lead_id": lead.id,
            "company_name": lead.company_name,
            "stage": lead.stage if isinstance(lead.stage, str) else lead.stage.value,
            "score_icp": lead.score_icp,
            "reason": "stale_in_active_stage",
            "days_since_update": (now - lead.updated_at).days,
        })

    # 3. Leads with declining scores (score < 50 but were updated recently,
    #    indicating a recent re-score that lowered them)
    recently_updated_low = await db.execute(
        select(Lead).where(
            Lead.score_icp.isnot(None),
            Lead.score_icp < 50,
            Lead.updated_at >= seven_days_ago,
            Lead.stage.notin_([LeadStage.WON.value, LeadStage.LOST.value]),
        )
    )
    for lead in recently_updated_low.scalars().all():
        # Avoid duplicates
        existing_ids = {r["lead_id"] for r in results}
        if lead.id not in existing_ids:
            results.append({
                "lead_id": lead.id,
                "company_name": lead.company_name,
                "stage": lead.stage if isinstance(lead.stage, str) else lead.stage.value,
                "score_icp": lead.score_icp,
                "reason": "declining_score",
            })

    logger.info("Found %d leads needing attention", len(results))
    return results


# ---------------------------------------------------------------------------
# Pipeline velocity metrics
# ---------------------------------------------------------------------------


async def get_velocity_metrics(db: AsyncSession) -> dict[str, Any]:
    """Compute pipeline velocity metrics from the event store and database.

    Metrics:
    - ``avg_days_per_stage``: Average number of days leads spend in each stage.
    - ``fastest_deal_days``: Days for the fastest won deal.
    - ``slowest_deal_days``: Days for the slowest won deal.
    - ``bottleneck_stages``: Stages where leads tend to get stuck the longest.
    - ``total_won``: Number of won deals.
    - ``total_lost``: Number of lost deals.
    - ``avg_pipeline_days``: Average total days in the pipeline for closed deals.

    Args:
        db: Async database session.

    Returns:
        A dict with velocity metrics.
    """
    # Gather stage duration data from the event store
    stage_durations: dict[str, list[float]] = {s.value: [] for s in _STAGE_ORDER}
    deal_durations: list[float] = []

    for lead_id, events in _event_store.items():
        if not events:
            continue

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        current_stage = LeadStage.RAW
        stage_enter_time = sorted_events[0].timestamp

        for event in sorted_events:
            mapped_stage = _EVENT_TO_STAGE.get(event.event_type)
            if mapped_stage is not None and mapped_stage != current_stage:
                # Record time spent in the previous stage
                duration_days = (event.timestamp - stage_enter_time).total_seconds() / 86400
                stage_key = current_stage.value
                if stage_key in stage_durations:
                    stage_durations[stage_key].append(duration_days)
                current_stage = mapped_stage
                stage_enter_time = event.timestamp

        # If the lead reached WON, record total deal duration
        if current_stage == LeadStage.WON:
            total_days = (sorted_events[-1].timestamp - sorted_events[0].timestamp).total_seconds() / 86400
            deal_durations.append(total_days)

    # Also pull summary stats from the database for won/lost counts
    total_won = await db.scalar(
        select(func.count(Lead.id)).where(Lead.stage == LeadStage.WON.value)
    ) or 0
    total_lost = await db.scalar(
        select(func.count(Lead.id)).where(Lead.stage == LeadStage.LOST.value)
    ) or 0

    # Compute averages
    avg_days_per_stage: dict[str, float | None] = {}
    for stage_name, durations in stage_durations.items():
        if durations:
            avg_days_per_stage[stage_name] = round(
                sum(durations) / len(durations), 2
            )
        else:
            avg_days_per_stage[stage_name] = None

    # Find bottleneck stages (highest average duration)
    bottleneck_stages: list[str] = []
    valid_stages = {k: v for k, v in avg_days_per_stage.items() if v is not None}
    if valid_stages:
        max_avg = max(valid_stages.values())  # type: ignore[arg-of]
        bottleneck_stages = [k for k, v in valid_stages.items() if v == max_avg]

    fastest_deal = round(min(deal_durations), 2) if deal_durations else None
    slowest_deal = round(max(deal_durations), 2) if deal_durations else None
    avg_pipeline_days = (
        round(sum(deal_durations) / len(deal_durations), 2)
        if deal_durations
        else None
    )

    return {
        "avg_days_per_stage": avg_days_per_stage,
        "fastest_deal_days": fastest_deal,
        "slowest_deal_days": slowest_deal,
        "bottleneck_stages": bottleneck_stages,
        "total_won": total_won,
        "total_lost": total_lost,
        "avg_pipeline_days": avg_pipeline_days,
    }
