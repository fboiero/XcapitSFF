"""Review Gate — enforces human/agent review before phase transitions.

Every pipeline phase (SPECIFY, PLAN, IMPLEMENT, etc.) can require review
before proceeding. This module tracks review requests, decisions, and
provides approval gating for the orchestration layer.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


def _generate_review_id() -> str:
    """Generate a sequential review ID like REV-0001."""
    _generate_review_id._counter = getattr(_generate_review_id, "_counter", 0) + 1
    return f"REV-{_generate_review_id._counter:04d}"


@dataclass
class ReviewRequest:
    id: str
    workspace_id: str
    task_id: str
    phase: str
    artifact_ids: list[str] = field(default_factory=list)
    reviewer_id: str | None = None
    decision: ReviewDecision = ReviewDecision.PENDING
    feedback: str = ""
    priority: str = "medium"
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: datetime | None = None


class ReviewGateManager:
    """In-memory review gate manager.

    In production, this would persist to a database and integrate with
    notification channels. For now, it's in-memory with full query support.
    """

    def __init__(self):
        self._reviews: dict[str, ReviewRequest] = {}

    def request_review(
        self,
        workspace_id: str,
        task_id: str,
        phase: str,
        artifact_ids: list[str] | None = None,
        reviewer_id: str | None = None,
        priority: str = "medium",
    ) -> ReviewRequest:
        """Create a new review request for a phase."""
        review_id = _generate_review_id()
        review = ReviewRequest(
            id=review_id,
            workspace_id=workspace_id,
            task_id=task_id,
            phase=phase,
            artifact_ids=artifact_ids or [],
            reviewer_id=reviewer_id,
            priority=priority,
        )
        self._reviews[review_id] = review
        logger.info(
            "Review requested %s for phase '%s' in workspace %s",
            review_id, phase, workspace_id,
        )
        return review

    def submit_decision(
        self,
        review_id: str,
        decision: ReviewDecision,
        feedback: str = "",
        reviewer_id: str = "",
    ) -> ReviewRequest | None:
        """Submit a decision for a review request. Sets decided_at timestamp."""
        review = self._reviews.get(review_id)
        if not review:
            return None

        review.decision = decision
        review.feedback = feedback
        if reviewer_id:
            review.reviewer_id = reviewer_id
        review.decided_at = datetime.now()

        logger.info(
            "Review %s decided: %s by %s",
            review_id, decision.value, reviewer_id or review.reviewer_id or "unknown",
        )
        return review

    def get_review(self, review_id: str) -> ReviewRequest | None:
        """Get a review request by ID."""
        return self._reviews.get(review_id)

    def get_pending_reviews(
        self,
        workspace_id: str | None = None,
        reviewer_id: str | None = None,
    ) -> list[ReviewRequest]:
        """Get all pending reviews, optionally filtered by workspace or reviewer."""
        results = [
            r for r in self._reviews.values()
            if r.decision == ReviewDecision.PENDING
        ]
        if workspace_id:
            results = [r for r in results if r.workspace_id == workspace_id]
        if reviewer_id:
            results = [r for r in results if r.reviewer_id == reviewer_id]
        return results

    def get_reviews_for_task(self, task_id: str) -> list[ReviewRequest]:
        """Get all reviews for a specific task."""
        return [
            r for r in self._reviews.values()
            if r.task_id == task_id
        ]

    def is_phase_approved(self, workspace_id: str, phase: str) -> bool:
        """Check if all reviews for a workspace+phase are approved."""
        phase_reviews = [
            r for r in self._reviews.values()
            if r.workspace_id == workspace_id and r.phase == phase
        ]
        if not phase_reviews:
            return False
        return all(r.decision == ReviewDecision.APPROVED for r in phase_reviews)

    def get_stats(self) -> dict:
        """Get review statistics."""
        reviews = list(self._reviews.values())
        total = len(reviews)
        pending = sum(1 for r in reviews if r.decision == ReviewDecision.PENDING)
        approved = sum(1 for r in reviews if r.decision == ReviewDecision.APPROVED)
        rejected = sum(1 for r in reviews if r.decision == ReviewDecision.REJECTED)

        # Calculate average decision time for decided reviews
        decided = [r for r in reviews if r.decided_at is not None]
        if decided:
            total_hours = sum(
                (r.decided_at - r.created_at).total_seconds() / 3600
                for r in decided
            )
            avg_decision_hours = round(total_hours / len(decided), 2)
        else:
            avg_decision_hours = 0.0

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "avg_decision_hours": avg_decision_hours,
        }


# Singleton
review_gate_manager = ReviewGateManager()
