"""API endpoints for structured reports."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.reporting import generate_executive_report

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/executive")
async def api_executive_report(
    format: str = Query(default="json", pattern="^(json|text|markdown)$"),
    db: AsyncSession = Depends(get_db),
):
    """Generate executive report in JSON, text, or markdown format."""
    report = await generate_executive_report(db)

    if format == "text":
        return PlainTextResponse(report.to_text())
    elif format == "markdown":
        return PlainTextResponse(report.to_markdown(), media_type="text/markdown")
    else:
        return report.to_dict()
