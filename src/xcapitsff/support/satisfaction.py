"""Customer Satisfaction (CSAT) tracking and analysis.

Tracks satisfaction scores, NPS, and sentiment from ticket interactions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SatisfactionRating(int, Enum):
    VERY_DISSATISFIED = 1
    DISSATISFIED = 2
    NEUTRAL = 3
    SATISFIED = 4
    VERY_SATISFIED = 5


@dataclass
class CSATResponse:
    ticket_id: int
    customer_id: int
    rating: SatisfactionRating
    comment: str = ""
    submitted_at: datetime = field(default_factory=datetime.now)


@dataclass
class NPSResponse:
    customer_id: int
    score: int  # 0-10
    comment: str = ""
    submitted_at: datetime = field(default_factory=datetime.now)

    @property
    def category(self) -> str:
        if self.score >= 9:
            return "promoter"
        if self.score >= 7:
            return "passive"
        return "detractor"


@dataclass
class SatisfactionReport:
    period: str
    csat_responses: int
    csat_average: float
    csat_by_category: dict[str, float]  # category → avg rating
    nps_responses: int
    nps_score: float  # -100 to +100
    nps_promoters: int
    nps_passives: int
    nps_detractors: int
    top_complaints: list[str]
    top_praises: list[str]


class SatisfactionTracker:
    """Tracks and analyzes customer satisfaction."""

    def __init__(self):
        self._csat: list[CSATResponse] = []
        self._nps: list[NPSResponse] = []

    def record_csat(
        self, ticket_id: int, customer_id: int, rating: int, comment: str = ""
    ) -> CSATResponse:
        rating_enum = SatisfactionRating(min(max(rating, 1), 5))
        response = CSATResponse(
            ticket_id=ticket_id,
            customer_id=customer_id,
            rating=rating_enum,
            comment=comment,
        )
        self._csat.append(response)
        return response

    def record_nps(self, customer_id: int, score: int, comment: str = "") -> NPSResponse:
        score = min(max(score, 0), 10)
        response = NPSResponse(customer_id=customer_id, score=score, comment=comment)
        self._nps.append(response)
        return response

    def get_csat_average(self, category: str | None = None) -> float | None:
        responses = self._csat
        if not responses:
            return None
        values = [r.rating.value for r in responses]
        return round(sum(values) / len(values), 2)

    def get_nps_score(self) -> float | None:
        if not self._nps:
            return None
        promoters = sum(1 for r in self._nps if r.category == "promoter")
        detractors = sum(1 for r in self._nps if r.category == "detractor")
        total = len(self._nps)
        return round((promoters - detractors) / total * 100, 1)

    def get_report(self, period: str = "all") -> SatisfactionReport:
        csat_avg = self.get_csat_average() or 0.0
        nps = self.get_nps_score() or 0.0

        promoters = sum(1 for r in self._nps if r.category == "promoter")
        passives = sum(1 for r in self._nps if r.category == "passive")
        detractors = sum(1 for r in self._nps if r.category == "detractor")

        # Extract complaints (rating <= 2) and praises (rating >= 4)
        complaints = [r.comment for r in self._csat if r.rating.value <= 2 and r.comment]
        praises = [r.comment for r in self._csat if r.rating.value >= 4 and r.comment]

        return SatisfactionReport(
            period=period,
            csat_responses=len(self._csat),
            csat_average=csat_avg,
            csat_by_category={},
            nps_responses=len(self._nps),
            nps_score=nps,
            nps_promoters=promoters,
            nps_passives=passives,
            nps_detractors=detractors,
            top_complaints=complaints[:5],
            top_praises=praises[:5],
        )

    def get_customer_satisfaction(self, customer_id: int) -> dict:
        csat = [r for r in self._csat if r.customer_id == customer_id]
        nps = [r for r in self._nps if r.customer_id == customer_id]

        csat_avg = round(sum(r.rating.value for r in csat) / len(csat), 2) if csat else None
        latest_nps = nps[-1].score if nps else None

        return {
            "customer_id": customer_id,
            "csat_count": len(csat),
            "csat_average": csat_avg,
            "latest_nps": latest_nps,
            "nps_category": nps[-1].category if nps else None,
        }


# Singleton
satisfaction_tracker = SatisfactionTracker()
