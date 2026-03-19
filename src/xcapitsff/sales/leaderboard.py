"""Lead Scoring Leaderboard — rank and track top leads across dimensions."""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead, LeadStage, OutreachMessage

logger = logging.getLogger(__name__)


@dataclass
class LeaderboardEntry:
    rank: int
    lead_id: int
    company_name: str | None
    contact_name: str | None
    region: str
    score_icp: float | None
    c_level: bool
    afinidad: str
    stage: str
    outreach_count: int = 0
    days_in_pipeline: int = 0


@dataclass
class Leaderboard:
    title: str
    generated_at: datetime = field(default_factory=datetime.now)
    entries: list[LeaderboardEntry] = field(default_factory=list)
    total_leads: int = 0


async def get_top_leads_leaderboard(
    db: AsyncSession, limit: int = 25, region: str | None = None
) -> Leaderboard:
    """Get top leads ranked by ICP score."""
    query = select(Lead).where(Lead.score_icp.isnot(None))
    if region:
        query = query.where(Lead.region == region)
    query = query.order_by(Lead.score_icp.desc()).limit(limit)

    result = await db.execute(query)
    leads = list(result.scalars().all())

    total = await db.scalar(select(func.count(Lead.id))) or 0

    entries = []
    for i, lead in enumerate(leads):
        outreach_count = await db.scalar(
            select(func.count(OutreachMessage.id)).where(OutreachMessage.lead_id == lead.id)
        ) or 0

        days = (datetime.now() - lead.created_at).days if lead.created_at else 0

        entries.append(LeaderboardEntry(
            rank=i + 1,
            lead_id=lead.id,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            region=lead.region if isinstance(lead.region, str) else lead.region.value,
            score_icp=lead.score_icp,
            c_level=lead.c_level,
            afinidad=lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
            stage=lead.stage if isinstance(lead.stage, str) else lead.stage.value,
            outreach_count=outreach_count,
            days_in_pipeline=days,
        ))

    return Leaderboard(
        title=f"Top {limit} Leads" + (f" — {region}" if region else ""),
        entries=entries,
        total_leads=total,
    )


async def get_c_level_leaderboard(db: AsyncSession, limit: int = 25) -> Leaderboard:
    """Get top C-level leads."""
    query = (
        select(Lead)
        .where(Lead.c_level.is_(True), Lead.score_icp.isnot(None))
        .order_by(Lead.score_icp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    leads = list(result.scalars().all())

    entries = []
    for i, lead in enumerate(leads):
        entries.append(LeaderboardEntry(
            rank=i + 1,
            lead_id=lead.id,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            region=lead.region if isinstance(lead.region, str) else lead.region.value,
            score_icp=lead.score_icp,
            c_level=True,
            afinidad=lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
            stage=lead.stage if isinstance(lead.stage, str) else lead.stage.value,
        ))

    return Leaderboard(title=f"Top {limit} C-Level Leads", entries=entries)


async def get_ready_for_outreach(db: AsyncSession, limit: int = 20) -> Leaderboard:
    """Get qualified leads that haven't been contacted yet — ready for outreach."""
    query = (
        select(Lead)
        .where(
            Lead.stage.in_([LeadStage.RAW.value, LeadStage.QUALIFIED.value]),
            Lead.score_icp.isnot(None),
            Lead.score_icp >= 45,
        )
        .order_by(Lead.score_icp.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    leads = list(result.scalars().all())

    entries = []
    for i, lead in enumerate(leads):
        entries.append(LeaderboardEntry(
            rank=i + 1,
            lead_id=lead.id,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            region=lead.region if isinstance(lead.region, str) else lead.region.value,
            score_icp=lead.score_icp,
            c_level=lead.c_level,
            afinidad=lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
            stage=lead.stage if isinstance(lead.stage, str) else lead.stage.value,
        ))

    return Leaderboard(title="Ready for Outreach", entries=entries)
