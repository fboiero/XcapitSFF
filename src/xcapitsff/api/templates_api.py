"""API endpoints for ticket response templates."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.support.templates import (
    get_all_templates,
    get_template,
    get_templates_by_category,
    render_template,
)

router = APIRouter(prefix="/templates", tags=["Templates"])


class RenderRequest(BaseModel):
    template_id: str
    data: dict


@router.get("/")
async def list_templates(category: str | None = None):
    if category:
        templates = get_templates_by_category(category)
    else:
        templates = get_all_templates()
    return {
        "count": len(templates),
        "templates": [
            {
                "template_id": t.template_id,
                "category": t.category,
                "name": t.name,
                "language": t.language.value,
                "tags": list(t.tags),
            }
            for t in templates
        ],
    }


@router.get("/{template_id}")
async def get_template_detail(template_id: str):
    t = get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "template_id": t.template_id,
        "category": t.category,
        "name": t.name,
        "language": t.language.value,
        "subject": t.subject,
        "body": t.body,
        "internal_note": t.internal_note,
        "tags": list(t.tags),
    }


@router.post("/render")
async def render_template_endpoint(req: RenderRequest):
    t = get_template(req.template_id)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    subject, body = render_template(t, req.data)
    return {"subject": subject, "body": body, "template_id": t.template_id}
