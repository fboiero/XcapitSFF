"""API endpoints for Email Template management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.email_templates import (
    EmailTemplateManager,
    TemplateCategory,
    email_template_manager,
)

router = APIRouter(prefix="/email-templates", tags=["Email Templates"])


# --- Request models ---


class TemplateCreateRequest(BaseModel):
    tenant_id: str
    name: str
    category: str
    subject: str
    body_html: str
    body_text: str | None = None
    tags: list[str] | None = None
    created_by: str | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None
    tags: list[str] | None = None


class RenderRequest(BaseModel):
    variables: dict


class PreviewRequest(BaseModel):
    sample_data: dict | None = None


class DuplicateRequest(BaseModel):
    new_name: str


# --- Endpoints ---


@router.post("/", status_code=201)
async def create_template(req: TemplateCreateRequest):
    template = email_template_manager.create(
        tenant_id=req.tenant_id,
        name=req.name,
        category=req.category,
        subject=req.subject,
        body_html=req.body_html,
        body_text=req.body_text,
        tags=req.tags,
        created_by=req.created_by,
    )
    return _serialize(template)


@router.get("/")
async def list_templates(
    tenant_id: str = Query(...),
    category: str | None = None,
    search: str | None = None,
):
    templates = email_template_manager.list_templates(
        tenant_id=tenant_id, category=category, search=search
    )
    return {"count": len(templates), "templates": [_serialize(t) for t in templates]}


@router.get("/defaults")
async def get_default_templates():
    defaults = email_template_manager.get_default_templates()
    return {"count": len(defaults), "templates": defaults}


@router.post("/setup-defaults")
async def setup_defaults(tenant_id: str = Query(...)):
    templates = email_template_manager.setup_defaults(tenant_id)
    return {"count": len(templates), "templates": [_serialize(t) for t in templates]}


@router.get("/{template_id}")
async def get_template(template_id: str):
    template = email_template_manager.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    return _serialize(template)


@router.put("/{template_id}")
async def update_template(template_id: str, req: TemplateUpdateRequest):
    try:
        kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
        template = email_template_manager.update(template_id, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email template not found")
    return _serialize(template)


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    if not email_template_manager.delete(template_id):
        raise HTTPException(status_code=404, detail="Email template not found")
    return {"deleted": True}


@router.post("/{template_id}/render")
async def render_template(template_id: str, req: RenderRequest):
    try:
        result = email_template_manager.render(template_id, req.variables)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email template not found")
    return result


@router.post("/{template_id}/duplicate")
async def duplicate_template(template_id: str, req: DuplicateRequest):
    try:
        template = email_template_manager.duplicate(template_id, req.new_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="Email template not found")
    return _serialize(template)


# --- Serialiser ---


def _serialize(t) -> dict:
    return {
        "id": t.id,
        "tenant_id": t.tenant_id,
        "name": t.name,
        "category": t.category.value,
        "subject": t.subject,
        "body_html": t.body_html,
        "body_text": t.body_text,
        "variables": t.variables,
        "thumbnail_preview": t.thumbnail_preview,
        "tags": t.tags,
        "is_default": t.is_default,
        "usage_count": t.usage_count,
        "created_by": t.created_by,
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
    }
