"""Campaign Manager — organize outreach into trackable campaigns.

A campaign is a structured outreach effort targeting a segment of leads
with specific messaging over a defined time period.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignType(str, Enum):
    OUTREACH = "outreach"  # Cold outreach to new leads
    NURTURING = "nurturing"  # Warm leads, educational content
    REACTIVATION = "reactivation"  # Re-engage cold/lost leads
    UPSELL = "upsell"  # Existing customers, new products
    EVENT = "event"  # Event-based (webinar, conference)


@dataclass
class CampaignTarget:
    """Criteria for selecting leads into the campaign."""
    regions: list[str] | None = None
    afinidad_min: str | None = None  # HIGH, MEDIUM, LOW
    score_min: float | None = None
    score_max: float | None = None
    c_level_only: bool = False
    stages: list[str] | None = None
    exclude_contacted_days: int = 30  # don't re-contact recently contacted


@dataclass
class CampaignMetrics:
    total_targeted: int = 0
    messages_sent: int = 0
    messages_opened: int = 0  # tracking placeholder
    replies_received: int = 0
    meetings_booked: int = 0
    conversions: int = 0
    open_rate: float = 0.0
    reply_rate: float = 0.0
    conversion_rate: float = 0.0

    def recalculate(self) -> None:
        if self.messages_sent > 0:
            self.open_rate = round(self.messages_opened / self.messages_sent * 100, 1)
            self.reply_rate = round(self.replies_received / self.messages_sent * 100, 1)
        if self.total_targeted > 0:
            self.conversion_rate = round(self.conversions / self.total_targeted * 100, 1)


@dataclass
class Campaign:
    campaign_id: str
    name: str
    campaign_type: CampaignType
    status: CampaignStatus = CampaignStatus.DRAFT
    channel: str = "email"
    target: CampaignTarget = field(default_factory=CampaignTarget)
    template_ids: list[str] = field(default_factory=list)
    followup_days: list[int] = field(default_factory=lambda: [3, 7, 14])
    metrics: CampaignMetrics = field(default_factory=CampaignMetrics)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str = ""

    def start(self) -> None:
        if self.status != CampaignStatus.DRAFT:
            raise ValueError(f"Cannot start campaign in status {self.status.value}")
        self.status = CampaignStatus.ACTIVE
        self.started_at = datetime.now()

    def pause(self) -> None:
        if self.status != CampaignStatus.ACTIVE:
            raise ValueError(f"Cannot pause campaign in status {self.status.value}")
        self.status = CampaignStatus.PAUSED

    def resume(self) -> None:
        if self.status != CampaignStatus.PAUSED:
            raise ValueError(f"Cannot resume campaign in status {self.status.value}")
        self.status = CampaignStatus.ACTIVE

    def complete(self) -> None:
        self.status = CampaignStatus.COMPLETED
        self.completed_at = datetime.now()
        self.metrics.recalculate()

    def cancel(self) -> None:
        self.status = CampaignStatus.CANCELLED
        self.completed_at = datetime.now()


class CampaignManager:
    """Manages campaign lifecycle and tracking."""

    def __init__(self):
        self._campaigns: dict[str, Campaign] = {}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"CAMP-{self._counter:04d}"

    def create(
        self,
        name: str,
        campaign_type: CampaignType | str,
        channel: str = "email",
        target: CampaignTarget | None = None,
        template_ids: list[str] | None = None,
        followup_days: list[int] | None = None,
        notes: str = "",
    ) -> Campaign:
        if isinstance(campaign_type, str):
            campaign_type = CampaignType(campaign_type)

        campaign = Campaign(
            campaign_id=self._next_id(),
            name=name,
            campaign_type=campaign_type,
            channel=channel,
            target=target or CampaignTarget(),
            template_ids=template_ids or [],
            followup_days=followup_days or [3, 7, 14],
            notes=notes,
        )
        self._campaigns[campaign.campaign_id] = campaign
        logger.info(f"Campaign created: {campaign.campaign_id} — {name}")
        return campaign

    def get(self, campaign_id: str) -> Campaign | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self, status: CampaignStatus | None = None, limit: int = 50
    ) -> list[Campaign]:
        campaigns = list(self._campaigns.values())
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        return sorted(campaigns, key=lambda c: c.created_at, reverse=True)[:limit]

    def update_metrics(self, campaign_id: str, **kwargs) -> Campaign | None:
        campaign = self.get(campaign_id)
        if not campaign:
            return None
        for key, value in kwargs.items():
            if hasattr(campaign.metrics, key):
                setattr(campaign.metrics, key, value)
        campaign.metrics.recalculate()
        return campaign

    def get_active_campaigns(self) -> list[Campaign]:
        return self.list_campaigns(status=CampaignStatus.ACTIVE)

    def get_stats(self) -> dict:
        by_status = {}
        by_type = {}
        total_sent = 0
        total_replies = 0

        for c in self._campaigns.values():
            by_status[c.status.value] = by_status.get(c.status.value, 0) + 1
            by_type[c.campaign_type.value] = by_type.get(c.campaign_type.value, 0) + 1
            total_sent += c.metrics.messages_sent
            total_replies += c.metrics.replies_received

        return {
            "total_campaigns": len(self._campaigns),
            "by_status": by_status,
            "by_type": by_type,
            "total_messages_sent": total_sent,
            "total_replies": total_replies,
            "avg_reply_rate": round(total_replies / total_sent * 100, 1) if total_sent > 0 else 0,
        }


# Singleton
campaign_manager = CampaignManager()
