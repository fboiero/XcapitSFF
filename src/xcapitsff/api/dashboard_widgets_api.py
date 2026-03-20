"""Dashboard Widgets API — customizable widget-based dashboard endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from xcapitsff.core.dashboard_widgets import (
    DashboardWidgetManager,
    WidgetSize,
    WidgetType,
    widget_manager,
)

router = APIRouter(prefix="/dashboard/widgets", tags=["Dashboard Widgets"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AddWidgetRequest(BaseModel):
    type: str = Field(..., description="Widget type (e.g. 'kpi', 'line_chart')")
    title: str = Field(..., min_length=1, max_length=120)
    description: str = ""
    config: dict = Field(default_factory=dict)
    size: str = WidgetSize.MEDIUM.value
    position: dict | None = None


class UpdateWidgetRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    config: dict | None = None
    size: str | None = None
    position: dict | None = None
    visible: bool | None = None


class ReorderRequest(BaseModel):
    widget_order: list[str] = Field(..., description="Ordered list of widget IDs")


class CloneRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=120)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DEFAULT_TENANT = "default"
_DEFAULT_USER = "default"


def _manager() -> DashboardWidgetManager:
    return widget_manager


def _parse_widget_type(raw: str) -> WidgetType:
    try:
        return WidgetType(raw)
    except ValueError:
        valid = [t.value for t in WidgetType]
        raise HTTPException(status_code=400, detail=f"Invalid widget type '{raw}'. Valid: {valid}")


def _parse_widget_size(raw: str) -> WidgetSize:
    try:
        return WidgetSize(raw)
    except ValueError:
        valid = [s.value for s in WidgetSize]
        raise HTTPException(status_code=400, detail=f"Invalid widget size '{raw}'. Valid: {valid}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def get_dashboard_widgets(
    tenant_id: str = Query(_DEFAULT_TENANT),
    user_id: str = Query(_DEFAULT_USER),
):
    """Get the current dashboard layout with data for all visible widgets."""
    mgr = _manager()
    return mgr.get_full_dashboard(tenant_id, user_id)


@router.get("/catalog")
async def get_widget_catalog():
    """Return the full widget catalog describing every available type."""
    mgr = _manager()
    return {"catalog": mgr.get_widget_catalog()}


@router.post("")
async def add_widget(
    body: AddWidgetRequest,
    tenant_id: str = Query(_DEFAULT_TENANT),
    user_id: str = Query(_DEFAULT_USER),
):
    """Add a new widget to the user's dashboard."""
    mgr = _manager()
    layout = mgr.get_layout(tenant_id, user_id)
    wtype = _parse_widget_type(body.type)
    wsize = _parse_widget_size(body.size)
    widget = mgr.add_widget(
        layout_id=layout.id,
        widget_type=wtype,
        title=body.title,
        config=body.config,
        size=wsize,
        position=body.position,
    )
    return {
        "id": widget.id,
        "type": widget.type.value,
        "title": widget.title,
        "description": widget.description,
        "config": widget.config,
        "size": widget.size.value,
        "position": widget.position,
        "visible": widget.visible,
    }


@router.put("/{widget_id}")
async def update_widget(
    widget_id: str,
    body: UpdateWidgetRequest,
    tenant_id: str = Query(_DEFAULT_TENANT),
    user_id: str = Query(_DEFAULT_USER),
):
    """Update a widget's properties."""
    mgr = _manager()
    layout = mgr.get_layout(tenant_id, user_id)
    kwargs: dict = {}
    if body.title is not None:
        kwargs["title"] = body.title
    if body.description is not None:
        kwargs["description"] = body.description
    if body.config is not None:
        kwargs["config"] = body.config
    if body.size is not None:
        kwargs["size"] = _parse_widget_size(body.size)
    if body.position is not None:
        kwargs["position"] = body.position
    if body.visible is not None:
        kwargs["visible"] = body.visible

    try:
        widget = mgr.update_widget(layout.id, widget_id, **kwargs)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Widget {widget_id} not found")

    return {
        "id": widget.id,
        "type": widget.type.value,
        "title": widget.title,
        "description": widget.description,
        "config": widget.config,
        "size": widget.size.value,
        "position": widget.position,
        "visible": widget.visible,
    }


@router.delete("/{widget_id}")
async def remove_widget(
    widget_id: str,
    tenant_id: str = Query(_DEFAULT_TENANT),
    user_id: str = Query(_DEFAULT_USER),
):
    """Remove a widget from the dashboard."""
    mgr = _manager()
    layout = mgr.get_layout(tenant_id, user_id)
    removed = mgr.remove_widget(layout.id, widget_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"Widget {widget_id} not found")
    return {"removed": True, "widget_id": widget_id}


@router.post("/reorder")
async def reorder_widgets(
    body: ReorderRequest,
    tenant_id: str = Query(_DEFAULT_TENANT),
    user_id: str = Query(_DEFAULT_USER),
):
    """Reorder dashboard widgets according to the provided list of IDs."""
    mgr = _manager()
    layout = mgr.get_layout(tenant_id, user_id)
    try:
        updated = mgr.reorder_widgets(layout.id, body.widget_order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "layout_id": updated.id,
        "widget_count": len(updated.widgets),
        "order": [w.id for w in updated.widgets],
    }


@router.post("/reset", name="reset_dashboard")
async def reset_to_default(
    tenant_id: str = Query(_DEFAULT_TENANT),
    user_id: str = Query(_DEFAULT_USER),
):
    """Reset the dashboard to the default widget configuration."""
    mgr = _manager()
    layout = mgr.get_layout(tenant_id, user_id)
    try:
        updated = mgr.reset_to_default(layout.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "layout_id": updated.id,
        "widget_count": len(updated.widgets),
        "is_default": updated.is_default,
    }


@router.post("/clone", name="clone_dashboard")
async def clone_layout(
    body: CloneRequest,
    tenant_id: str = Query(_DEFAULT_TENANT),
    user_id: str = Query(_DEFAULT_USER),
):
    """Clone the current layout under a new name."""
    mgr = _manager()
    layout = mgr.get_layout(tenant_id, user_id)
    try:
        cloned = mgr.clone_layout(layout.id, body.new_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {
        "layout_id": cloned.id,
        "name": cloned.name,
        "widget_count": len(cloned.widgets),
        "is_default": cloned.is_default,
    }
