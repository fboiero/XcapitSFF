"""Tests for review gate manager."""

import time

from xcapitsff.core.review_gate import (
    ReviewDecision,
    ReviewGateManager,
)


def test_request_review():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "SPECIFY")
    assert rev.id.startswith("REV-")
    assert rev.workspace_id == "ws-1"
    assert rev.task_id == "task-1"
    assert rev.phase == "SPECIFY"
    assert rev.decision == ReviewDecision.PENDING
    assert rev.decided_at is None


def test_request_review_with_artifacts():
    mgr = ReviewGateManager()
    rev = mgr.request_review(
        "ws-1", "task-1", "PLAN",
        artifact_ids=["ART-0001", "ART-0002"],
    )
    assert rev.artifact_ids == ["ART-0001", "ART-0002"]


def test_request_review_with_reviewer():
    mgr = ReviewGateManager()
    rev = mgr.request_review(
        "ws-1", "task-1", "IMPLEMENT",
        reviewer_id="user-42",
    )
    assert rev.reviewer_id == "user-42"


def test_request_review_priority():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "PLAN", priority="high")
    assert rev.priority == "high"


def test_request_review_default_priority():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "PLAN")
    assert rev.priority == "medium"


def test_submit_approve():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "SPECIFY")
    result = mgr.submit_decision(rev.id, ReviewDecision.APPROVED, "LGTM")
    assert result is not None
    assert result.decision == ReviewDecision.APPROVED
    assert result.feedback == "LGTM"
    assert result.decided_at is not None


def test_submit_reject():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "PLAN")
    result = mgr.submit_decision(rev.id, ReviewDecision.REJECTED, "Needs rework")
    assert result.decision == ReviewDecision.REJECTED
    assert result.feedback == "Needs rework"


def test_submit_changes_requested():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "IMPLEMENT")
    result = mgr.submit_decision(
        rev.id, ReviewDecision.CHANGES_REQUESTED,
        "Fix validation logic",
        reviewer_id="reviewer-1",
    )
    assert result.decision == ReviewDecision.CHANGES_REQUESTED
    assert result.reviewer_id == "reviewer-1"


def test_submit_decision_nonexistent():
    mgr = ReviewGateManager()
    assert mgr.submit_decision("REV-9999", ReviewDecision.APPROVED) is None


def test_submit_decision_sets_decided_at():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "VERIFY")
    assert rev.decided_at is None

    result = mgr.submit_decision(rev.id, ReviewDecision.APPROVED)
    assert result.decided_at is not None
    assert result.decided_at >= rev.created_at


def test_get_review():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "SPECIFY")
    retrieved = mgr.get_review(rev.id)
    assert retrieved is not None
    assert retrieved.id == rev.id


def test_get_review_nonexistent():
    mgr = ReviewGateManager()
    assert mgr.get_review("REV-9999") is None


def test_get_pending_reviews():
    mgr = ReviewGateManager()
    r1 = mgr.request_review("ws-1", "task-1", "SPECIFY")
    r2 = mgr.request_review("ws-1", "task-2", "PLAN")
    mgr.submit_decision(r1.id, ReviewDecision.APPROVED)

    pending = mgr.get_pending_reviews()
    assert len(pending) == 1
    assert pending[0].id == r2.id


def test_get_pending_reviews_by_workspace():
    mgr = ReviewGateManager()
    mgr.request_review("ws-1", "task-1", "SPECIFY")
    mgr.request_review("ws-2", "task-2", "SPECIFY")

    pending_ws1 = mgr.get_pending_reviews(workspace_id="ws-1")
    assert len(pending_ws1) == 1
    assert pending_ws1[0].workspace_id == "ws-1"


def test_get_pending_reviews_by_reviewer():
    mgr = ReviewGateManager()
    mgr.request_review("ws-1", "task-1", "SPECIFY", reviewer_id="alice")
    mgr.request_review("ws-1", "task-2", "PLAN", reviewer_id="bob")
    mgr.request_review("ws-1", "task-3", "IMPLEMENT", reviewer_id="alice")

    alice_pending = mgr.get_pending_reviews(reviewer_id="alice")
    assert len(alice_pending) == 2
    assert all(r.reviewer_id == "alice" for r in alice_pending)


def test_get_reviews_for_task():
    mgr = ReviewGateManager()
    mgr.request_review("ws-1", "task-1", "SPECIFY")
    mgr.request_review("ws-1", "task-1", "PLAN")
    mgr.request_review("ws-1", "task-2", "SPECIFY")

    task1_reviews = mgr.get_reviews_for_task("task-1")
    assert len(task1_reviews) == 2


def test_is_phase_approved_all_approved():
    mgr = ReviewGateManager()
    r1 = mgr.request_review("ws-1", "task-1", "SPECIFY")
    r2 = mgr.request_review("ws-1", "task-2", "SPECIFY")
    mgr.submit_decision(r1.id, ReviewDecision.APPROVED)
    mgr.submit_decision(r2.id, ReviewDecision.APPROVED)

    assert mgr.is_phase_approved("ws-1", "SPECIFY") is True


def test_is_phase_approved_some_pending():
    mgr = ReviewGateManager()
    r1 = mgr.request_review("ws-1", "task-1", "PLAN")
    mgr.request_review("ws-1", "task-2", "PLAN")
    mgr.submit_decision(r1.id, ReviewDecision.APPROVED)

    assert mgr.is_phase_approved("ws-1", "PLAN") is False


def test_is_phase_approved_some_rejected():
    mgr = ReviewGateManager()
    r1 = mgr.request_review("ws-1", "task-1", "IMPLEMENT")
    r2 = mgr.request_review("ws-1", "task-2", "IMPLEMENT")
    mgr.submit_decision(r1.id, ReviewDecision.APPROVED)
    mgr.submit_decision(r2.id, ReviewDecision.REJECTED)

    assert mgr.is_phase_approved("ws-1", "IMPLEMENT") is False


def test_is_phase_approved_no_reviews():
    mgr = ReviewGateManager()
    assert mgr.is_phase_approved("ws-1", "NONEXISTENT") is False


def test_stats_empty():
    mgr = ReviewGateManager()
    stats = mgr.get_stats()
    assert stats["total"] == 0
    assert stats["pending"] == 0
    assert stats["approved"] == 0
    assert stats["rejected"] == 0
    assert stats["avg_decision_hours"] == 0.0


def test_stats_mixed():
    mgr = ReviewGateManager()
    r1 = mgr.request_review("ws-1", "task-1", "SPECIFY")
    r2 = mgr.request_review("ws-1", "task-2", "PLAN")
    r3 = mgr.request_review("ws-1", "task-3", "IMPLEMENT")
    mgr.submit_decision(r1.id, ReviewDecision.APPROVED)
    mgr.submit_decision(r2.id, ReviewDecision.REJECTED)

    stats = mgr.get_stats()
    assert stats["total"] == 3
    assert stats["pending"] == 1
    assert stats["approved"] == 1
    assert stats["rejected"] == 1


def test_stats_avg_decision_hours():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "SPECIFY")
    mgr.submit_decision(rev.id, ReviewDecision.APPROVED)

    stats = mgr.get_stats()
    # Decision was nearly instant, so avg should be close to 0
    assert stats["avg_decision_hours"] >= 0.0
    assert stats["avg_decision_hours"] < 1.0


def test_created_at_set():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "SPECIFY")
    assert rev.created_at is not None


def test_reviewer_id_updated_on_decision():
    mgr = ReviewGateManager()
    rev = mgr.request_review("ws-1", "task-1", "SPECIFY")
    assert rev.reviewer_id is None

    mgr.submit_decision(rev.id, ReviewDecision.APPROVED, reviewer_id="late-reviewer")
    assert rev.reviewer_id == "late-reviewer"
