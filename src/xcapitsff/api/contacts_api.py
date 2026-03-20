"""API endpoints for Contact management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.contacts import ContactManager

router = APIRouter(prefix="/contacts", tags=["Contacts"])

# Shared in-memory manager instance
_manager = ContactManager()


def get_contact_manager() -> ContactManager:
    return _manager


# --- Pydantic schemas ---


class ContactCreateRequest(BaseModel):
    tenant_id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    company_id: str | None = None
    source: str = "manual"
    tags: list[str] = []
    custom_fields: dict = {}
    notes: str = ""
    owner_id: str | None = None


class ContactUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    company_id: str | None = None
    source: str | None = None
    tags: list[str] | None = None
    custom_fields: dict | None = None
    notes: str | None = None
    owner_id: str | None = None


class AssignRequest(BaseModel):
    owner_id: str


class MergeRequest(BaseModel):
    primary_id: str
    secondary_id: str


class ContactResponse(BaseModel):
    id: str
    tenant_id: str
    first_name: str
    last_name: str
    email: str | None
    phone: str | None
    title: str | None
    company_id: str | None
    source: str
    tags: list[str]
    custom_fields: dict
    notes: str
    created_at: str
    updated_at: str
    last_contacted_at: str | None
    owner_id: str | None


def _to_response(contact) -> dict:
    return {
        "id": contact.id,
        "tenant_id": contact.tenant_id,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "email": contact.email,
        "phone": contact.phone,
        "title": contact.title,
        "company_id": contact.company_id,
        "source": contact.source,
        "tags": contact.tags,
        "custom_fields": contact.custom_fields,
        "notes": contact.notes,
        "created_at": contact.created_at.isoformat(),
        "updated_at": contact.updated_at.isoformat(),
        "last_contacted_at": contact.last_contacted_at.isoformat() if contact.last_contacted_at else None,
        "owner_id": contact.owner_id,
    }


# --- Endpoints ---


@router.post("/", response_model=ContactResponse, status_code=201)
async def api_create_contact(data: ContactCreateRequest):
    try:
        kwargs = {}
        for field in ("phone", "title", "company_id", "source", "tags", "custom_fields", "notes", "owner_id"):
            val = getattr(data, field)
            if val is not None:
                kwargs[field] = val
        contact = get_contact_manager().create(
            tenant_id=data.tenant_id,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            **kwargs,
        )
        return _to_response(contact)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/", response_model=list[ContactResponse])
async def api_list_contacts(
    tenant_id: str = Query(...),
    company_id: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
):
    contacts = get_contact_manager().list_contacts(
        tenant_id=tenant_id,
        company_id=company_id,
        owner_id=owner_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [_to_response(c) for c in contacts]


@router.get("/search", response_model=list[ContactResponse])
async def api_search_contacts(
    tenant_id: str = Query(...),
    q: str = Query(...),
):
    contacts = get_contact_manager().search(tenant_id=tenant_id, query=q)
    return [_to_response(c) for c in contacts]


@router.get("/{contact_id}", response_model=ContactResponse)
async def api_get_contact(contact_id: str):
    try:
        contact = get_contact_manager().get(contact_id)
        return _to_response(contact)
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.put("/{contact_id}", response_model=ContactResponse)
async def api_update_contact(contact_id: str, data: ContactUpdateRequest):
    try:
        kwargs = {k: v for k, v in data.model_dump().items() if v is not None}
        contact = get_contact_manager().update(contact_id, **kwargs)
        return _to_response(contact)
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{contact_id}", status_code=204)
async def api_delete_contact(contact_id: str):
    deleted = get_contact_manager().delete(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.post("/{contact_id}/assign", response_model=ContactResponse)
async def api_assign_contact(contact_id: str, data: AssignRequest):
    try:
        contact = get_contact_manager().assign(contact_id, data.owner_id)
        return _to_response(contact)
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.post("/merge", response_model=ContactResponse)
async def api_merge_contacts(data: MergeRequest):
    try:
        contact = get_contact_manager().merge_contacts(data.primary_id, data.secondary_id)
        return _to_response(contact)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{contact_id}/timeline")
async def api_contact_timeline(contact_id: str):
    try:
        timeline = get_contact_manager().get_contact_timeline(contact_id)
        return {"contact_id": contact_id, "events": timeline}
    except KeyError:
        raise HTTPException(status_code=404, detail="Contact not found")
