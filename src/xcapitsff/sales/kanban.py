"""Kanban Board — visual pipeline management data layer.

Provides the data structures for a drag-and-drop pipeline board.
The frontend consumes this API to render the kanban.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.models import Lead, LeadStage

logger = logging.getLogger(__name__)

# Stage display configuration
STAGE_CONFIG = {
    "raw": {"label": "Nuevos", "color": "#94a3b8", "order": 0, "emoji": "📥"},
    "qualified": {"label": "Calificados", "color": "#3b82f6", "order": 1, "emoji": "✅"},
    "contacted": {"label": "Contactados", "color": "#8b5cf6", "order": 2, "emoji": "📞"},
    "meeting": {"label": "Reunión", "color": "#f59e0b", "order": 3, "emoji": "🤝"},
    "proposal": {"label": "Propuesta", "color": "#f97316", "order": 4, "emoji": "📄"},
    "negotiation": {"label": "Negociación", "color": "#ef4444", "order": 5, "emoji": "💬"},
    "won": {"label": "Ganados", "color": "#22c55e", "order": 6, "emoji": "🎉"},
    "lost": {"label": "Perdidos", "color": "#6b7280", "order": 7, "emoji": "❌"},
}


@dataclass
class KanbanCard:
    lead_id: int
    company_name: str | None
    contact_name: str | None
    score_icp: float | None
    c_level: bool
    afinidad: str
    region: str
    stage: str
    days_in_stage: int = 0
    outreach_count: int = 0
    last_activity: str = ""


@dataclass
class KanbanColumn:
    stage: str
    label: str
    color: str
    emoji: str
    cards: list[KanbanCard] = field(default_factory=list)
    count: int = 0
    total_score: float = 0


@dataclass
class KanbanBoard:
    columns: list[KanbanColumn]
    total_leads: int
    total_value_index: float  # sum of all scores as proxy for pipeline value
    generated_at: datetime = field(default_factory=datetime.now)


async def get_kanban_board(
    db: AsyncSession,
    exclude_closed: bool = False,
) -> KanbanBoard:
    """Generate full kanban board data from the database."""
    query = select(Lead)
    if exclude_closed:
        query = query.where(Lead.stage.notin_([LeadStage.WON.value, LeadStage.LOST.value]))
    query = query.order_by(Lead.score_icp.desc().nullslast())

    result = await db.execute(query)
    leads = list(result.scalars().all())

    # Group by stage
    columns_data: dict[str, list[KanbanCard]] = {stage: [] for stage in STAGE_CONFIG}
    now = datetime.now()

    for lead in leads:
        stage = lead.stage if isinstance(lead.stage, str) else lead.stage.value
        days = (now - lead.updated_at).days if lead.updated_at else 0

        card = KanbanCard(
            lead_id=lead.id,
            company_name=lead.company_name,
            contact_name=lead.contact_name,
            score_icp=lead.score_icp,
            c_level=lead.c_level,
            afinidad=lead.afinidad if isinstance(lead.afinidad, str) else lead.afinidad.value,
            region=lead.region if isinstance(lead.region, str) else lead.region.value,
            stage=stage,
            days_in_stage=days,
        )
        if stage in columns_data:
            columns_data[stage].append(card)

    columns = []
    total_leads = 0
    total_value = 0.0

    for stage, config in STAGE_CONFIG.items():
        cards = columns_data.get(stage, [])
        col_score = sum(c.score_icp or 0 for c in cards)
        columns.append(KanbanColumn(
            stage=stage,
            label=config["label"],
            color=config["color"],
            emoji=config["emoji"],
            cards=cards,
            count=len(cards),
            total_score=round(col_score, 1),
        ))
        total_leads += len(cards)
        total_value += col_score

    return KanbanBoard(
        columns=columns,
        total_leads=total_leads,
        total_value_index=round(total_value, 1),
    )


async def move_card(db: AsyncSession, lead_id: int, to_stage: str) -> bool:
    """Move a lead to a new stage (from kanban drag-and-drop)."""
    from xcapitsff.sales.pipeline import get_lead, is_valid_transition
    from xcapitsff.core.models import LeadStage

    lead = await get_lead(db, lead_id)
    if not lead:
        return False

    current = lead.stage if isinstance(lead.stage, str) else lead.stage.value
    target = LeadStage(to_stage)
    current_stage = LeadStage(current)

    if not is_valid_transition(current_stage, target):
        return False

    lead.stage = to_stage
    await db.flush()
    return True
