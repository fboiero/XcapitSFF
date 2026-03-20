"""API endpoints for saved views & filters."""

from fastapi import APIRouter, HTTPException, Query

from xcapitsff.core.saved_views import (
    FilterCondition,
    SavedViewManager,
    SortOrder,
    ViewConfig,
    ViewEntity,
    saved_view_manager,
)

router = APIRouter(prefix="/views", tags=["Saved Views"])


def _build_config(data: dict) -> ViewConfig:
    """Build a ViewConfig from a request dict."""
    filters = []
    for f in data.get("filters", []):
        filters.append(FilterCondition(
            field=f["field"],
            operator=f["operator"],
            value=f.get("value"),
        ))
    sort_order = SortOrder.DESC
    if data.get("sort_order"):
        sort_order = SortOrder(data["sort_order"])

    return ViewConfig(
        columns=data.get("columns", []),
        filters=filters,
        sort_by=data.get("sort_by", ""),
        sort_order=sort_order,
        group_by=data.get("group_by"),
        page_size=data.get("page_size", 25),
    )


@router.post("/")
async def create_view(
    tenant_id: str,
    user_id: str,
    entity: str,
    name: str,
    config: dict,
    description: str = "",
    is_shared: bool = False,
):
    """Create a new saved view."""
    try:
        entity_enum = ViewEntity(entity)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity: {entity}")

    view_config = _build_config(config)
    view = saved_view_manager.create(
        tenant_id=tenant_id,
        user_id=user_id,
        entity=entity_enum,
        name=name,
        config=view_config,
        description=description,
        is_shared=is_shared,
    )
    return view.to_dict()


@router.get("/")
async def list_views(
    tenant_id: str,
    user_id: str,
    entity: str | None = None,
):
    """List saved views for a user (own + shared)."""
    views = saved_view_manager.get_views(tenant_id, user_id, entity=entity)
    return {"count": len(views), "views": [v.to_dict() for v in views]}


@router.put("/{view_id}")
async def update_view(view_id: str, name: str | None = None, description: str | None = None):
    """Update a saved view."""
    kwargs = {}
    if name is not None:
        kwargs["name"] = name
    if description is not None:
        kwargs["description"] = description

    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")

    view = saved_view_manager.update(view_id, **kwargs)
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    return view.to_dict()


@router.delete("/{view_id}")
async def delete_view(view_id: str):
    """Delete a saved view."""
    deleted = saved_view_manager.delete(view_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="View not found")
    return {"deleted": True}


@router.post("/{view_id}/default")
async def set_default_view(view_id: str, user_id: str):
    """Set a view as default for the user."""
    view = saved_view_manager.set_default(view_id, user_id)
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    return view.to_dict()


@router.post("/{view_id}/duplicate")
async def duplicate_view(view_id: str, new_name: str):
    """Duplicate a view with a new name."""
    view = saved_view_manager.duplicate(view_id, new_name)
    if not view:
        raise HTTPException(status_code=404, detail="View not found")
    return view.to_dict()


@router.get("/popular")
async def popular_views(
    tenant_id: str,
    entity: str,
    limit: int = Query(default=5, le=20),
):
    """Get the most popular views for an entity."""
    try:
        entity_enum = ViewEntity(entity)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid entity: {entity}")

    views = saved_view_manager.get_popular_views(tenant_id, entity_enum, limit=limit)
    return {"count": len(views), "views": [v.to_dict() for v in views]}
