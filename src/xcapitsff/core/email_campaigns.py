"""Email Campaign Manager — create, schedule, send, and track email campaigns.

Supports one-time blasts, drip sequences, triggered sends, and A/B tests.
Tracks per-recipient delivery events (open, click, bounce, unsubscribe)
and computes aggregate campaign statistics.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class CampaignType(str, Enum):
    ONE_TIME = "one_time"
    DRIP = "drip"
    TRIGGERED = "triggered"
    AB_TEST = "ab_test"


class RecipientStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    UNSUBSCRIBED = "unsubscribed"


@dataclass
class Recipient:
    email: str
    name: str = ""
    variables: dict = field(default_factory=dict)
    status: RecipientStatus = RecipientStatus.PENDING
    sent_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None


@dataclass
class CampaignStats:
    total_recipients: int = 0
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0


@dataclass
class EmailCampaign:
    id: str
    tenant_id: str
    name: str
    type: CampaignType
    status: CampaignStatus
    template_id: str
    subject_override: str | None = None
    recipients: list[Recipient] = field(default_factory=list)
    scheduled_at: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    stats: dict = field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=None))
    ab_variant_id: str | None = None
    tags: list[str] = field(default_factory=list)


class EmailCampaignManager:
    """Manages email campaign lifecycle with in-memory storage."""

    def __init__(self) -> None:
        self._campaigns: dict[str, EmailCampaign] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        tenant_id: str,
        name: str,
        campaign_type: CampaignType | str,
        template_id: str,
        created_by: str | None = None,
    ) -> EmailCampaign:
        if isinstance(campaign_type, str):
            campaign_type = CampaignType(campaign_type)

        campaign = EmailCampaign(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            type=campaign_type,
            status=CampaignStatus.DRAFT,
            template_id=template_id,
            created_by=created_by,
        )
        self._campaigns[campaign.id] = campaign
        logger.info("Email campaign created: %s — %s", campaign.id, name)
        return campaign

    def update(self, campaign_id: str, **kwargs) -> EmailCampaign:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")

        for key, value in kwargs.items():
            if key == "type" and isinstance(value, str):
                value = CampaignType(value)
            if key == "status" and isinstance(value, str):
                value = CampaignStatus(value)
            if hasattr(campaign, key) and key not in ("id", "tenant_id", "created_at"):
                setattr(campaign, key, value)

        logger.info("Email campaign updated: %s", campaign_id)
        return campaign

    def delete(self, campaign_id: str) -> bool:
        if campaign_id in self._campaigns:
            del self._campaigns[campaign_id]
            logger.info("Email campaign deleted: %s", campaign_id)
            return True
        return False

    def get(self, campaign_id: str) -> EmailCampaign | None:
        return self._campaigns.get(campaign_id)

    def list_campaigns(
        self,
        tenant_id: str,
        status: CampaignStatus | str | None = None,
    ) -> list[EmailCampaign]:
        if isinstance(status, str):
            status = CampaignStatus(status)

        results = [c for c in self._campaigns.values() if c.tenant_id == tenant_id]
        if status is not None:
            results = [c for c in results if c.status == status]
        return sorted(results, key=lambda c: c.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Recipients
    # ------------------------------------------------------------------

    def add_recipients(
        self, campaign_id: str, recipients: list[dict]
    ) -> EmailCampaign:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")

        existing_emails = {r.email for r in campaign.recipients}
        for r in recipients:
            if r["email"] not in existing_emails:
                campaign.recipients.append(
                    Recipient(
                        email=r["email"],
                        name=r.get("name", ""),
                        variables=r.get("variables", {}),
                    )
                )
                existing_emails.add(r["email"])

        logger.info(
            "Added recipients to campaign %s, total: %d",
            campaign_id,
            len(campaign.recipients),
        )
        return campaign

    def remove_recipient(self, campaign_id: str, email: str) -> bool:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")

        original_len = len(campaign.recipients)
        campaign.recipients = [r for r in campaign.recipients if r.email != email]
        return len(campaign.recipients) < original_len

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def schedule(self, campaign_id: str, scheduled_at: str) -> EmailCampaign:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")
        if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.PAUSED):
            raise ValueError(
                f"Cannot schedule campaign in status {campaign.status.value}"
            )

        campaign.scheduled_at = scheduled_at
        campaign.status = CampaignStatus.SCHEDULED
        logger.info("Campaign %s scheduled for %s", campaign_id, scheduled_at)
        return campaign

    def send(self, campaign_id: str) -> EmailCampaign:
        """Simulate sending the campaign to all pending recipients."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")
        if campaign.status not in (
            CampaignStatus.DRAFT,
            CampaignStatus.SCHEDULED,
        ):
            raise ValueError(
                f"Cannot send campaign in status {campaign.status.value}"
            )

        campaign.status = CampaignStatus.SENDING
        campaign.started_at = datetime.now(tz=None)

        for recipient in campaign.recipients:
            if recipient.status == RecipientStatus.PENDING:
                recipient.status = RecipientStatus.SENT
                recipient.sent_at = datetime.now(tz=None)

        campaign.status = CampaignStatus.SENT
        campaign.completed_at = datetime.now(tz=None)
        logger.info(
            "Campaign %s sent to %d recipients",
            campaign_id,
            len(campaign.recipients),
        )
        return campaign

    def pause(self, campaign_id: str) -> EmailCampaign:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")
        if campaign.status not in (CampaignStatus.SENDING, CampaignStatus.SCHEDULED):
            raise ValueError(
                f"Cannot pause campaign in status {campaign.status.value}"
            )
        campaign.status = CampaignStatus.PAUSED
        logger.info("Campaign %s paused", campaign_id)
        return campaign

    def resume(self, campaign_id: str) -> EmailCampaign:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")
        if campaign.status != CampaignStatus.PAUSED:
            raise ValueError(
                f"Cannot resume campaign in status {campaign.status.value}"
            )
        campaign.status = CampaignStatus.SCHEDULED
        logger.info("Campaign %s resumed", campaign_id)
        return campaign

    def cancel(self, campaign_id: str) -> EmailCampaign:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")
        if campaign.status == CampaignStatus.SENT:
            raise ValueError("Cannot cancel an already sent campaign")
        campaign.status = CampaignStatus.CANCELLED
        campaign.completed_at = datetime.now(tz=None)
        logger.info("Campaign %s cancelled", campaign_id)
        return campaign

    # ------------------------------------------------------------------
    # Tracking events
    # ------------------------------------------------------------------

    def _find_recipient(
        self, campaign_id: str, email: str
    ) -> tuple[EmailCampaign, Recipient] | tuple[None, None]:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return None, None
        for r in campaign.recipients:
            if r.email == email:
                return campaign, r
        return campaign, None

    def record_open(self, campaign_id: str, email: str) -> bool:
        campaign, recipient = self._find_recipient(campaign_id, email)
        if not recipient:
            return False
        if recipient.status in (RecipientStatus.SENT, RecipientStatus.OPENED):
            recipient.status = RecipientStatus.OPENED
            recipient.opened_at = datetime.now(tz=None)
            return True
        return False

    def record_click(self, campaign_id: str, email: str) -> bool:
        campaign, recipient = self._find_recipient(campaign_id, email)
        if not recipient:
            return False
        if recipient.status in (
            RecipientStatus.SENT,
            RecipientStatus.OPENED,
            RecipientStatus.CLICKED,
        ):
            recipient.status = RecipientStatus.CLICKED
            if not recipient.opened_at:
                recipient.opened_at = datetime.now(tz=None)
            recipient.clicked_at = datetime.now(tz=None)
            return True
        return False

    def record_bounce(self, campaign_id: str, email: str) -> bool:
        campaign, recipient = self._find_recipient(campaign_id, email)
        if not recipient:
            return False
        recipient.status = RecipientStatus.BOUNCED
        return True

    def record_unsubscribe(self, campaign_id: str, email: str) -> bool:
        campaign, recipient = self._find_recipient(campaign_id, email)
        if not recipient:
            return False
        recipient.status = RecipientStatus.UNSUBSCRIBED
        return True

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self, campaign_id: str) -> CampaignStats:
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            raise KeyError(f"Campaign {campaign_id} not found")

        total = len(campaign.recipients)
        sent = sum(1 for r in campaign.recipients if r.status != RecipientStatus.PENDING)
        bounced = sum(1 for r in campaign.recipients if r.status == RecipientStatus.BOUNCED)
        delivered = sent - bounced
        opened = sum(
            1
            for r in campaign.recipients
            if r.status in (RecipientStatus.OPENED, RecipientStatus.CLICKED)
        )
        clicked = sum(
            1 for r in campaign.recipients if r.status == RecipientStatus.CLICKED
        )
        unsubscribed = sum(
            1
            for r in campaign.recipients
            if r.status == RecipientStatus.UNSUBSCRIBED
        )

        open_rate = round(opened / delivered * 100, 1) if delivered > 0 else 0.0
        click_rate = round(clicked / delivered * 100, 1) if delivered > 0 else 0.0
        bounce_rate = round(bounced / sent * 100, 1) if sent > 0 else 0.0

        return CampaignStats(
            total_recipients=total,
            sent=sent,
            delivered=delivered,
            opened=opened,
            clicked=clicked,
            bounced=bounced,
            unsubscribed=unsubscribed,
            open_rate=open_rate,
            click_rate=click_rate,
            bounce_rate=bounce_rate,
        )

    def get_campaign_performance(
        self, tenant_id: str, days: int = 30
    ) -> dict:
        """Aggregate performance stats for all campaigns in a tenant within N days."""
        cutoff = datetime.now(tz=None)
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=days)

        campaigns = [
            c
            for c in self._campaigns.values()
            if c.tenant_id == tenant_id and c.created_at >= cutoff
        ]

        total_campaigns = len(campaigns)
        total_recipients = 0
        total_sent = 0
        total_opened = 0
        total_clicked = 0
        total_bounced = 0
        total_unsubscribed = 0

        for c in campaigns:
            stats = self.get_stats(c.id)
            total_recipients += stats.total_recipients
            total_sent += stats.sent
            total_opened += stats.opened
            total_clicked += stats.clicked
            total_bounced += stats.bounced
            total_unsubscribed += stats.unsubscribed

        delivered = total_sent - total_bounced

        return {
            "period_days": days,
            "total_campaigns": total_campaigns,
            "total_recipients": total_recipients,
            "total_sent": total_sent,
            "total_delivered": delivered,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_bounced": total_bounced,
            "total_unsubscribed": total_unsubscribed,
            "avg_open_rate": round(total_opened / delivered * 100, 1)
            if delivered > 0
            else 0.0,
            "avg_click_rate": round(total_clicked / delivered * 100, 1)
            if delivered > 0
            else 0.0,
            "avg_bounce_rate": round(total_bounced / total_sent * 100, 1)
            if total_sent > 0
            else 0.0,
        }


# Singleton
email_campaign_manager = EmailCampaignManager()
