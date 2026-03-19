"""API endpoints for lead enrichment."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.models import Lead
from xcapitsff.sales.enrichment import enrich_lead, enrich_leads_batch

router = APIRouter(prefix="/enrichment", tags=["Enrichment"])


@router.post("/{lead_id}")
async def api_enrich_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Enrich a single lead with inferred data."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = {
        "id": lead.id,
        "company_name": lead.company_name,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "region": lead.region if isinstance(lead.region, str) else lead.region.value,
        "c_level": lead.c_level,
    }

    enrichment = enrich_lead(lead_data)
    return {
        "lead_id": lead_id,
        "fields_enriched": enrichment.fields_enriched,
        "inferred": enrichment.fields_inferred,
        "confidence": enrichment.confidence,
        "notes": enrichment.notes,
    }


@router.post("/batch")
async def api_enrich_batch(
    lead_ids: list[int],
    db: AsyncSession = Depends(get_db),
):
    """Enrich multiple leads."""
    result = await db.execute(select(Lead).where(Lead.id.in_(lead_ids)))
    leads = list(result.scalars().all())

    leads_data = [
        {
            "id": l.id,
            "company_name": l.company_name,
            "contact_name": l.contact_name,
            "contact_email": l.contact_email,
            "region": l.region if isinstance(l.region, str) else l.region.value,
            "c_level": l.c_level,
        }
        for l in leads
    ]

    results = enrich_leads_batch(leads_data)
    return {
        "count": len(results),
        "results": [
            {
                "lead_id": r.lead_id,
                "fields_enriched": r.fields_enriched,
                "inferred": r.fields_inferred,
                "confidence": r.confidence,
            }
            for r in results
        ],
    }
