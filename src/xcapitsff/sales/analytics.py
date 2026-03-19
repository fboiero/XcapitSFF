"""Advanced sales analytics — reports, health checks, and outreach effectiveness."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead, LeadStage, OutreachMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

SCORE_BUCKETS = [
    (0, 10),
    (10, 20),
    (20, 30),
    (30, 40),
    (40, 50),
    (50, 60),
    (60, 70),
    (70, 80),
    (80, 90),
    (90, 100),
]

STALE_DAYS_THRESHOLD = 30


@dataclass
class SalesReport:
    """Comprehensive sales report for a given period."""

    period: str
    total_leads: int = 0
    new_leads: int = 0
    qualified_leads: int = 0
    conversion_funnel: dict[str, int] = field(default_factory=dict)
    avg_score_by_region: dict[str, float | None] = field(default_factory=dict)
    avg_score_by_afinidad: dict[str, float | None] = field(default_factory=dict)
    top_leads: list[dict] = field(default_factory=list)
    score_distribution: dict[str, int] = field(default_factory=dict)
    c_level_ratio: float = 0.0
    stale_leads_count: int = 0


@dataclass
class LeadHealthIssue:
    """A single issue identified for a lead."""

    lead_id: int
    company_name: str | None
    issue_type: str
    detail: str


@dataclass
class LeadHealthReport:
    """Report identifying leads with data quality or pipeline issues."""

    leads_without_score: list[LeadHealthIssue] = field(default_factory=list)
    leads_without_contact: list[LeadHealthIssue] = field(default_factory=list)
    leads_stuck: list[LeadHealthIssue] = field(default_factory=list)
    leads_low_engagement: list[LeadHealthIssue] = field(default_factory=list)
    total_issues: int = 0


@dataclass
class ChannelStats:
    """Outreach statistics for a single channel."""

    channel: str
    sent: int = 0
    replied: int = 0
    draft: int = 0
    reply_rate: float = 0.0


@dataclass
class OutreachReport:
    """Report on outreach message effectiveness by channel."""

    total_messages: int = 0
    total_sent: int = 0
    total_replied: int = 0
    overall_reply_rate: float = 0.0
    by_channel: list[ChannelStats] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------


async def generate_sales_report(
    db: AsyncSession, period_days: int = 30
) -> SalesReport:
    """Generate a comprehensive sales report for the given period.

    Args:
        db: Async database session.
        period_days: Number of days to look back for "new" leads.

    Returns:
        A fully populated ``SalesReport``.
    """
    cutoff = datetime.now(tz=None) - timedelta(days=period_days)
    period_label = f"last_{period_days}_days"

    # Total leads
    total_leads = await db.scalar(select(func.count(Lead.id))) or 0

    # New leads in period
    new_leads = await db.scalar(
        select(func.count(Lead.id)).where(Lead.created_at >= cutoff)
    ) or 0

    # Qualified leads (stage >= qualified, not lost)
    qualified_stages = [
        LeadStage.QUALIFIED.value,
        LeadStage.CONTACTED.value,
        LeadStage.MEETING.value,
        LeadStage.PROPOSAL.value,
        LeadStage.NEGOTIATION.value,
        LeadStage.WON.value,
    ]
    qualified_leads = await db.scalar(
        select(func.count(Lead.id)).where(Lead.stage.in_(qualified_stages))
    ) or 0

    # Conversion funnel: count per stage
    stage_q = await db.execute(
        select(Lead.stage, func.count(Lead.id)).group_by(Lead.stage)
    )
    conversion_funnel: dict[str, int] = {}
    for row in stage_q:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        conversion_funnel[key] = row[1]

    # Avg score by region
    region_avg_q = await db.execute(
        select(Lead.region, func.avg(Lead.score_icp))
        .where(Lead.score_icp.isnot(None))
        .group_by(Lead.region)
    )
    avg_score_by_region: dict[str, float | None] = {}
    for row in region_avg_q:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        avg_score_by_region[key] = round(float(row[1]), 1) if row[1] is not None else None

    # Avg score by afinidad
    afinidad_avg_q = await db.execute(
        select(Lead.afinidad, func.avg(Lead.score_icp))
        .where(Lead.score_icp.isnot(None))
        .group_by(Lead.afinidad)
    )
    avg_score_by_afinidad: dict[str, float | None] = {}
    for row in afinidad_avg_q:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        avg_score_by_afinidad[key] = round(float(row[1]), 1) if row[1] is not None else None

    # Top leads (by score)
    top_q = await db.execute(
        select(Lead)
        .where(Lead.score_icp.isnot(None))
        .order_by(Lead.score_icp.desc())
        .limit(10)
    )
    top_leads = [
        {
            "id": lead.id,
            "company_name": lead.company_name,
            "contact_name": lead.contact_name,
            "score_icp": lead.score_icp,
            "region": lead.region.value if hasattr(lead.region, "value") else str(lead.region),
            "stage": lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage),
            "c_level": lead.c_level,
        }
        for lead in top_q.scalars().all()
    ]

    # Score distribution (histogram buckets)
    score_distribution: dict[str, int] = {}
    for low, high in SCORE_BUCKETS:
        bucket_label = f"{low}-{high}"
        count = await db.scalar(
            select(func.count(Lead.id)).where(
                Lead.score_icp.isnot(None),
                Lead.score_icp >= low,
                Lead.score_icp < high,
            )
        ) or 0
        score_distribution[bucket_label] = count
    # Include leads with score exactly 100
    count_100 = await db.scalar(
        select(func.count(Lead.id)).where(Lead.score_icp == 100)
    ) or 0
    if count_100 > 0:
        score_distribution["90-100"] = score_distribution.get("90-100", 0) + count_100

    # C-level ratio
    c_level_count = await db.scalar(
        select(func.count(Lead.id)).where(Lead.c_level.is_(True))
    ) or 0
    c_level_ratio = (c_level_count / total_leads) if total_leads > 0 else 0.0

    # Stale leads count
    stale_cutoff = datetime.now(tz=None) - timedelta(days=STALE_DAYS_THRESHOLD)
    stale_leads_count = await db.scalar(
        select(func.count(Lead.id)).where(
            Lead.updated_at < stale_cutoff,
            Lead.stage.notin_([LeadStage.WON.value, LeadStage.LOST.value]),
        )
    ) or 0

    return SalesReport(
        period=period_label,
        total_leads=total_leads,
        new_leads=new_leads,
        qualified_leads=qualified_leads,
        conversion_funnel=conversion_funnel,
        avg_score_by_region=avg_score_by_region,
        avg_score_by_afinidad=avg_score_by_afinidad,
        top_leads=top_leads,
        score_distribution=score_distribution,
        c_level_ratio=round(c_level_ratio, 3),
        stale_leads_count=stale_leads_count,
    )


async def generate_lead_health_report(db: AsyncSession) -> LeadHealthReport:
    """Identify leads with data quality or pipeline issues.

    Checks:
    - Leads without a score (score_icp is NULL).
    - Leads without contact info (no email and no contact_name).
    - Leads stuck in the same stage for more than 30 days (not won/lost).
    - Leads with low engagement (no outreach messages and not contacted).

    Args:
        db: Async database session.

    Returns:
        A ``LeadHealthReport`` with categorised issues.
    """
    report = LeadHealthReport()

    # Leads without score
    no_score_q = await db.execute(
        select(Lead).where(Lead.score_icp.is_(None))
    )
    for lead in no_score_q.scalars().all():
        report.leads_without_score.append(
            LeadHealthIssue(
                lead_id=lead.id,
                company_name=lead.company_name,
                issue_type="no_score",
                detail="Lead has no ICP score assigned.",
            )
        )

    # Leads without contact info
    no_contact_q = await db.execute(
        select(Lead).where(
            Lead.contact_email.is_(None),
            Lead.contact_name.is_(None),
        )
    )
    for lead in no_contact_q.scalars().all():
        report.leads_without_contact.append(
            LeadHealthIssue(
                lead_id=lead.id,
                company_name=lead.company_name,
                issue_type="no_contact",
                detail="Lead has no contact name or email.",
            )
        )

    # Leads stuck in the same stage too long
    stuck_cutoff = datetime.now(tz=None) - timedelta(days=STALE_DAYS_THRESHOLD)
    stuck_q = await db.execute(
        select(Lead).where(
            Lead.updated_at < stuck_cutoff,
            Lead.stage.notin_([LeadStage.WON.value, LeadStage.LOST.value]),
        )
    )
    for lead in stuck_q.scalars().all():
        days_stuck = (datetime.now(tz=None) - lead.updated_at).days
        stage_val = lead.stage.value if hasattr(lead.stage, "value") else str(lead.stage)
        report.leads_stuck.append(
            LeadHealthIssue(
                lead_id=lead.id,
                company_name=lead.company_name,
                issue_type="stuck",
                detail=f"Lead stuck in stage '{stage_val}' for {days_stuck} days.",
            )
        )

    # Leads with low engagement: in early stages with no outreach messages
    early_stages = [LeadStage.RAW.value, LeadStage.QUALIFIED.value]
    low_eng_q = await db.execute(
        select(Lead).where(Lead.stage.in_(early_stages))
    )
    for lead in low_eng_q.scalars().all():
        msg_count = await db.scalar(
            select(func.count(OutreachMessage.id)).where(
                OutreachMessage.lead_id == lead.id
            )
        ) or 0
        if msg_count == 0:
            report.leads_low_engagement.append(
                LeadHealthIssue(
                    lead_id=lead.id,
                    company_name=lead.company_name,
                    issue_type="low_engagement",
                    detail="Lead in early stage with no outreach messages.",
                )
            )

    report.total_issues = (
        len(report.leads_without_score)
        + len(report.leads_without_contact)
        + len(report.leads_stuck)
        + len(report.leads_low_engagement)
    )
    return report


async def generate_outreach_effectiveness(db: AsyncSession) -> OutreachReport:
    """Track outreach message effectiveness by channel.

    Counts sent, replied, and draft messages per channel and computes reply
    rates.

    Args:
        db: Async database session.

    Returns:
        An ``OutreachReport`` with per-channel and overall statistics.
    """
    # Total messages
    total_messages = await db.scalar(
        select(func.count(OutreachMessage.id))
    ) or 0

    # By channel and status
    channel_status_q = await db.execute(
        select(
            OutreachMessage.channel,
            OutreachMessage.status,
            func.count(OutreachMessage.id),
        ).group_by(OutreachMessage.channel, OutreachMessage.status)
    )

    channel_data: dict[str, dict[str, int]] = {}
    for row in channel_status_q:
        channel = str(row[0])
        status = str(row[1])
        count = row[2]
        if channel not in channel_data:
            channel_data[channel] = {"sent": 0, "replied": 0, "draft": 0}
        if status == "sent":
            channel_data[channel]["sent"] += count
        elif status == "replied":
            channel_data[channel]["replied"] += count
        elif status == "draft":
            channel_data[channel]["draft"] += count

    total_sent = 0
    total_replied = 0
    by_channel: list[ChannelStats] = []

    for channel, stats in sorted(channel_data.items()):
        sent = stats["sent"] + stats["replied"]  # replied messages were also sent
        replied = stats["replied"]
        draft = stats["draft"]
        reply_rate = (replied / sent * 100) if sent > 0 else 0.0
        total_sent += sent
        total_replied += replied
        by_channel.append(
            ChannelStats(
                channel=channel,
                sent=sent,
                replied=replied,
                draft=draft,
                reply_rate=round(reply_rate, 1),
            )
        )

    overall_reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0.0

    return OutreachReport(
        total_messages=total_messages,
        total_sent=total_sent,
        total_replied=total_replied,
        overall_reply_rate=round(overall_reply_rate, 1),
        by_channel=by_channel,
    )
