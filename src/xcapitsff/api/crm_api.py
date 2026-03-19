"""API endpoints for CRM integration — import, export, and sync leads."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.core.models import Lead
from xcapitsff.integrations.crm import (
    CrmFactory,
    CrmSyncEngine,
    DEFAULT_MAPPINGS,
)

router = APIRouter(prefix="/crm", tags=["CRM Integration"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CrmImportRequest(BaseModel):
    provider: str
    config: dict = {}


class CrmExportRequest(BaseModel):
    provider: str
    config: dict = {}
    lead_ids: list[int] = []


class CrmSyncRequest(BaseModel):
    provider: str
    config: dict = {}
    lead_ids_to_export: list[int] = []


class CrmImportResponse(BaseModel):
    provider: str
    imported: int
    skipped: int
    errors: list[str] = []
    leads: list[dict] = []


class CrmExportResponse(BaseModel):
    provider: str
    exported: int
    errors: list[str] = []
    ids: list[str] = []


class CrmSyncResponse(BaseModel):
    provider: str
    imported: int
    exported: int
    updated: int
    skipped: int
    errors: list[str] = []


class FieldMappingResponse(BaseModel):
    provider: str
    field_map: dict[str, str]
    reverse_map: dict[str, str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/import", response_model=CrmImportResponse)
async def crm_import_leads(
    request: CrmImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import leads from a CRM provider."""
    try:
        provider = CrmFactory.get_provider(request.provider, request.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Fetch existing leads for dedup
    result = await db.execute(select(Lead))
    existing = result.scalars().all()
    existing_leads = [
        {"contact_email": lead.contact_email}
        for lead in existing
        if lead.contact_email
    ]

    # Import and dedup
    try:
        leads = provider.import_leads()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CRM import failed: {exc}")

    sync_result = CrmSyncEngine.sync_from_crm(provider, existing_leads)

    return CrmImportResponse(
        provider=request.provider,
        imported=sync_result.imported,
        skipped=sync_result.skipped,
        errors=sync_result.errors,
        leads=leads,
    )


@router.post("/export", response_model=CrmExportResponse)
async def crm_export_leads(
    request: CrmExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export leads to a CRM provider."""
    try:
        provider = CrmFactory.get_provider(request.provider, request.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Fetch leads to export
    query = select(Lead)
    if request.lead_ids:
        query = query.where(Lead.id.in_(request.lead_ids))

    result = await db.execute(query)
    leads = result.scalars().all()

    leads_data = [
        {
            "company_name": lead.company_name,
            "contact_name": lead.contact_name,
            "contact_email": lead.contact_email,
            "region": lead.region if isinstance(lead.region, str) else lead.region.value,
            "stage": lead.stage if isinstance(lead.stage, str) else lead.stage.value,
            "score_icp": lead.score_icp,
            "notes": lead.notes,
            "c_level": lead.c_level,
        }
        for lead in leads
    ]

    try:
        export_result = provider.export_leads(leads_data)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CRM export failed: {exc}")

    return CrmExportResponse(
        provider=request.provider,
        exported=export_result.exported_count,
        errors=export_result.errors,
        ids=export_result.ids,
    )


@router.get("/providers")
async def list_crm_providers():
    """List available CRM providers."""
    return {
        "providers": CrmFactory.list_providers(),
    }


@router.post("/sync", response_model=CrmSyncResponse)
async def crm_sync(
    request: CrmSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """Two-way sync with a CRM provider."""
    try:
        provider = CrmFactory.get_provider(request.provider, request.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Existing leads for dedup
    result = await db.execute(select(Lead))
    existing = result.scalars().all()
    existing_leads = [
        {"contact_email": lead.contact_email}
        for lead in existing
        if lead.contact_email
    ]

    # Leads to export
    leads_to_export: list[dict] = []
    if request.lead_ids_to_export:
        export_result = await db.execute(
            select(Lead).where(Lead.id.in_(request.lead_ids_to_export))
        )
        export_leads = export_result.scalars().all()
        leads_to_export = [
            {
                "company_name": lead.company_name,
                "contact_name": lead.contact_name,
                "contact_email": lead.contact_email,
                "region": lead.region if isinstance(lead.region, str) else lead.region.value,
                "stage": lead.stage if isinstance(lead.stage, str) else lead.stage.value,
                "score_icp": lead.score_icp,
                "notes": lead.notes,
                "c_level": lead.c_level,
            }
            for lead in export_leads
        ]

    try:
        sync_result = CrmSyncEngine.two_way_sync(
            provider, existing_leads, leads_to_export
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"CRM sync failed: {exc}")

    return CrmSyncResponse(
        provider=request.provider,
        imported=sync_result.imported,
        exported=sync_result.exported,
        updated=sync_result.updated,
        skipped=sync_result.skipped,
        errors=sync_result.errors,
    )


@router.get("/field-mappings/{provider}", response_model=FieldMappingResponse)
async def get_field_mappings(provider: str):
    """Get field mappings for a CRM provider."""
    key = provider.lower().strip()
    mapping = DEFAULT_MAPPINGS.get(key)
    if mapping is None:
        raise HTTPException(
            status_code=404,
            detail=f"No field mapping found for provider '{provider}'",
        )

    return FieldMappingResponse(
        provider=mapping.provider_name,
        field_map=mapping.field_map,
        reverse_map=mapping.reverse_map,
    )
