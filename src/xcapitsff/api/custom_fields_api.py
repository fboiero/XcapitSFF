"""API endpoints for custom fields and tagging system."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.custom_fields import custom_field_manager
from xcapitsff.core.tags import tag_manager


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

fields_router = APIRouter(prefix="/fields", tags=["Custom Fields"])
tags_router = APIRouter(prefix="/tags", tags=["Tags"])


# ---------------------------------------------------------------------------
# Request / Response models — Custom Fields
# ---------------------------------------------------------------------------


class DefineFieldRequest(BaseModel):
    tenant_id: str
    entity_type: str
    name: str
    label: str
    field_type: str
    required: bool = False
    default_value: Any = None
    options: list[str] = []
    display_order: int = 0


class FieldDefinitionResponse(BaseModel):
    field_id: str
    tenant_id: str
    entity_type: str
    name: str
    label: str
    field_type: str
    required: bool
    default_value: Any
    options: list[str]
    display_order: int


class SetFieldValueRequest(BaseModel):
    value: Any


class FieldValuesResponse(BaseModel):
    entity_id: int
    values: dict[str, Any]


# ---------------------------------------------------------------------------
# Request / Response models — Tags
# ---------------------------------------------------------------------------


class CreateTagRequest(BaseModel):
    tenant_id: str
    name: str
    color: str = "#3B82F6"
    entity_type: str = "all"


class TagResponse(BaseModel):
    tag_id: str
    name: str
    color: str
    tenant_id: str
    entity_type: str
    created_at: str


class TagEntityRequest(BaseModel):
    entity_type: str
    entity_id: int


class PopularTagResponse(BaseModel):
    tag: TagResponse
    count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _field_def_to_response(d) -> FieldDefinitionResponse:
    return FieldDefinitionResponse(
        field_id=d.field_id,
        tenant_id=d.tenant_id,
        entity_type=d.entity_type,
        name=d.name,
        label=d.label,
        field_type=d.field_type.value,
        required=d.required,
        default_value=d.default_value,
        options=d.options,
        display_order=d.display_order,
    )


def _tag_to_response(t) -> TagResponse:
    return TagResponse(
        tag_id=t.tag_id,
        name=t.name,
        color=t.color,
        tenant_id=t.tenant_id,
        entity_type=t.entity_type,
        created_at=t.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Custom Fields endpoints
# ---------------------------------------------------------------------------


@fields_router.post("", response_model=FieldDefinitionResponse)
async def define_field(request: DefineFieldRequest):
    """Define a new custom field for a tenant + entity type."""
    try:
        defn = custom_field_manager.define_field(
            tenant_id=request.tenant_id,
            entity_type=request.entity_type,
            name=request.name,
            label=request.label,
            field_type=request.field_type,
            required=request.required,
            default_value=request.default_value,
            options=request.options,
            display_order=request.display_order,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _field_def_to_response(defn)


@fields_router.get(
    "/{entity_type}",
    response_model=list[FieldDefinitionResponse],
)
async def list_fields(
    entity_type: str,
    tenant_id: str = Query(..., description="Tenant ID"),
):
    """List all custom field definitions for a tenant + entity type."""
    fields = custom_field_manager.get_fields(tenant_id, entity_type)
    return [_field_def_to_response(f) for f in fields]


@fields_router.put("/{entity_type}/{entity_id}/{field_id}")
async def set_field_value(
    entity_type: str,
    entity_id: int,
    field_id: str,
    request: SetFieldValueRequest,
):
    """Set a custom field value for a specific entity."""
    field_def = custom_field_manager.get_field(field_id)
    if field_def is None:
        raise HTTPException(status_code=404, detail=f"Field '{field_id}' not found")

    if field_def.entity_type != entity_type:
        raise HTTPException(
            status_code=400,
            detail=f"Field belongs to entity type '{field_def.entity_type}', not '{entity_type}'",
        )

    try:
        custom_field_manager.set_value(field_id, entity_id, request.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"status": "ok", "field_id": field_id, "entity_id": entity_id}


@fields_router.get("/{entity_type}/{entity_id}", response_model=FieldValuesResponse)
async def get_field_values(entity_type: str, entity_id: int):
    """Get all custom field values for a specific entity."""
    values = custom_field_manager.get_values(entity_id)
    return FieldValuesResponse(entity_id=entity_id, values=values)


@fields_router.delete("/{field_id}")
async def delete_field(field_id: str):
    """Delete a custom field definition and all its stored values."""
    deleted = custom_field_manager.delete_field(field_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Field '{field_id}' not found")
    return {"status": "deleted", "field_id": field_id}


# ---------------------------------------------------------------------------
# Tags endpoints
# ---------------------------------------------------------------------------


@tags_router.post("", response_model=TagResponse)
async def create_tag(request: CreateTagRequest):
    """Create a new tag."""
    try:
        tag = tag_manager.create_tag(
            tenant_id=request.tenant_id,
            name=request.name,
            color=request.color,
            entity_type=request.entity_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return _tag_to_response(tag)


@tags_router.get("", response_model=list[TagResponse])
async def list_tags(
    tenant_id: str = Query(..., description="Tenant ID"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
):
    """List tags for a tenant."""
    tags = tag_manager.get_tags(tenant_id, entity_type)
    return [_tag_to_response(t) for t in tags]


@tags_router.post("/{tag_id}/tag")
async def tag_entity(tag_id: str, request: TagEntityRequest):
    """Add a tag to an entity."""
    try:
        added = tag_manager.tag_entity(tag_id, request.entity_type, request.entity_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"status": "tagged" if added else "already_tagged", "tag_id": tag_id}


@tags_router.post("/{tag_id}/untag")
async def untag_entity(tag_id: str, request: TagEntityRequest):
    """Remove a tag from an entity."""
    removed = tag_manager.untag_entity(tag_id, request.entity_type, request.entity_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Tag association not found")
    return {"status": "untagged", "tag_id": tag_id}


@tags_router.get("/popular", response_model=list[PopularTagResponse])
async def popular_tags(
    tenant_id: str = Query(..., description="Tenant ID"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get the most used tags for a tenant."""
    popular = tag_manager.get_popular_tags(tenant_id, limit)
    return [
        PopularTagResponse(tag=_tag_to_response(tag), count=count)
        for tag, count in popular
    ]


@tags_router.get("/{entity_type}/{entity_id}", response_model=list[TagResponse])
async def get_entity_tags(entity_type: str, entity_id: int):
    """Get all tags on a specific entity."""
    tags = tag_manager.get_entity_tags(entity_type, entity_id)
    return [_tag_to_response(t) for t in tags]
