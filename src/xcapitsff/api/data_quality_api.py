"""API endpoints for data-quality checks.

Exposes the quality-check engine so operators can inspect database health
via the REST API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.data_quality import (
    check_customer_quality,
    check_lead_quality,
    check_ticket_quality,
    run_full_quality_check,
)
from xcapitsff.core.database import get_db

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_report(report) -> dict:
    """Turn a DataQualityReport into a JSON-serialisable dict."""
    return {
        "total_records": report.total_records,
        "issues_found": report.issues_found,
        "issues_by_severity": dict(report.issues_by_severity),
        "details": [
            {
                "severity": d.severity,
                "entity_type": d.entity_type,
                "entity_id": d.entity_id,
                "field": d.field,
                "description": d.description,
            }
            for d in report.details
        ],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/")
async def api_full_quality_check(db: AsyncSession = Depends(get_db)):
    """Run a full data-quality check across leads, tickets, and customers."""
    return await run_full_quality_check(db)


@router.get("/leads")
async def api_lead_quality(db: AsyncSession = Depends(get_db)):
    """Run data-quality checks on the leads table only."""
    report = await check_lead_quality(db)
    return _serialize_report(report)


@router.get("/tickets")
async def api_ticket_quality(db: AsyncSession = Depends(get_db)):
    """Run data-quality checks on the tickets table only."""
    report = await check_ticket_quality(db)
    return _serialize_report(report)


@router.get("/customers")
async def api_customer_quality(db: AsyncSession = Depends(get_db)):
    """Run data-quality checks on the customers table only."""
    report = await check_customer_quality(db)
    return _serialize_report(report)
