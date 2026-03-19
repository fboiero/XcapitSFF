"""Meeting Scheduler — book and track meetings with leads.

Integrates with the lead lifecycle: when a meeting is scheduled,
the lead advances to "meeting" stage automatically.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class MeetingStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class MeetingType(str, Enum):
    DISCOVERY = "discovery"
    DEMO = "demo"
    PROPOSAL_REVIEW = "proposal_review"
    NEGOTIATION = "negotiation"
    ONBOARDING = "onboarding"
    CHECK_IN = "check_in"
    SUPPORT = "support"


@dataclass
class Meeting:
    meeting_id: str
    lead_id: int | None = None
    customer_id: int | None = None
    title: str = ""
    meeting_type: MeetingType = MeetingType.DISCOVERY
    status: MeetingStatus = MeetingStatus.SCHEDULED
    scheduled_at: datetime | None = None
    duration_minutes: int = 30
    attendees: list[str] = field(default_factory=list)
    location: str = ""  # "zoom", "google_meet", "office", URL
    notes: str = ""
    outcome: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    reminder_sent: bool = False


@dataclass
class AvailabilitySlot:
    start: datetime
    end: datetime
    available: bool = True


class MeetingManager:
    """Manages meeting scheduling and tracking."""

    def __init__(self):
        self._meetings: dict[str, Meeting] = {}
        self._counter = 0
        # Simple availability: weekdays 9am-6pm
        self._working_hours = (9, 18)
        self._slot_duration = 30  # minutes

    def _next_id(self) -> str:
        self._counter += 1
        return f"MTG-{self._counter:06d}"

    def schedule(
        self,
        title: str,
        scheduled_at: datetime,
        meeting_type: MeetingType | str = MeetingType.DISCOVERY,
        lead_id: int | None = None,
        customer_id: int | None = None,
        duration_minutes: int = 30,
        attendees: list[str] | None = None,
        location: str = "zoom",
        notes: str = "",
    ) -> Meeting:
        if isinstance(meeting_type, str):
            meeting_type = MeetingType(meeting_type)

        meeting = Meeting(
            meeting_id=self._next_id(),
            lead_id=lead_id,
            customer_id=customer_id,
            title=title,
            meeting_type=meeting_type,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            attendees=attendees or [],
            location=location,
            notes=notes,
        )
        self._meetings[meeting.meeting_id] = meeting
        logger.info(f"Meeting scheduled: {meeting.meeting_id} — {title} at {scheduled_at}")
        return meeting

    def get_meeting(self, meeting_id: str) -> Meeting | None:
        return self._meetings.get(meeting_id)

    def update_status(self, meeting_id: str, status: MeetingStatus | str, outcome: str = "") -> Meeting | None:
        meeting = self._meetings.get(meeting_id)
        if not meeting:
            return None
        if isinstance(status, str):
            status = MeetingStatus(status)
        meeting.status = status
        if outcome:
            meeting.outcome = outcome
        return meeting

    def get_upcoming(self, days: int = 7) -> list[Meeting]:
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        return sorted(
            [
                m for m in self._meetings.values()
                if m.scheduled_at and now <= m.scheduled_at <= cutoff
                and m.status in (MeetingStatus.SCHEDULED, MeetingStatus.CONFIRMED)
            ],
            key=lambda m: m.scheduled_at,
        )

    def get_for_lead(self, lead_id: int) -> list[Meeting]:
        return [m for m in self._meetings.values() if m.lead_id == lead_id]

    def get_for_customer(self, customer_id: int) -> list[Meeting]:
        return [m for m in self._meetings.values() if m.customer_id == customer_id]

    def get_available_slots(self, date: datetime, duration_minutes: int = 30) -> list[AvailabilitySlot]:
        """Get available time slots for a given date."""
        slots = []
        start_hour, end_hour = self._working_hours
        current = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)

        # Skip weekends
        if current.weekday() >= 5:
            return []

        booked = [
            m for m in self._meetings.values()
            if m.scheduled_at and m.scheduled_at.date() == date.date()
            and m.status in (MeetingStatus.SCHEDULED, MeetingStatus.CONFIRMED)
        ]

        while current + timedelta(minutes=duration_minutes) <= end:
            slot_end = current + timedelta(minutes=duration_minutes)
            is_available = True
            for m in booked:
                m_end = m.scheduled_at + timedelta(minutes=m.duration_minutes)
                if current < m_end and slot_end > m.scheduled_at:
                    is_available = False
                    break
            slots.append(AvailabilitySlot(start=current, end=slot_end, available=is_available))
            current += timedelta(minutes=self._slot_duration)

        return slots

    def get_needs_reminder(self, hours_before: int = 24) -> list[Meeting]:
        """Get meetings that need a reminder sent."""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours_before)
        return [
            m for m in self._meetings.values()
            if m.scheduled_at and now < m.scheduled_at <= cutoff
            and not m.reminder_sent
            and m.status in (MeetingStatus.SCHEDULED, MeetingStatus.CONFIRMED)
        ]

    def get_stats(self) -> dict:
        by_status = {}
        by_type = {}
        for m in self._meetings.values():
            by_status[m.status.value] = by_status.get(m.status.value, 0) + 1
            by_type[m.meeting_type.value] = by_type.get(m.meeting_type.value, 0) + 1

        no_shows = sum(1 for m in self._meetings.values() if m.status == MeetingStatus.NO_SHOW)
        completed = sum(1 for m in self._meetings.values() if m.status == MeetingStatus.COMPLETED)
        total = len(self._meetings)

        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "completion_rate": round(completed / max(total, 1) * 100, 1),
            "no_show_rate": round(no_shows / max(total, 1) * 100, 1),
            "upcoming_7d": len(self.get_upcoming(7)),
        }


# Singleton
meeting_manager = MeetingManager()
