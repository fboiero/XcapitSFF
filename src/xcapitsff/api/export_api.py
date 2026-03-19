"""API endpoints for data export."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.sales.export import export_leads_csv, export_leads_json, export_pipeline_summary

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/leads/csv")
async def api_export_leads_csv(
    include_outreach: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Export all leads as downloadable CSV."""
    result = await export_leads_csv(db, include_outreach=include_outreach)
    return Response(
        content=result.content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={result.filename}"},
    )


@router.get("/leads/json")
async def api_export_leads_json(db: AsyncSession = Depends(get_db)):
    """Export all leads as downloadable JSON."""
    result = await export_leads_json(db)
    return Response(
        content=result.content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={result.filename}"},
    )


@router.get("/pipeline/csv")
async def api_export_pipeline_summary(db: AsyncSession = Depends(get_db)):
    """Export pipeline summary as CSV."""
    result = await export_pipeline_summary(db)
    return Response(
        content=result.content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={result.filename}"},
    )
