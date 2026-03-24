"""Workspace API — manage project workspaces, phases, and requirements."""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.project_workspace import (
    ProjectStatus,
    Workspace,
    workspace_manager,
)

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


# ---------------------------------------------------------------------------
# Serialization helper
# ---------------------------------------------------------------------------

def _serialize(obj):
    """Convert dataclass instances to JSON-safe dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        d = {}
        for f in obj.__dataclass_fields__:
            v = getattr(obj, f)
            if isinstance(v, datetime):
                d[f] = v.isoformat() if v else None
            elif isinstance(v, list):
                d[f] = [_serialize(i) if hasattr(i, "__dataclass_fields__") else
                        (i.value if hasattr(i, "value") else i) for i in v]
            elif isinstance(v, dict):
                d[f] = v
            elif hasattr(v, "value"):  # enum
                d[f] = v.value
            else:
                d[f] = v
        return d
    return obj


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class CreateWorkspaceBody(BaseModel):
    tenant_id: str
    name: str
    client_name: str
    description: str = ""


class UpdateWorkspaceBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None


class AddRequirementBody(BaseModel):
    requirement: str


class UpdateStatusBody(BaseModel):
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/")
def create_workspace(body: CreateWorkspaceBody):
    """Create a new workspace."""
    ws = workspace_manager.create(
        tenant_id=body.tenant_id,
        name=body.name,
        client_name=body.client_name,
        description=body.description,
    )
    return _serialize(ws)


@router.get("/")
def list_workspaces(tenant_id: Optional[str] = None, status: Optional[str] = None):
    """List workspaces with optional filters."""
    st = ProjectStatus(status) if status else None
    workspaces = workspace_manager.list_workspaces(tenant_id=tenant_id, status=st)
    return [_serialize(w) for w in workspaces]


@router.get("/stats")
def workspace_stats():
    """Return overall workspace statistics."""
    return workspace_manager.get_stats()


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str):
    """Get workspace detail."""
    ws = workspace_manager.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _serialize(ws)


@router.patch("/{workspace_id}")
def update_workspace(workspace_id: str, body: UpdateWorkspaceBody):
    """Update workspace fields."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    ws = workspace_manager.update_workspace(workspace_id, **updates)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _serialize(ws)


@router.post("/{workspace_id}/advance-phase")
def advance_phase(workspace_id: str):
    """Advance workspace to the next phase."""
    ws = workspace_manager.advance_phase(workspace_id)
    if ws is None:
        raise HTTPException(
            status_code=400,
            detail="Cannot advance phase (workspace not found, already at final phase, or gate not approved)",
        )
    return _serialize(ws)


@router.get("/{workspace_id}/phase-status")
def get_phase_status(workspace_id: str):
    """Get current phase and gate info."""
    status = workspace_manager.get_phase_status(workspace_id)
    if not status:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return status


@router.post("/{workspace_id}/requirements")
def add_requirement(workspace_id: str, body: AddRequirementBody):
    """Add a requirement to the workspace."""
    ok = workspace_manager.add_requirement(workspace_id, body.requirement)
    if not ok:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"workspace_id": workspace_id, "requirement": body.requirement, "added": True}


@router.get("/{workspace_id}/requirements")
def list_requirements(workspace_id: str):
    """List all requirements for a workspace."""
    ws = workspace_manager.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace_manager.get_requirements(workspace_id)


@router.patch("/{workspace_id}/status")
def change_status(workspace_id: str, body: UpdateStatusBody):
    """Change workspace status."""
    ws = workspace_manager.get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    status_map = {
        "active": workspace_manager.activate,
        "on_hold": workspace_manager.put_on_hold,
        "completed": workspace_manager.complete,
        "archived": workspace_manager.archive,
    }

    handler = status_map.get(body.status)
    if handler is None:
        raise HTTPException(status_code=400, detail=f"Unknown status: {body.status}")

    handler(workspace_id)
    return {"workspace_id": workspace_id, "status": body.status}
