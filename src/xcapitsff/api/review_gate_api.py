"""Review Gate API — manage review requests, approvals, and rejections."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.review_gate import (
    ReviewDecision,
    review_gate_manager,
)

router = APIRouter(prefix="/reviews", tags=["Review Gate"])


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

def _serialize(obj):
    """Convert dataclass instances to JSON-safe dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        d = {}
        for f in obj.__dataclass_fields__:
            v = getattr(obj, f)
            if isinstance(v, datetime):
                d[f] = v.isoformat() if v else None
            elif isinstance(v, list):
                d[f] = [_serialize(i) if hasattr(i, "__dataclass_fields__") else
                        (i.value if hasattr(i, "value") else i) for i in v]
            elif hasattr(v, "value"):  # enum
                d[f] = v.value
            else:
                d[f] = v
        return d
    return obj


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class ApproveBody(BaseModel):
    feedback: Optional[str] = ""
    reviewer_id: str


class RejectBody(BaseModel):
    feedback: str
    reviewer_id: str


class RequestChangesBody(BaseModel):
    feedback: str
    reviewer_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
def list_reviews(
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    reviewer_id: Optional[str] = None,
):
    """List reviews with optional filters."""
    # Get all reviews from the store
    all_reviews = list(review_gate_manager._reviews.values())

    if workspace_id:
        all_reviews = [r for r in all_reviews if r.workspace_id == workspace_id]
    if status:
        try:
            decision = ReviewDecision(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown status: {status}")
        all_reviews = [r for r in all_reviews if r.decision == decision]
    if reviewer_id:
        all_reviews = [r for r in all_reviews if r.reviewer_id == reviewer_id]

    return [_serialize(r) for r in all_reviews]


@router.get("/pending")
def pending_reviews(workspace_id: Optional[str] = None):
    """Get pending reviews (shortcut)."""
    reviews = review_gate_manager.get_pending_reviews(workspace_id=workspace_id)
    return [_serialize(r) for r in reviews]


@router.get("/stats")
def review_stats():
    """Get review statistics."""
    return review_gate_manager.get_stats()


@router.get("/{review_id}")
def get_review(review_id: str):
    """Get review detail."""
    review = review_gate_manager.get_review(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize(review)


@router.post("/{review_id}/approve")
def approve_review(review_id: str, body: ApproveBody):
    """Approve a review."""
    review = review_gate_manager.submit_decision(
        review_id=review_id,
        decision=ReviewDecision.APPROVED,
        feedback=body.feedback or "",
        reviewer_id=body.reviewer_id,
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize(review)


@router.post("/{review_id}/reject")
def reject_review(review_id: str, body: RejectBody):
    """Reject a review."""
    review = review_gate_manager.submit_decision(
        review_id=review_id,
        decision=ReviewDecision.REJECTED,
        feedback=body.feedback,
        reviewer_id=body.reviewer_id,
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize(review)


@router.post("/{review_id}/request-changes")
def request_changes(review_id: str, body: RequestChangesBody):
    """Request changes on a review."""
    review = review_gate_manager.submit_decision(
        review_id=review_id,
        decision=ReviewDecision.CHANGES_REQUESTED,
        feedback=body.feedback,
        reviewer_id=body.reviewer_id,
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return _serialize(review)
