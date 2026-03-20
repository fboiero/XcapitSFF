"""Tests for the gamification engine and usage insights."""

from __future__ import annotations

from datetime import date

import pytest

from xcapitsff.selfservice.gamification import (
    ACHIEVEMENTS,
    LEVELS,
    Achievement,
    AchievementCategory,
    GamificationEngine,
    UserAchievement,
    _check_threshold,
)
from xcapitsff.selfservice.usage_insights import (
    ALL_FEATURES,
    UsageInsight,
    UsageInsightsEngine,
)


# ===================================================================
# Gamification Engine tests
# ===================================================================


class TestAchievementCatalog:
    """Tests for the pre-built achievement catalogue."""

    def test_all_achievements_defined(self):
        """All 16 achievements are present."""
        assert len(ACHIEVEMENTS) == 16

    def test_unique_ids(self):
        """Each achievement has a unique ID."""
        ids = [a.achievement_id for a in ACHIEVEMENTS]
        assert len(ids) == len(set(ids))

    def test_categories_covered(self):
        """All four categories have at least one achievement."""
        categories = {a.category for a in ACHIEVEMENTS}
        assert AchievementCategory.SALES in categories
        assert AchievementCategory.SUPPORT in categories
        assert AchievementCategory.LEARNING in categories
        assert AchievementCategory.ENGAGEMENT in categories

    def test_points_positive(self):
        """Every achievement has a positive point value."""
        for a in ACHIEVEMENTS:
            assert a.points > 0, f"{a.achievement_id} has non-positive points"

    def test_spanish_names(self):
        """Spot-check a few achievement names are in Spanish."""
        by_id = {a.achievement_id: a for a in ACHIEVEMENTS}
        assert by_id["primer_lead"].name == "Primer Lead"
        assert by_id["leads_10"].name == "Prospector Novato"
        assert by_id["deal_won"].name == "Cerrador"
        assert by_id["primer_ticket"].name == "Primera Respuesta"
        assert by_id["csat_high"].name == "Cliente Feliz"
        assert by_id["daily_login_7"].name == "Constante"


class TestCheckThreshold:
    """Tests for the internal _check_threshold helper."""

    def test_simple_threshold_unlocked(self):
        unlocked, progress = _check_threshold({"leads_created": 10}, "leads_created", 10)
        assert unlocked is True
        assert progress == 100.0

    def test_simple_threshold_in_progress(self):
        unlocked, progress = _check_threshold({"leads_created": 5}, "leads_created", 10)
        assert unlocked is False
        assert progress == 50.0

    def test_csat_unlocked(self):
        unlocked, _ = _check_threshold({"csat_average": 4.8}, "csat_average", 4)
        assert unlocked is True

    def test_csat_not_unlocked(self):
        unlocked, progress = _check_threshold({"csat_average": 3.0}, "csat_average", 4)
        assert unlocked is False
        assert 0 < progress < 100

    def test_boolean_condition(self):
        unlocked, progress = _check_threshold({"wizard_completed": True}, "wizard_completed", 1)
        assert unlocked is True
        assert progress == 100.0


class TestGamificationEngine:
    """Tests for the GamificationEngine class."""

    def setup_method(self):
        self.engine = GamificationEngine()

    def test_check_achievements_unlocks_primer_lead(self):
        newly = self.engine.check_achievements("user1", {"leads_created": 1})
        ids = [a.achievement_id for a in newly]
        assert "primer_lead" in ids

    def test_check_achievements_no_double_unlock(self):
        self.engine.check_achievements("user1", {"leads_created": 1})
        newly = self.engine.check_achievements("user1", {"leads_created": 2})
        ids = [a.achievement_id for a in newly]
        assert "primer_lead" not in ids

    def test_check_achievements_multiple_at_once(self):
        context = {
            "leads_created": 100,
            "outreach_sent": 5,
            "deals_won": 1,
        }
        newly = self.engine.check_achievements("user1", context)
        ids = [a.achievement_id for a in newly]
        assert "primer_lead" in ids
        assert "leads_10" in ids
        assert "leads_100" in ids
        assert "primer_outreach" in ids
        assert "deal_won" in ids

    def test_get_user_achievements_empty(self):
        result = self.engine.get_user_achievements("unknown")
        assert result == []

    def test_get_user_achievements_has_progress(self):
        self.engine.check_achievements("user1", {"leads_created": 5})
        achievements = self.engine.get_user_achievements("user1")
        leads_10 = next(
            (a for a in achievements if a.achievement_id == "leads_10"), None
        )
        assert leads_10 is not None
        assert leads_10.progress == 50.0
        assert leads_10.unlocked_at is None

    def test_get_user_level_novato(self):
        level = self.engine.get_user_level("new_user")
        assert level["level"] == "Novato"
        assert level["points"] == 0

    def test_get_user_level_intermediate(self):
        # Unlock achievements worth 1 + 5 + 20 + 5 = 31 pts → Intermedio
        self.engine.check_achievements("user1", {
            "leads_created": 100,
            "outreach_sent": 1,
        })
        level = self.engine.get_user_level("user1")
        assert level["level"] == "Intermedio"
        assert level["points"] == 31  # primer_lead(1) + leads_10(5) + leads_100(20) + primer_outreach(5)

    def test_get_user_level_progress_percentage(self):
        self.engine.check_achievements("user1", {"leads_created": 1})
        level = self.engine.get_user_level("user1")
        # 1 point, Novato (0-20), next is 21
        assert level["level"] == "Novato"
        assert level["progress_percentage"] == pytest.approx(4.76, abs=0.1)

    def test_leaderboard_ordering(self):
        self.engine.check_achievements("alice", {"leads_created": 100, "deals_won": 1})
        self.engine.check_achievements("bob", {"leads_created": 1})
        board = self.engine.get_leaderboard(limit=10)
        assert len(board) == 2
        assert board[0]["user_id"] == "alice"
        assert board[0]["points"] > board[1]["points"]

    def test_leaderboard_limit(self):
        for i in range(20):
            self.engine.check_achievements(f"user{i}", {"leads_created": i + 1})
        board = self.engine.get_leaderboard(limit=5)
        assert len(board) == 5

    def test_get_all_achievements(self):
        result = self.engine.get_all_achievements()
        assert len(result) == 16
        assert all(isinstance(a, Achievement) for a in result)


# ===================================================================
# Usage Insights tests
# ===================================================================


class TestUsageInsightsEngine:
    """Tests for the UsageInsightsEngine class."""

    def setup_method(self):
        self.engine = UsageInsightsEngine()

    def test_weekly_insights_returns_five(self):
        self.engine.set_tenant_data("t1", {
            "leads_this_week": 20,
            "leads_last_week": 15,
            "avg_resolution_hours_this_week": 4,
            "avg_resolution_hours_last_week": 5,
            "hot_leads_uncontacted": 3,
            "csat_this_week": 4.2,
            "feature_most_used": "leads",
            "feature_least_used": "workflows",
        })
        insights = self.engine.generate_weekly_insights("t1")
        assert len(insights) == 5
        types = [i.insight_type for i in insights]
        assert "leads_qualified" in types
        assert "resolution_time" in types
        assert "hot_leads_uncontacted" in types
        assert "csat_weekly" in types
        assert "feature_usage" in types

    def test_weekly_insights_trend_up(self):
        self.engine.set_tenant_data("t1", {
            "leads_this_week": 20,
            "leads_last_week": 10,
        })
        insights = self.engine.generate_weekly_insights("t1")
        leads_insight = next(i for i in insights if i.insight_type == "leads_qualified")
        assert leads_insight.trend == "up"

    def test_weekly_insights_trend_down(self):
        self.engine.set_tenant_data("t1", {
            "leads_this_week": 5,
            "leads_last_week": 20,
        })
        insights = self.engine.generate_weekly_insights("t1")
        leads_insight = next(i for i in insights if i.insight_type == "leads_qualified")
        assert leads_insight.trend == "down"

    def test_daily_digest_structure(self):
        self.engine.set_tenant_data("t1", {
            "new_leads_today": 10,
            "tickets_resolved_today": 5,
            "outreach_sent_today": 3,
            "meetings_scheduled_today": 2,
            "key_actions_needed": ["Contactar leads hot"],
        })
        digest = self.engine.generate_daily_digest("t1")
        assert digest["tenant_id"] == "t1"
        assert digest["new_leads"] == 10
        assert digest["tickets_resolved"] == 5
        assert digest["outreach_sent"] == 3
        assert digest["meetings_scheduled"] == 2
        assert "Contactar leads hot" in digest["key_actions_needed"]
        assert digest["date"] == date.today().isoformat()

    def test_daily_digest_defaults(self):
        digest = self.engine.generate_daily_digest("unknown")
        assert digest["new_leads"] == 0
        assert digest["tickets_resolved"] == 0
        assert digest["key_actions_needed"] == []

    def test_feature_adoption_all_features(self):
        adoption = self.engine.get_feature_adoption("t1")
        for feature in ALL_FEATURES:
            assert feature in adoption
            assert adoption[feature]["used"] is False
            assert adoption[feature]["usage_count"] == 0
            assert adoption[feature]["last_used"] is None

    def test_feature_adoption_with_data(self):
        self.engine.set_tenant_data("t1", {
            "feature_usage": {
                "leads": {"usage_count": 42, "last_used": "2025-03-15"},
                "tickets": {"usage_count": 10, "last_used": "2025-03-14"},
            },
        })
        adoption = self.engine.get_feature_adoption("t1")
        assert adoption["leads"]["used"] is True
        assert adoption["leads"]["usage_count"] == 42
        assert adoption["leads"]["last_used"] == "2025-03-15"
        assert adoption["outreach"]["used"] is False

    def test_insights_empty_tenant(self):
        """Generating insights for unknown tenant returns safe defaults."""
        insights = self.engine.generate_weekly_insights("nonexistent")
        assert len(insights) == 5
        for i in insights:
            assert isinstance(i, UsageInsight)
