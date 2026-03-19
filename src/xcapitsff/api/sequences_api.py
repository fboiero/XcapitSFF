"""API endpoints for Outreach Sequence management.

Provides CRUD for sequences, enrollment management, step processing,
and performance statistics.
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.sales.outreach import Channel
from xcapitsff.sales.sequences import (
    EnrollmentStatus,
    SequenceStep,
    sequence_engine,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sequences", tags=["Sequences"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class StepRequest(BaseModel):
    step_number: int
    delay_days: int
    channel: str  # email, linkedin, whatsapp
    template_key: str | None = None
    condition: str | None = None


class SequenceCreateRequest(BaseModel):
    name: str
    description: str = ""
    steps: list[StepRequest]
    target_criteria: dict | None = None


class EnrollRequest(BaseModel):
    lead_id: str


class ProcessRequest(BaseModel):
    lead_data: dict[str, dict] | None = None


# ---------------------------------------------------------------------------
# Sequence CRUD
# ---------------------------------------------------------------------------


@router.get("/")
async def list_sequences(
    active_only: bool = Query(default=False),
):
    """List all sequences."""
    sequences = sequence_engine.list_sequences(active_only=active_only)
    return {
        "count": len(sequences),
        "sequences": [_serialize_sequence(s) for s in sequences],
    }


@router.post("/", status_code=201)
async def create_sequence(req: SequenceCreateRequest):
    """Create a custom sequence."""
    steps = []
    for step_req in req.steps:
        try:
            channel = Channel(step_req.channel.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid channel: {step_req.channel}",
            )
        steps.append(
            SequenceStep(
                step_number=step_req.step_number,
                delay_days=step_req.delay_days,
                channel=channel,
                template_key=step_req.template_key,
                condition=step_req.condition,
            )
        )

    try:
        sequence = sequence_engine.create_sequence(
            name=req.name,
            steps=steps,
            target_criteria=req.target_criteria,
            description=req.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _serialize_sequence(sequence)


@router.get("/{sequence_id}")
async def get_sequence(sequence_id: str):
    """Get sequence detail."""
    sequence = sequence_engine.get_sequence(sequence_id)
    if sequence is None:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return _serialize_sequence(sequence)


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------


@router.post("/{sequence_id}/enroll", status_code=201)
async def enroll_lead(sequence_id: str, req: EnrollRequest):
    """Enroll a lead in a sequence."""
    try:
        enrollment = sequence_engine.enroll_lead(
            sequence_id=sequence_id,
            lead_id=req.lead_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _serialize_enrollment(enrollment)


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------


@router.post("/process")
async def process_pending_steps(req: ProcessRequest | None = None):
    """Trigger processing of all pending sequence steps."""
    lead_data = req.lead_data if req else None
    results = sequence_engine.process_pending_steps(
        lead_data_provider=lead_data,
    )
    return {
        "processed": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@router.get("/{sequence_id}/stats")
async def sequence_stats(sequence_id: str):
    """Get sequence performance stats."""
    try:
        stats = sequence_engine.get_sequence_stats(sequence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return stats


# ---------------------------------------------------------------------------
# Lead enrollment lookup (mounted separately to avoid route conflicts)
# ---------------------------------------------------------------------------

leads_sequences_router = APIRouter(tags=["Sequences"])


@leads_sequences_router.get("/leads/{lead_id}/sequences")
async def lead_sequences(lead_id: str):
    """Get all sequences a lead is enrolled in."""
    enrollments = sequence_engine.get_enrollment_status(lead_id)
    return {
        "lead_id": lead_id,
        "count": len(enrollments),
        "enrollments": [_serialize_enrollment(e) for e in enrollments],
    }


# ---------------------------------------------------------------------------
# Enrollment actions
# ---------------------------------------------------------------------------

enrollments_router = APIRouter(prefix="/sequences/enrollments", tags=["Sequences"])


@enrollments_router.post("/{enrollment_id}/pause")
async def pause_enrollment(enrollment_id: str):
    """Pause an active enrollment."""
    try:
        enrollment = sequence_engine.pause_enrollment(enrollment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_enrollment(enrollment)


@enrollments_router.post("/{enrollment_id}/resume")
async def resume_enrollment(enrollment_id: str):
    """Resume a paused enrollment."""
    try:
        enrollment = sequence_engine.resume_enrollment(enrollment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_enrollment(enrollment)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _serialize_sequence(s) -> dict:
    return {
        "sequence_id": s.sequence_id,
        "name": s.name,
        "description": s.description,
        "is_active": s.is_active,
        "target_criteria": s.target_criteria,
        "steps": [
            {
                "step_number": step.step_number,
                "delay_days": step.delay_days,
                "channel": step.channel.value,
                "template_key": step.template_key,
                "condition": step.condition,
            }
            for step in s.steps
        ],
        "created_at": s.created_at.isoformat(),
    }


def _serialize_enrollment(e) -> dict:
    return {
        "enrollment_id": e.enrollment_id,
        "sequence_id": e.sequence_id,
        "lead_id": e.lead_id,
        "current_step": e.current_step,
        "status": e.status.value,
        "enrolled_at": e.enrolled_at.isoformat(),
        "last_step_at": e.last_step_at.isoformat() if e.last_step_at else None,
        "next_step_at": e.next_step_at.isoformat() if e.next_step_at else None,
    }
