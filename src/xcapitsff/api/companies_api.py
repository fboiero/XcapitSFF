"""API endpoints for Company management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.companies import CompanyManager
from xcapitsff.api.contacts_api import get_contact_manager

router = APIRouter(prefix="/companies", tags=["Companies"])

# Shared in-memory manager instance (linked to contact manager)
_manager = CompanyManager(contact_manager=get_contact_manager())


def get_company_manager() -> CompanyManager:
    return _manager


# --- Pydantic schemas ---


class CompanyCreateRequest(BaseModel):
    tenant_id: str
    name: str
    domain: str | None = None
    industry: str | None = None
    size: str | None = None
    revenue_range: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str | None = None
    tags: list[str] = []
    custom_fields: dict = {}
    parent_company_id: str | None = None
    owner_id: str | None = None


class CompanyUpdateRequest(BaseModel):
    name: str | None = None
    domain: str | None = None
    industry: str | None = None
    size: str | None = None
    revenue_range: str | None = None
    country: str | None = None
    city: str | None = None
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    logo_url: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    parent_company_id: str | None = None
    owner_id: str | None = None


class MergeRequest(BaseModel):
    primary_id: str
    secondary_id: str


class CompanyResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    domain: str | None
    industry: str | None
    size: str | None
    revenue_range: str | None
    country: str | None
    city: str | None
    address: str | None
    phone: str | None
    website: str | None
    logo_url: str | None
    description: str | None
    tags: list[str]
    custom_fields: dict
    parent_company_id: str | None
    created_at: str
    updated_at: str
    owner_id: str | None


def _to_response(company) -> dict:
    return {
        "id": company.id,
        "tenant_id": company.tenant_id,
        "name": company.name,
        "domain": company.domain,
        "industry": company.industry,
        "size": company.size,
        "revenue_range": company.revenue_range,
        "country": company.country,
        "city": company.city,
        "address": company.address,
        "phone": company.phone,
        "website": company.website,
        "logo_url": company.logo_url,
        "description": company.description,
        "tags": company.tags,
        "custom_fields": company.custom_fields,
        "parent_company_id": company.parent_company_id,
        "created_at": company.created_at.isoformat(),
        "updated_at": company.updated_at.isoformat(),
        "owner_id": company.owner_id,
    }


# --- Endpoints ---


@router.post("/", response_model=CompanyResponse, status_code=201)
async def api_create_company(data: CompanyCreateRequest):
    try:
        kwargs = {}
        for field in (
            "domain", "industry", "size", "revenue_range", "country", "city",
            "address", "phone", "website", "logo_url", "description",
            "tags", "custom_fields", "parent_company_id", "owner_id",
        ):
            val = getattr(data, field)
            if val is not None:
                kwargs[field] = val
        company = get_company_manager().create(
            tenant_id=data.tenant_id,
            name=data.name,
            **kwargs,
        )
        return _to_response(company)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=list[CompanyResponse])
async def api_list_companies(
    tenant_id: str = Query(...),
    industry: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    companies = get_company_manager().list_companies(
        tenant_id=tenant_id,
        industry=industry,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [_to_response(c) for c in companies]


@router.get("/search", response_model=list[CompanyResponse])
async def api_search_companies(
    tenant_id: str = Query(...),
    q: str = Query(...),
):
    companies = get_company_manager().search(tenant_id=tenant_id, query=q)
    return [_to_response(c) for c in companies]


@router.get("/{company_id}", response_model=CompanyResponse)
async def api_get_company(company_id: str):
    try:
        company = get_company_manager().get(company_id)
        return _to_response(company)
    except KeyError:
        raise HTTPException(status_code=404, detail="Company not found")


@router.put("/{company_id}", response_model=CompanyResponse)
async def api_update_company(company_id: str, data: CompanyUpdateRequest):
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None}
        company = get_company_manager().update(company_id, **kwargs)
        return _to_response(company)
    except KeyError:
        raise HTTPException(status_code=404, detail="Company not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{company_id}", status_code=204)
async def api_delete_company(company_id: str):
    deleted = get_company_manager().delete(company_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Company not found")


@router.get("/{company_id}/contacts")
async def api_company_contacts(company_id: str):
    try:
        contacts = get_company_manager().get_company_contacts(company_id)
        return [
            {
                "id": c.id,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "email": c.email,
                "title": c.title,
                "owner_id": c.owner_id,
            }
            for c in contacts
        ]
    except KeyError:
        raise HTTPException(status_code=404, detail="Company not found")


@router.get("/{company_id}/hierarchy")
async def api_company_hierarchy(company_id: str):
    try:
        hierarchy = get_company_manager().get_hierarchy(company_id)
        return {
            "company": _to_response(hierarchy["company"]),
            "parent": _to_response(hierarchy["parent"]) if hierarchy["parent"] else None,
            "siblings": [_to_response(s) for s in hierarchy["siblings"]],
            "children": [_to_response(ch) for ch in hierarchy["children"]],
        }
    except KeyError:
        raise HTTPException(status_code=404, detail="Company not found")


@router.get("/{company_id}/stats")
async def api_company_stats(company_id: str):
    try:
        stats = get_company_manager().get_stats(company_id)
        return stats
    except KeyError:
        raise HTTPException(status_code=404, detail="Company not found")


@router.post("/{company_id}/enrich", response_model=CompanyResponse)
async def api_enrich_company(company_id: str):
    try:
        company = get_company_manager().enrich(company_id)
        return _to_response(company)
    except KeyError:
        raise HTTPException(status_code=404, detail="Company not found")


@router.post("/merge", response_model=CompanyResponse)
async def api_merge_companies(data: MergeRequest):
    try:
        company = get_company_manager().merge_companies(data.primary_id, data.secondary_id)
        return _to_response(company)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
