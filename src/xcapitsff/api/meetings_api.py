"""API endpoints for Meeting Scheduler."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.sales.meetings import MeetingStatus, MeetingType, meeting_manager

router = APIRouter(prefix="/meetings", tags=["Meetings"])


class ScheduleMeetingRequest(BaseModel):
    title: str
    scheduled_at: str  # ISO format
    meeting_type: str = "discovery"
    lead_id: int | None = None
    customer_id: int | None = None
    duration_minutes: int = 30
    attendees: list[str] = []
    location: str = "zoom"
    notes: str = ""


class UpdateStatusRequest(BaseModel):
    status: str
    outcome: str = ""


@router.post("/", status_code=201)
async def schedule_meeting(req: ScheduleMeetingRequest):
    meeting = meeting_manager.schedule(
        title=req.title,
        scheduled_at=datetime.fromisoformat(req.scheduled_at),
        meeting_type=req.meeting_type,
        lead_id=req.lead_id,
        customer_id=req.customer_id,
        duration_minutes=req.duration_minutes,
        attendees=req.attendees,
        location=req.location,
        notes=req.notes,
    )
    return {
        "meeting_id": meeting.meeting_id,
        "title": meeting.title,
        "scheduled_at": meeting.scheduled_at.isoformat() if meeting.scheduled_at else None,
        "status": meeting.status.value,
    }


@router.get("/upcoming")
async def upcoming_meetings(days: int = Query(default=7, le=30)):
    meetings = meeting_manager.get_upcoming(days)
    return {
        "count": len(meetings),
        "meetings": [
            {
                "meeting_id": m.meeting_id,
                "title": m.title,
                "type": m.meeting_type.value,
                "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None,
                "duration_minutes": m.duration_minutes,
                "lead_id": m.lead_id,
                "location": m.location,
                "status": m.status.value,
            }
            for m in meetings
        ],
    }


@router.get("/availability")
async def get_availability(date: str, duration: int = Query(default=30)):
    """Get available time slots for a date."""
    dt = datetime.fromisoformat(date)
    slots = meeting_manager.get_available_slots(dt, duration)
    return {
        "date": date,
        "slots": [
            {
                "start": s.start.isoformat(),
                "end": s.end.isoformat(),
                "available": s.available,
            }
            for s in slots
        ],
    }


@router.patch("/{meeting_id}/status")
async def update_meeting_status(meeting_id: str, req: UpdateStatusRequest):
    meeting = meeting_manager.update_status(meeting_id, req.status, req.outcome)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"meeting_id": meeting_id, "status": meeting.status.value}


@router.get("/stats")
async def meeting_stats():
    return meeting_manager.get_stats()


@router.get("/lead/{lead_id}")
async def meetings_for_lead(lead_id: int):
    meetings = meeting_manager.get_for_lead(lead_id)
    return {"lead_id": lead_id, "count": len(meetings), "meetings": [
        {"meeting_id": m.meeting_id, "title": m.title, "status": m.status.value,
         "scheduled_at": m.scheduled_at.isoformat() if m.scheduled_at else None}
        for m in meetings
    ]}
