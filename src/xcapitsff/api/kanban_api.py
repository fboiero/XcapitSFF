"""API endpoints for Kanban board."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.sales.kanban import get_kanban_board, move_card

router = APIRouter(prefix="/kanban", tags=["Kanban"])


class MoveCardRequest(BaseModel):
    to_stage: str


@router.get("/board")
async def api_kanban_board(
    exclude_closed: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Get full kanban board with all columns and cards."""
    board = await get_kanban_board(db, exclude_closed=exclude_closed)
    return {
        "total_leads": board.total_leads,
        "total_value_index": board.total_value_index,
        "generated_at": board.generated_at.isoformat(),
        "columns": [
            {
                "stage": col.stage,
                "label": col.label,
                "color": col.color,
                "emoji": col.emoji,
                "count": col.count,
                "total_score": col.total_score,
                "cards": [
                    {
                        "lead_id": c.lead_id,
                        "company_name": c.company_name,
                        "contact_name": c.contact_name,
                        "score_icp": c.score_icp,
                        "c_level": c.c_level,
                        "afinidad": c.afinidad,
                        "region": c.region,
                        "days_in_stage": c.days_in_stage,
                    }
                    for c in col.cards
                ],
            }
            for col in board.columns
        ],
    }


@router.post("/move/{lead_id}")
async def api_move_card(
    lead_id: int,
    req: MoveCardRequest,
    db: AsyncSession = Depends(get_db),
):
    """Move a card to a different stage (drag-and-drop)."""
    success = await move_card(db, lead_id, req.to_stage)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid move or lead not found")
    return {"status": "moved", "lead_id": lead_id, "to_stage": req.to_stage}
