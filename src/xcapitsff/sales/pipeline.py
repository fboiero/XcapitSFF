"""Sales Pipeline — stage management, transitions, bulk operations, analytics."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead, LeadStage, OutreachMessage
from xcapitsff.core.schemas import (
    LeadCreate,
    LeadFilter,
    LeadUpdate,
    SalesPipelineStats,
)
from xcapitsff.sales.scoring import calculate_icp_score

logger = logging.getLogger(__name__)

# Valid stage transitions
STAGE_TRANSITIONS: dict[LeadStage, list[LeadStage]] = {
    LeadStage.RAW: [LeadStage.CONTACTED, LeadStage.QUALIFIED, LeadStage.LOST],
    LeadStage.CONTACTED: [LeadStage.QUALIFIED, LeadStage.PROPOSAL, LeadStage.LOST],
    LeadStage.QUALIFIED: [LeadStage.PROPOSAL, LeadStage.NEGOTIATION, LeadStage.LOST],
    LeadStage.MEETING: [LeadStage.PROPOSAL, LeadStage.LOST],
    LeadStage.PROPOSAL: [LeadStage.NEGOTIATION, LeadStage.WON, LeadStage.LOST],
    LeadStage.NEGOTIATION: [LeadStage.WON, LeadStage.LOST],
    LeadStage.WON: [],
    LeadStage.LOST: [LeadStage.RAW],
}


@dataclass
class BulkActionResult:
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] | None = None


def is_valid_transition(current: LeadStage, target: LeadStage) -> bool:
    return target in STAGE_TRANSITIONS.get(current, [])


def get_valid_transitions(current: LeadStage) -> list[str]:
    return [s.value for s in STAGE_TRANSITIONS.get(current, [])]


async def create_lead(db: AsyncSession, data: LeadCreate) -> Lead:
    score = calculate_icp_score(
        region=data.region.value,
        c_level=data.c_level,
        existing_score=data.score_icp,
        afinidad=data.afinidad.value,
    )

    lead = Lead(
        company_name=data.company_name,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        region=data.region.value,
        c_level=data.c_level,
        score_icp=score,
        afinidad=data.afinidad.value,
        notes=data.notes,
    )
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    logger.info(f"Lead created: id={lead.id} score={score} region={data.region.value}")
    return lead


async def get_leads(
    db: AsyncSession, filters: LeadFilter | None = None, limit: int = 100, offset: int = 0
) -> list[Lead]:
    query = select(Lead)

    if filters:
        if filters.region:
            query = query.where(Lead.region == filters.region.value)
        if filters.c_level is not None:
            query = query.where(Lead.c_level == filters.c_level)
        if filters.afinidad:
            query = query.where(Lead.afinidad == filters.afinidad.value)
        if filters.stage:
            query = query.where(Lead.stage == filters.stage.value)
        if filters.score_min is not None:
            query = query.where(Lead.score_icp >= filters.score_min)
        if filters.score_max is not None:
            query = query.where(Lead.score_icp <= filters.score_max)

    query = query.order_by(Lead.score_icp.desc().nullslast()).limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_lead(db: AsyncSession, lead_id: int) -> Lead | None:
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    return result.scalar_one_or_none()


async def update_lead(db: AsyncSession, lead_id: int, data: LeadUpdate) -> Lead | None:
    lead = await get_lead(db, lead_id)
    if not lead:
        return None

    update_data = data.model_dump(exclude_unset=True)

    if "stage" in update_data and update_data["stage"]:
        target = LeadStage(update_data["stage"])
        if not is_valid_transition(lead.stage, target):
            valid = get_valid_transitions(lead.stage)
            raise ValueError(
                f"Invalid transition: {lead.stage.value} -> {target.value}. "
                f"Valid transitions: {valid}"
            )

    for field, value in update_data.items():
        setattr(lead, field, value)

    await db.flush()
    await db.refresh(lead)
    return lead


async def delete_lead(db: AsyncSession, lead_id: int) -> bool:
    lead = await get_lead(db, lead_id)
    if not lead:
        return False
    await db.delete(lead)
    await db.flush()
    return True


async def bulk_qualify(db: AsyncSession, score_threshold: float = 60.0) -> BulkActionResult:
    """Auto-qualify all RAW leads above the score threshold."""
    result = BulkActionResult()
    raw_leads = await db.execute(
        select(Lead).where(
            Lead.stage == LeadStage.RAW.value,
            Lead.score_icp.isnot(None),
            Lead.score_icp >= score_threshold,
        )
    )
    for lead in raw_leads.scalars().all():
        result.processed += 1
        lead.stage = LeadStage.QUALIFIED
        result.updated += 1

    await db.flush()
    logger.info(f"Bulk qualify: {result.updated}/{result.processed} leads qualified")
    return result


async def bulk_rescore(db: AsyncSession) -> BulkActionResult:
    """Recalculate ICP scores for all leads."""
    result = BulkActionResult()
    all_leads = await db.execute(select(Lead))

    for lead in all_leads.scalars().all():
        result.processed += 1
        old_score = lead.score_icp
        new_score = calculate_icp_score(
            region=lead.region if isinstance(lead.region, str) else lead.region.value,
            c_level=lead.c_level,
            existing_score=lead.score_icp,
            afinidad=lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
        )
        if new_score != old_score:
            lead.score_icp = new_score
            result.updated += 1

    await db.flush()
    logger.info(f"Bulk rescore: {result.updated}/{result.processed} scores updated")
    return result


async def get_pipeline_stats(db: AsyncSession) -> SalesPipelineStats:
    total = await db.scalar(select(func.count(Lead.id))) or 0

    # By stage
    stage_q = await db.execute(
        select(Lead.stage, func.count(Lead.id)).group_by(Lead.stage)
    )
    by_stage = {}
    for row in stage_q:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        by_stage[key] = row[1]

    # By region
    region_q = await db.execute(
        select(Lead.region, func.count(Lead.id)).group_by(Lead.region)
    )
    by_region = {}
    for row in region_q:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        by_region[key] = row[1]

    # By afinidad
    afinidad_q = await db.execute(
        select(Lead.afinidad, func.count(Lead.id)).group_by(Lead.afinidad)
    )
    by_afinidad = {}
    for row in afinidad_q:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        by_afinidad[key] = row[1]

    # Avg score
    avg_score = await db.scalar(
        select(func.avg(Lead.score_icp)).where(Lead.score_icp.isnot(None))
    )

    # C-level count
    c_level_count = await db.scalar(
        select(func.count(Lead.id)).where(Lead.c_level.is_(True))
    ) or 0

    # Conversion rate
    won = by_stage.get("won", 0)
    conversion_rate = (won / total * 100) if total > 0 else None

    return SalesPipelineStats(
        total_leads=total,
        by_stage=by_stage,
        by_region=by_region,
        by_afinidad=by_afinidad,
        avg_score_icp=round(avg_score, 1) if avg_score else None,
        c_level_count=c_level_count,
        conversion_rate=round(conversion_rate, 1) if conversion_rate else None,
    )


async def get_pipeline_funnel(db: AsyncSession) -> list[dict]:
    """Get funnel data: count per stage in pipeline order."""
    stage_order = [s for s in LeadStage]
    counts = {}
    result = await db.execute(
        select(Lead.stage, func.count(Lead.id)).group_by(Lead.stage)
    )
    for row in result:
        key = row[0].value if hasattr(row[0], "value") else str(row[0])
        counts[key] = row[1]

    funnel = []
    for stage in stage_order:
        count = counts.get(stage.value, 0)
        funnel.append({"stage": stage.value, "count": count})
    return funnel


async def get_hot_leads(db: AsyncSession, limit: int = 20) -> list[Lead]:
    """Get top leads by score that need immediate action."""
    result = await db.execute(
        select(Lead)
        .where(
            Lead.score_icp >= 60,
            Lead.stage.in_([LeadStage.RAW.value, LeadStage.QUALIFIED.value]),
        )
        .order_by(Lead.score_icp.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_stale_leads(db: AsyncSession, days: int = 30) -> list[Lead]:
    """Get leads that haven't been updated in N days and aren't won/lost."""
    from datetime import timedelta
    cutoff = datetime.now(tz=None) - timedelta(days=days)
    result = await db.execute(
        select(Lead)
        .where(
            Lead.updated_at < cutoff,
            Lead.stage.notin_([LeadStage.WON.value, LeadStage.LOST.value]),
        )
        .order_by(Lead.updated_at.asc())
    )
    return list(result.scalars().all())
