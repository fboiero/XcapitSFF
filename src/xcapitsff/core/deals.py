"""Deals Pipeline — stage management, forecasting, conversion tracking.

Provides in-memory deal lifecycle management with pipeline analytics,
revenue forecasting, and lead-to-deal conversion.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


# --- Enums ---


class DealStage(str, Enum):
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class DealPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Default probability by stage
STAGE_PROBABILITY: dict[DealStage, float] = {
    DealStage.PROSPECTING: 10.0,
    DealStage.QUALIFICATION: 25.0,
    DealStage.PROPOSAL: 50.0,
    DealStage.NEGOTIATION: 75.0,
    DealStage.CLOSED_WON: 100.0,
    DealStage.CLOSED_LOST: 0.0,
}

# Valid stage transitions
DEAL_STAGE_TRANSITIONS: dict[DealStage, list[DealStage]] = {
    DealStage.PROSPECTING: [DealStage.QUALIFICATION, DealStage.CLOSED_LOST],
    DealStage.QUALIFICATION: [DealStage.PROPOSAL, DealStage.CLOSED_LOST],
    DealStage.PROPOSAL: [DealStage.NEGOTIATION, DealStage.CLOSED_LOST],
    DealStage.NEGOTIATION: [DealStage.CLOSED_WON, DealStage.CLOSED_LOST],
    DealStage.CLOSED_WON: [],
    DealStage.CLOSED_LOST: [DealStage.PROSPECTING],
}


# --- Dataclass ---


@dataclass
class Deal:
    id: str
    tenant_id: str
    name: str
    stage: DealStage
    priority: DealPriority
    amount: float
    currency: str = "USD"
    probability: float = 0.0
    expected_close_date: str = ""
    owner_id: str = ""
    company_id: str | None = None
    contact_id: str | None = None
    lead_id: str | None = None
    tags: list[str] = field(default_factory=list)
    custom_fields: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    closed_at: str | None = None
    lost_reason: str | None = None


# --- Manager ---


class DealManager:
    """In-memory deal pipeline manager."""

    def __init__(self) -> None:
        self._deals: dict[str, Deal] = {}

    def create(
        self,
        tenant_id: str,
        name: str,
        amount: float,
        *,
        stage: DealStage = DealStage.PROSPECTING,
        priority: DealPriority = DealPriority.MEDIUM,
        currency: str = "USD",
        probability: float | None = None,
        expected_close_date: str = "",
        owner_id: str = "",
        company_id: str | None = None,
        contact_id: str | None = None,
        lead_id: str | None = None,
        tags: list[str] | None = None,
        custom_fields: dict | None = None,
    ) -> Deal:
        now = datetime.now(tz=None).isoformat()
        deal = Deal(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            stage=stage,
            priority=priority,
            amount=amount,
            currency=currency,
            probability=probability if probability is not None else STAGE_PROBABILITY.get(stage, 0.0),
            expected_close_date=expected_close_date,
            owner_id=owner_id,
            company_id=company_id,
            contact_id=contact_id,
            lead_id=lead_id,
            tags=tags or [],
            custom_fields=custom_fields or {},
            created_at=now,
            updated_at=now,
        )
        self._deals[deal.id] = deal
        logger.info("Deal created: id=%s name=%s amount=%.2f", deal.id, name, amount)
        return deal

    def update(self, deal_id: str, **kwargs) -> Deal:
        deal = self._deals.get(deal_id)
        if not deal:
            raise KeyError(f"Deal not found: {deal_id}")
        for key, value in kwargs.items():
            if hasattr(deal, key) and key != "id":
                setattr(deal, key, value)
        deal.updated_at = datetime.now(tz=None).isoformat()
        logger.info("Deal updated: id=%s fields=%s", deal_id, list(kwargs.keys()))
        return deal

    def delete(self, deal_id: str) -> bool:
        if deal_id not in self._deals:
            return False
        del self._deals[deal_id]
        logger.info("Deal deleted: id=%s", deal_id)
        return True

    def get(self, deal_id: str) -> Deal:
        deal = self._deals.get(deal_id)
        if not deal:
            raise KeyError(f"Deal not found: {deal_id}")
        return deal

    def list_deals(
        self,
        tenant_id: str,
        stage: DealStage | None = None,
        owner_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Deal]:
        results = [d for d in self._deals.values() if d.tenant_id == tenant_id]
        if stage is not None:
            results = [d for d in results if d.stage == stage]
        if owner_id is not None:
            results = [d for d in results if d.owner_id == owner_id]
        results.sort(key=lambda d: d.created_at, reverse=True)
        return results[offset : offset + limit]

    def move_stage(
        self, deal_id: str, new_stage: DealStage, lost_reason: str | None = None
    ) -> Deal:
        deal = self.get(deal_id)
        valid = DEAL_STAGE_TRANSITIONS.get(deal.stage, [])
        if new_stage not in valid:
            raise ValueError(
                f"Invalid transition: {deal.stage.value} -> {new_stage.value}. "
                f"Valid: {[s.value for s in valid]}"
            )
        deal.stage = new_stage
        deal.probability = STAGE_PROBABILITY.get(new_stage, deal.probability)
        deal.updated_at = datetime.now(tz=None).isoformat()

        if new_stage in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST):
            deal.closed_at = datetime.now(tz=None).isoformat()
        if new_stage == DealStage.CLOSED_LOST and lost_reason:
            deal.lost_reason = lost_reason

        logger.info("Deal %s moved to %s", deal_id, new_stage.value)
        return deal

    def get_pipeline_summary(self, tenant_id: str) -> dict:
        deals = [d for d in self._deals.values() if d.tenant_id == tenant_id]
        by_stage: dict[str, dict] = {}
        for stage in DealStage:
            stage_deals = [d for d in deals if d.stage == stage]
            by_stage[stage.value] = {
                "count": len(stage_deals),
                "value": sum(d.amount for d in stage_deals),
            }

        active_deals = [
            d for d in deals
            if d.stage not in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST)
        ]
        total_pipeline = sum(d.amount for d in active_deals)
        weighted_pipeline = sum(d.amount * d.probability / 100 for d in active_deals)
        avg_deal_size = total_pipeline / len(active_deals) if active_deals else 0.0

        won = [d for d in deals if d.stage == DealStage.CLOSED_WON]
        lost = [d for d in deals if d.stage == DealStage.CLOSED_LOST]
        closed_total = len(won) + len(lost)
        win_rate = (len(won) / closed_total * 100) if closed_total > 0 else 0.0

        return {
            "by_stage": by_stage,
            "total_pipeline": total_pipeline,
            "weighted_pipeline": round(weighted_pipeline, 2),
            "avg_deal_size": round(avg_deal_size, 2),
            "win_rate": round(win_rate, 1),
        }

    def get_forecast(self, tenant_id: str, months: int = 3) -> dict:
        # Active deals (pipeline forecast)
        active_deals = [
            d for d in self._deals.values()
            if d.tenant_id == tenant_id
            and d.stage not in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST)
            and d.expected_close_date
        ]

        # Won deals (realized revenue)
        won_deals = [
            d for d in self._deals.values()
            if d.tenant_id == tenant_id
            and d.stage == DealStage.CLOSED_WON
        ]

        now = datetime.now(tz=None)
        by_month: dict[str, float] = {}
        won_by_month: dict[str, float] = {}
        for m in range(months):
            month_start = (now + timedelta(days=30 * m)).replace(day=1)
            month_key = month_start.strftime("%Y-%m")
            by_month[month_key] = 0.0
            won_by_month[month_key] = 0.0

        # Pipeline forecast (weighted by probability)
        for deal in active_deals:
            try:
                close_dt = datetime.fromisoformat(deal.expected_close_date)
                month_key = close_dt.strftime("%Y-%m")
                if month_key in by_month:
                    by_month[month_key] += deal.amount * deal.probability / 100
            except (ValueError, TypeError):
                continue

        # Won revenue (100% realized)
        for deal in won_deals:
            try:
                close_dt = datetime.fromisoformat(deal.closed_at) if deal.closed_at else datetime.now(tz=None)
                month_key = close_dt.strftime("%Y-%m")
                if month_key in won_by_month:
                    won_by_month[month_key] += deal.amount
            except (ValueError, TypeError):
                continue

        total_pipeline = sum(by_month.values())
        total_won = sum(won_by_month.values())

        return {
            "by_month": {k: round(v, 2) for k, v in by_month.items()},
            "won_by_month": {k: round(v, 2) for k, v in won_by_month.items()},
            "total_forecast": round(total_pipeline, 2),
            "total_won": round(total_won, 2),
            "total_revenue": round(total_pipeline + total_won, 2),
        }

    def get_won_deals(self, tenant_id: str, days: int = 30) -> list[Deal]:
        cutoff = (datetime.now(tz=None) - timedelta(days=days)).isoformat()
        return [
            d for d in self._deals.values()
            if d.tenant_id == tenant_id
            and d.stage == DealStage.CLOSED_WON
            and d.closed_at is not None
            and d.closed_at >= cutoff
        ]

    def get_lost_deals(self, tenant_id: str, days: int = 30) -> list[Deal]:
        cutoff = (datetime.now(tz=None) - timedelta(days=days)).isoformat()
        return [
            d for d in self._deals.values()
            if d.tenant_id == tenant_id
            and d.stage == DealStage.CLOSED_LOST
            and d.closed_at is not None
            and d.closed_at >= cutoff
        ]

    def get_aging_deals(self, tenant_id: str, days: int = 30) -> list[Deal]:
        cutoff = (datetime.now(tz=None) - timedelta(days=days)).isoformat()
        return [
            d for d in self._deals.values()
            if d.tenant_id == tenant_id
            and d.stage not in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST)
            and d.updated_at <= cutoff
        ]

    def convert_from_lead(
        self, tenant_id: str, lead_id: str, name: str, amount: float, **kwargs
    ) -> Deal:
        deal = self.create(
            tenant_id=tenant_id,
            name=name,
            amount=amount,
            lead_id=lead_id,
            **kwargs,
        )
        logger.info("Lead %s converted to deal %s", lead_id, deal.id)
        return deal


# Singleton
deal_manager = DealManager()
