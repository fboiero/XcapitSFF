"""Territory Management — assign and balance leads across sales territories.

Territories are geographic/strategic groupings of leads with assigned
sales reps (agents). The system auto-balances lead distribution and
tracks territory performance.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Territory:
    territory_id: str
    name: str
    regions: list[str]  # ["LATAM"] or ["Iberia"] or both
    assigned_reps: list[str]  # agent/rep names
    max_leads: int = 500
    current_leads: int = 0
    score_range: tuple[float, float] | None = None  # optional: only leads in score range
    c_level_only: bool = False
    is_active: bool = True


@dataclass
class TerritoryAssignment:
    lead_id: int
    territory_id: str
    assigned_rep: str
    assigned_at: datetime = field(default_factory=datetime.now)
    reason: str = ""


@dataclass
class TerritoryPerformance:
    territory_id: str
    name: str
    total_leads: int
    qualified_leads: int
    contacted_leads: int
    won_leads: int
    conversion_rate: float
    avg_score: float
    capacity_used: float  # percentage


class TerritoryManager:
    """Manages lead-to-territory assignment and balancing."""

    def __init__(self):
        self._territories: dict[str, Territory] = {}
        self._assignments: list[TerritoryAssignment] = {}
        self._lead_territory: dict[int, str] = {}  # lead_id → territory_id
        self._setup_defaults()

    def _setup_defaults(self):
        defaults = [
            Territory("latam-enterprise", "LATAM Enterprise", ["LATAM"],
                      ["senior_sales_1", "senior_sales_2"], score_range=(70, 100), c_level_only=True),
            Territory("latam-mid", "LATAM Mid-Market", ["LATAM"],
                      ["sales_rep_1", "sales_rep_2", "sales_rep_3"], score_range=(40, 69)),
            Territory("latam-smb", "LATAM SMB", ["LATAM"],
                      ["sales_rep_4", "sales_rep_5"], score_range=(0, 39)),
            Territory("iberia-all", "Iberia", ["Iberia"],
                      ["iberia_rep_1", "iberia_rep_2"]),
        ]
        for t in defaults:
            self._territories[t.territory_id] = t

    def add_territory(self, territory: Territory) -> None:
        self._territories[territory.territory_id] = territory

    def get_territory(self, territory_id: str) -> Territory | None:
        return self._territories.get(territory_id)

    def list_territories(self) -> list[Territory]:
        return list(self._territories.values())

    def assign_lead(self, lead_id: int, lead_data: dict) -> TerritoryAssignment | None:
        """Auto-assign a lead to the best matching territory."""
        region = lead_data.get("region", "LATAM")
        score = lead_data.get("score_icp", 0) or 0
        c_level = lead_data.get("c_level", False)

        candidates = []
        for t in self._territories.values():
            if not t.is_active:
                continue
            if region not in t.regions:
                continue
            if t.c_level_only and not c_level:
                continue
            if t.score_range:
                lo, hi = t.score_range
                if not (lo <= score <= hi):
                    continue
            if t.current_leads >= t.max_leads:
                continue
            candidates.append(t)

        if not candidates:
            return None

        # Pick territory with most capacity
        best = min(candidates, key=lambda t: t.current_leads / max(t.max_leads, 1))

        # Round-robin rep assignment
        rep_idx = best.current_leads % len(best.assigned_reps) if best.assigned_reps else 0
        rep = best.assigned_reps[rep_idx] if best.assigned_reps else "unassigned"

        assignment = TerritoryAssignment(
            lead_id=lead_id,
            territory_id=best.territory_id,
            assigned_rep=rep,
            reason=f"Auto-assigned: region={region}, score={score}",
        )

        best.current_leads += 1
        self._lead_territory[lead_id] = best.territory_id

        logger.info(f"Lead {lead_id} → territory {best.name} → rep {rep}")
        return assignment

    def get_lead_territory(self, lead_id: int) -> str | None:
        return self._lead_territory.get(lead_id)

    def get_stats(self) -> dict:
        stats = []
        for t in self._territories.values():
            stats.append({
                "territory_id": t.territory_id,
                "name": t.name,
                "regions": t.regions,
                "capacity": f"{t.current_leads}/{t.max_leads}",
                "utilization": round(t.current_leads / max(t.max_leads, 1) * 100, 1),
                "reps": len(t.assigned_reps),
                "active": t.is_active,
            })
        return {"territories": stats, "total": len(self._territories)}


# Singleton
territory_manager = TerritoryManager()
