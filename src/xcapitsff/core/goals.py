"""Goals & OKR Tracking System.

Track revenue goals, lead targets, deal quotas, and other objectives
with cascading goal hierarchies and weighted key results (OKR scoring).
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# --- Enums ---


class GoalType(str, Enum):
    REVENUE = "revenue"
    LEADS = "leads"
    DEALS_WON = "deals_won"
    TICKETS_RESOLVED = "tickets_resolved"
    MEETINGS_BOOKED = "meetings_booked"
    OUTREACH_SENT = "outreach_sent"
    CUSTOM = "custom"


class GoalPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class GoalStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    ACHIEVED = "achieved"
    EXCEEDED = "exceeded"


# --- Dataclasses ---


@dataclass
class KeyResult:
    id: str
    goal_id: str
    title: str
    target_value: float
    current_value: float = 0.0
    unit: str = ""
    weight: float = 1.0
    created_at: str = field(default_factory=lambda: datetime.now(tz=None).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=None).isoformat())


@dataclass
class Goal:
    id: str
    tenant_id: str
    title: str
    type: GoalType
    target_value: float
    unit: str
    period: GoalPeriod
    period_start: str
    period_end: str
    user_id: str | None = None
    current_value: float = 0.0
    parent_goal_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(tz=None).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(tz=None).isoformat())

    @property
    def progress_pct(self) -> float:
        """Percentage of target achieved (0-100+)."""
        if self.target_value <= 0:
            return 100.0 if self.current_value > 0 else 0.0
        return round(self.current_value / self.target_value * 100, 2)

    @property
    def status(self) -> GoalStatus:
        """Compute status from progress vs elapsed time."""
        return _compute_status(self.progress_pct, self.period_start, self.period_end)


# --- Status computation ---


def _compute_status(progress_pct: float, period_start: str, period_end: str) -> GoalStatus:
    """Determine goal status based on progress vs time elapsed.

    - exceeded: >= 110%
    - achieved: >= 100%
    - on_track: pace matches or ahead (within 10% behind pace)
    - at_risk: 10-25% behind pace
    - behind: > 25% behind pace
    """
    if progress_pct >= 110:
        return GoalStatus.EXCEEDED
    if progress_pct >= 100:
        return GoalStatus.ACHIEVED

    # Calculate time elapsed percentage
    try:
        start = datetime.fromisoformat(period_start)
        end = datetime.fromisoformat(period_end)
        now = datetime.now(tz=None)

        total_duration = (end - start).total_seconds()
        if total_duration <= 0:
            return GoalStatus.ON_TRACK

        elapsed = (now - start).total_seconds()
        elapsed_pct = max(0.0, min(100.0, elapsed / total_duration * 100))
    except (ValueError, TypeError):
        # If dates are unparseable, base solely on progress
        return GoalStatus.ON_TRACK if progress_pct >= 50 else GoalStatus.BEHIND

    if elapsed_pct == 0:
        return GoalStatus.ON_TRACK

    # How far behind pace is the goal?
    pace_gap = elapsed_pct - progress_pct  # positive = behind pace

    if pace_gap <= 10:
        return GoalStatus.ON_TRACK
    if pace_gap <= 25:
        return GoalStatus.AT_RISK
    return GoalStatus.BEHIND


# --- Manager ---


class GoalManager:
    """In-memory goals and OKR manager."""

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}
        self._key_results: dict[str, KeyResult] = {}

    # --- Goal CRUD ---

    def create(
        self,
        tenant_id: str,
        title: str,
        type: str | GoalType,
        target_value: float,
        unit: str,
        period: str | GoalPeriod,
        period_start: str,
        period_end: str,
        user_id: str | None = None,
        parent_goal_id: str | None = None,
    ) -> Goal:
        if isinstance(type, str):
            type = GoalType(type)
        if isinstance(period, str):
            period = GoalPeriod(period)

        goal_id = f"GOAL-{uuid.uuid4().hex[:8]}"
        goal = Goal(
            id=goal_id,
            tenant_id=tenant_id,
            title=title,
            type=type,
            target_value=target_value,
            unit=unit,
            period=period,
            period_start=period_start,
            period_end=period_end,
            user_id=user_id,
            parent_goal_id=parent_goal_id,
        )

        if parent_goal_id and parent_goal_id not in self._goals:
            raise ValueError(f"Parent goal {parent_goal_id} not found")

        self._goals[goal_id] = goal
        logger.info("Created goal %s: %s (target=%s %s)", goal_id, title, target_value, unit)
        return goal

    def update(self, goal_id: str, **kwargs) -> Goal:
        goal = self._get_or_raise(goal_id)
        now = datetime.now(tz=None).isoformat()

        for key, value in kwargs.items():
            if key == "type" and isinstance(value, str):
                value = GoalType(value)
            elif key == "period" and isinstance(value, str):
                value = GoalPeriod(value)
            if not hasattr(goal, key) or key in ("id", "tenant_id", "created_at"):
                raise ValueError(f"Cannot update field: {key}")
            setattr(goal, key, value)

        goal.updated_at = now
        logger.info("Updated goal %s", goal_id)
        return goal

    def delete(self, goal_id: str) -> bool:
        if goal_id not in self._goals:
            return False
        # Remove associated key results
        kr_ids = [kr.id for kr in self._key_results.values() if kr.goal_id == goal_id]
        for kr_id in kr_ids:
            del self._key_results[kr_id]
        del self._goals[goal_id]
        logger.info("Deleted goal %s", goal_id)
        return True

    def get(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def list_goals(
        self,
        tenant_id: str,
        user_id: str | None = None,
        period: str | GoalPeriod | None = None,
        type: str | GoalType | None = None,
    ) -> list[Goal]:
        if isinstance(period, str):
            period = GoalPeriod(period)
        if isinstance(type, str):
            type = GoalType(type)

        results = [g for g in self._goals.values() if g.tenant_id == tenant_id]

        if user_id is not None:
            results = [g for g in results if g.user_id == user_id]
        if period is not None:
            results = [g for g in results if g.period == period]
        if type is not None:
            results = [g for g in results if g.type == type]

        return sorted(results, key=lambda g: g.created_at, reverse=True)

    # --- Progress tracking ---

    def update_progress(self, goal_id: str, new_value: float) -> Goal:
        goal = self._get_or_raise(goal_id)
        goal.current_value = new_value
        goal.updated_at = datetime.now(tz=None).isoformat()
        logger.info("Goal %s progress updated to %s/%s", goal_id, new_value, goal.target_value)
        return goal

    def increment_progress(self, goal_id: str, delta: float) -> Goal:
        goal = self._get_or_raise(goal_id)
        goal.current_value += delta
        goal.updated_at = datetime.now(tz=None).isoformat()
        logger.info(
            "Goal %s progress incremented by %s to %s/%s",
            goal_id, delta, goal.current_value, goal.target_value,
        )
        return goal

    def get_status(self, goal_id: str) -> GoalStatus:
        goal = self._get_or_raise(goal_id)
        return goal.status

    # --- Key Results (OKR) ---

    def add_key_result(
        self,
        goal_id: str,
        title: str,
        target_value: float,
        unit: str,
        weight: float = 1.0,
    ) -> KeyResult:
        self._get_or_raise(goal_id)
        kr_id = f"KR-{uuid.uuid4().hex[:8]}"
        kr = KeyResult(
            id=kr_id,
            goal_id=goal_id,
            title=title,
            target_value=target_value,
            unit=unit,
            weight=weight,
        )
        self._key_results[kr_id] = kr
        logger.info("Added key result %s to goal %s", kr_id, goal_id)
        return kr

    def update_key_result(self, kr_id: str, current_value: float) -> KeyResult:
        if kr_id not in self._key_results:
            raise ValueError(f"Key result {kr_id} not found")
        kr = self._key_results[kr_id]
        kr.current_value = current_value
        kr.updated_at = datetime.now(tz=None).isoformat()
        logger.info("Key result %s updated to %s/%s", kr_id, current_value, kr.target_value)
        return kr

    def get_key_results(self, goal_id: str) -> list[KeyResult]:
        self._get_or_raise(goal_id)
        return [kr for kr in self._key_results.values() if kr.goal_id == goal_id]

    def get_okr_score(self, goal_id: str) -> float:
        """Compute weighted OKR score (0.0 - 1.0) from key results.

        Each KR contributes: (current / target) * weight.
        Final score = sum(weighted_scores) / sum(weights).
        Capped at 1.0 per KR contribution.
        """
        self._get_or_raise(goal_id)
        krs = self.get_key_results(goal_id)
        if not krs:
            # Fall back to goal-level progress
            goal = self._goals[goal_id]
            if goal.target_value <= 0:
                return 1.0 if goal.current_value > 0 else 0.0
            return min(1.0, round(goal.current_value / goal.target_value, 4))

        total_weight = sum(kr.weight for kr in krs)
        if total_weight <= 0:
            return 0.0

        weighted_sum = 0.0
        for kr in krs:
            if kr.target_value <= 0:
                kr_score = 1.0 if kr.current_value > 0 else 0.0
            else:
                kr_score = min(1.0, kr.current_value / kr.target_value)
            weighted_sum += kr_score * kr.weight

        return round(weighted_sum / total_weight, 4)

    # --- Reporting ---

    def get_team_scorecard(
        self, tenant_id: str, period: str | GoalPeriod | None = None
    ) -> list[dict]:
        """Build a scorecard grouping goals by user with OKR scores."""
        goals = self.list_goals(tenant_id, period=period)
        user_goals: dict[str | None, list[Goal]] = {}
        for g in goals:
            user_goals.setdefault(g.user_id, []).append(g)

        scorecard = []
        for uid, ugoals in user_goals.items():
            scores = [self.get_okr_score(g.id) for g in ugoals]
            avg_score = round(sum(scores) / len(scores), 4) if scores else 0.0
            scorecard.append({
                "user_id": uid,
                "is_team_goal": uid is None,
                "goal_count": len(ugoals),
                "avg_okr_score": avg_score,
                "goals": [
                    {
                        "id": g.id,
                        "title": g.title,
                        "type": g.type.value,
                        "progress_pct": g.progress_pct,
                        "status": g.status.value,
                        "okr_score": self.get_okr_score(g.id),
                    }
                    for g in ugoals
                ],
            })

        return sorted(scorecard, key=lambda s: s["avg_okr_score"], reverse=True)

    def get_goal_tree(self, goal_id: str) -> dict:
        """Return a goal with its parent chain and direct children."""
        goal = self._get_or_raise(goal_id)

        # Build parent chain
        parent = None
        if goal.parent_goal_id and goal.parent_goal_id in self._goals:
            pg = self._goals[goal.parent_goal_id]
            parent = {
                "id": pg.id,
                "title": pg.title,
                "type": pg.type.value,
                "progress_pct": pg.progress_pct,
                "status": pg.status.value,
            }

        # Direct children
        children = [
            {
                "id": g.id,
                "title": g.title,
                "type": g.type.value,
                "progress_pct": g.progress_pct,
                "status": g.status.value,
            }
            for g in self._goals.values()
            if g.parent_goal_id == goal_id
        ]

        return {
            "goal": {
                "id": goal.id,
                "title": goal.title,
                "type": goal.type.value,
                "target_value": goal.target_value,
                "current_value": goal.current_value,
                "unit": goal.unit,
                "progress_pct": goal.progress_pct,
                "status": goal.status.value,
                "okr_score": self.get_okr_score(goal.id),
            },
            "parent": parent,
            "children": children,
        }

    def get_trending(self, tenant_id: str) -> list[Goal]:
        """Return goals that are at risk or behind schedule."""
        return [
            g
            for g in self._goals.values()
            if g.tenant_id == tenant_id and g.status in (GoalStatus.AT_RISK, GoalStatus.BEHIND)
        ]

    # --- Internal helpers ---

    def _get_or_raise(self, goal_id: str) -> Goal:
        goal = self._goals.get(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found")
        return goal


# Module-level singleton
goal_manager = GoalManager()
