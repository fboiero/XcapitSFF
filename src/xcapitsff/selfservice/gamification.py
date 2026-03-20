"""Gamification engine — achievements, levels, and leaderboards.

Drives user engagement by rewarding key actions across sales, support,
learning, and general engagement.  All user-facing text is in Spanish.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class AchievementCategory(str, Enum):
    SALES = "sales"
    SUPPORT = "support"
    LEARNING = "learning"
    ENGAGEMENT = "engagement"


@dataclass
class Achievement:
    achievement_id: str
    name: str
    description: str
    icon: str
    category: AchievementCategory
    points: int
    condition_type: str
    condition_threshold: int


@dataclass
class UserAchievement:
    user_id: str
    achievement_id: str
    unlocked_at: Optional[datetime] = None
    progress: float = 0.0  # 0-100


# ---------------------------------------------------------------------------
# Pre-built achievements (all in Spanish)
# ---------------------------------------------------------------------------


ACHIEVEMENTS: list[Achievement] = [
    # --- Sales milestones ---
    Achievement(
        achievement_id="primer_lead",
        name="Primer Lead",
        description="Crear tu primer lead",
        icon="🎯",
        category=AchievementCategory.SALES,
        points=1,
        condition_type="leads_created",
        condition_threshold=1,
    ),
    Achievement(
        achievement_id="leads_10",
        name="Prospector Novato",
        description="Tener 10 leads",
        icon="🔍",
        category=AchievementCategory.SALES,
        points=5,
        condition_type="leads_created",
        condition_threshold=10,
    ),
    Achievement(
        achievement_id="leads_100",
        name="Prospector Experto",
        description="Tener 100 leads",
        icon="🏆",
        category=AchievementCategory.SALES,
        points=20,
        condition_type="leads_created",
        condition_threshold=100,
    ),
    Achievement(
        achievement_id="primer_outreach",
        name="Primer Contacto",
        description="Enviar tu primer outreach",
        icon="📧",
        category=AchievementCategory.SALES,
        points=5,
        condition_type="outreach_sent",
        condition_threshold=1,
    ),
    Achievement(
        achievement_id="deal_won",
        name="Cerrador",
        description="Ganar tu primer deal",
        icon="💰",
        category=AchievementCategory.SALES,
        points=50,
        condition_type="deals_won",
        condition_threshold=1,
    ),
    Achievement(
        achievement_id="hot_streak",
        name="Racha Caliente",
        description="5 leads hot consecutivos",
        icon="🔥",
        category=AchievementCategory.SALES,
        points=25,
        condition_type="hot_streak",
        condition_threshold=5,
    ),
    # --- Support milestones ---
    Achievement(
        achievement_id="primer_ticket",
        name="Primera Respuesta",
        description="Responder tu primer ticket",
        icon="🎫",
        category=AchievementCategory.SUPPORT,
        points=1,
        condition_type="tickets_resolved",
        condition_threshold=1,
    ),
    Achievement(
        achievement_id="tickets_50",
        name="Agente Estrella",
        description="Resolver 50 tickets",
        icon="⭐",
        category=AchievementCategory.SUPPORT,
        points=20,
        condition_type="tickets_resolved",
        condition_threshold=50,
    ),
    Achievement(
        achievement_id="sla_perfect",
        name="SLA Perfecto",
        description="Una semana sin breaches",
        icon="✅",
        category=AchievementCategory.SUPPORT,
        points=30,
        condition_type="sla_perfect_weeks",
        condition_threshold=1,
    ),
    Achievement(
        achievement_id="csat_high",
        name="Cliente Feliz",
        description="Promedio CSAT >= 4.5",
        icon="😊",
        category=AchievementCategory.SUPPORT,
        points=25,
        condition_type="csat_average",
        condition_threshold=4,  # threshold is >=4.5 checked via condition_type
    ),
    # --- Learning milestones ---
    Achievement(
        achievement_id="tutorial_complete",
        name="Estudiante",
        description="Completar un tutorial",
        icon="📚",
        category=AchievementCategory.LEARNING,
        points=5,
        condition_type="tutorials_completed",
        condition_threshold=1,
    ),
    Achievement(
        achievement_id="all_tutorials",
        name="Graduado",
        description="Completar todos los tutoriales",
        icon="🎓",
        category=AchievementCategory.LEARNING,
        points=30,
        condition_type="all_tutorials_completed",
        condition_threshold=1,
    ),
    Achievement(
        achievement_id="wizard_done",
        name="Configurado",
        description="Completar el setup wizard",
        icon="🧙",
        category=AchievementCategory.LEARNING,
        points=10,
        condition_type="wizard_completed",
        condition_threshold=1,
    ),
    # --- Engagement milestones ---
    Achievement(
        achievement_id="daily_login_7",
        name="Constante",
        description="7 días consecutivos usando el sistema",
        icon="📅",
        category=AchievementCategory.ENGAGEMENT,
        points=15,
        condition_type="consecutive_days",
        condition_threshold=7,
    ),
    Achievement(
        achievement_id="power_user",
        name="Power User",
        description="Usar 10+ features distintas en una semana",
        icon="⚡",
        category=AchievementCategory.ENGAGEMENT,
        points=20,
        condition_type="features_used_week",
        condition_threshold=10,
    ),
    Achievement(
        achievement_id="health_a",
        name="Workspace Sano",
        description="Health score grade A",
        icon="💚",
        category=AchievementCategory.ENGAGEMENT,
        points=30,
        condition_type="health_grade_a",
        condition_threshold=1,
    ),
]

# Quick lookup by achievement_id
_ACHIEVEMENTS_MAP: dict[str, Achievement] = {a.achievement_id: a for a in ACHIEVEMENTS}


# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------


LEVELS: list[dict] = [
    {"level": "Novato", "min_points": 0, "max_points": 20},
    {"level": "Intermedio", "min_points": 21, "max_points": 75},
    {"level": "Avanzado", "min_points": 76, "max_points": 150},
    {"level": "Experto", "min_points": 151, "max_points": 300},
    {"level": "Master", "min_points": 301, "max_points": float("inf")},
]


# ---------------------------------------------------------------------------
# Condition checkers
# ---------------------------------------------------------------------------


def _check_threshold(context: dict, condition_type: str, threshold: int) -> tuple[bool, float]:
    """Return (unlocked, progress_0_100) for a simple threshold check."""
    value = context.get(condition_type, 0)

    # Special handling for CSAT (threshold means >=4.5)
    if condition_type == "csat_average":
        if isinstance(value, (int, float)) and value >= 4.5:
            return True, 100.0
        progress = min((value / 4.5) * 100, 100.0) if value else 0.0
        return False, progress

    # Special handling for boolean flags
    if condition_type in (
        "all_tutorials_completed",
        "wizard_completed",
        "health_grade_a",
    ):
        if value:
            return True, 100.0
        return False, 0.0

    # General numeric threshold
    if isinstance(value, (int, float)):
        progress = min((value / threshold) * 100, 100.0) if threshold else 100.0
        return value >= threshold, progress

    return False, 0.0


# ---------------------------------------------------------------------------
# Gamification Engine
# ---------------------------------------------------------------------------


class GamificationEngine:
    """Core gamification logic — achievements, levels, leaderboards.

    Uses an in-memory store per instance.  In production this would be
    backed by the database; the interface stays the same.
    """

    def __init__(self) -> None:
        # user_id -> {achievement_id -> UserAchievement}
        self._user_achievements: dict[str, dict[str, UserAchievement]] = {}

    # ------------------------------------------------------------------
    # Achievement management
    # ------------------------------------------------------------------

    def check_achievements(self, user_id: str, context: dict) -> list[Achievement]:
        """Check if any new achievements have been unlocked.

        *context* maps condition_type keys to their current numeric values
        (e.g. ``{"leads_created": 12, "tickets_resolved": 3}``).

        Returns the list of *newly* unlocked achievements.
        """
        user_map = self._user_achievements.setdefault(user_id, {})
        newly_unlocked: list[Achievement] = []

        for achievement in ACHIEVEMENTS:
            existing = user_map.get(achievement.achievement_id)
            already_unlocked = existing is not None and existing.unlocked_at is not None

            unlocked, progress = _check_threshold(
                context,
                achievement.condition_type,
                achievement.condition_threshold,
            )

            if unlocked and not already_unlocked:
                ua = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.achievement_id,
                    unlocked_at=datetime.now(tz=None),
                    progress=100.0,
                )
                user_map[achievement.achievement_id] = ua
                newly_unlocked.append(achievement)
                logger.info(
                    "Achievement unlocked: user=%s achievement=%s",
                    user_id,
                    achievement.achievement_id,
                )
            elif not already_unlocked:
                # Update progress even if not yet unlocked
                ua = UserAchievement(
                    user_id=user_id,
                    achievement_id=achievement.achievement_id,
                    unlocked_at=None,
                    progress=progress,
                )
                user_map[achievement.achievement_id] = ua

        return newly_unlocked

    def get_user_achievements(self, user_id: str) -> list[UserAchievement]:
        """Return all achievements (unlocked and in-progress) for *user_id*."""
        user_map = self._user_achievements.get(user_id, {})
        return list(user_map.values())

    # ------------------------------------------------------------------
    # Levels
    # ------------------------------------------------------------------

    def _total_points(self, user_id: str) -> int:
        """Sum of points for unlocked achievements."""
        user_map = self._user_achievements.get(user_id, {})
        total = 0
        for ua in user_map.values():
            if ua.unlocked_at is not None:
                ach = _ACHIEVEMENTS_MAP.get(ua.achievement_id)
                if ach:
                    total += ach.points
        return total

    def get_user_level(self, user_id: str) -> dict:
        """Return the user's current level, points, and progress to next.

        Returns::

            {
                "level": "Intermedio",
                "points": 42,
                "next_level_points": 75,
                "progress_percentage": 38.18,
            }
        """
        points = self._total_points(user_id)
        current_level = LEVELS[0]

        for lvl in LEVELS:
            if points >= lvl["min_points"]:
                current_level = lvl
            else:
                break

        # Determine next level
        idx = LEVELS.index(current_level)
        if idx < len(LEVELS) - 1:
            next_level = LEVELS[idx + 1]
            next_level_points = next_level["min_points"]
            range_size = next_level_points - current_level["min_points"]
            progress_in_range = points - current_level["min_points"]
            progress_pct = round((progress_in_range / range_size) * 100, 2) if range_size else 100.0
        else:
            next_level_points = current_level["min_points"]
            progress_pct = 100.0

        return {
            "level": current_level["level"],
            "points": points,
            "next_level_points": next_level_points,
            "progress_percentage": progress_pct,
        }

    # ------------------------------------------------------------------
    # Leaderboard
    # ------------------------------------------------------------------

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        """Return the top users by total points."""
        entries: list[dict] = []
        for user_id in self._user_achievements:
            pts = self._total_points(user_id)
            level_info = self.get_user_level(user_id)
            unlocked = sum(
                1
                for ua in self._user_achievements[user_id].values()
                if ua.unlocked_at is not None
            )
            entries.append({
                "user_id": user_id,
                "points": pts,
                "level": level_info["level"],
                "achievements_unlocked": unlocked,
            })

        entries.sort(key=lambda e: e["points"], reverse=True)
        return entries[:limit]

    # ------------------------------------------------------------------
    # Catalogue
    # ------------------------------------------------------------------

    def get_all_achievements(self) -> list[Achievement]:
        """Return the full catalogue of achievements."""
        return list(ACHIEVEMENTS)
