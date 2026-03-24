"""Artifact Store API — browse, search, and manage versioned artifacts."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.core.artifact_store import (
    ArtifactFormat,
    ArtifactType,
    artifact_store,
)

router = APIRouter(prefix="/artifacts", tags=["Artifacts"])


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
            elif hasattr(v, "value"):  # enum
                d[f] = v.value
            else:
                d[f] = v
        return d
    return obj


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class StoreArtifactBody(BaseModel):
    workspace_id: str
    task_id: str
    type: str
    name: str
    content: str
    format: str = "markdown"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
def list_artifacts(
    workspace_id: Optional[str] = None,
    type: Optional[str] = None,
    task_id: Optional[str] = None,
):
    """List artifacts with optional filters."""
    if workspace_id:
        art_type = ArtifactType(type) if type else None
        results = artifact_store.list_by_workspace(workspace_id, artifact_type=art_type)
    elif task_id:
        results = artifact_store.list_by_task(task_id)
    else:
        # No filter — return all
        results = list(artifact_store._artifacts.values())
        if type:
            art_type = ArtifactType(type)
            results = [a for a in results if a.type == art_type]

    return [_serialize(a) for a in results]


@router.get("/search")
def search_artifacts(workspace_id: str, q: str):
    """Search artifacts by substring match."""
    results = artifact_store.search(workspace_id, q)
    return [_serialize(a) for a in results]


@router.get("/stats")
def artifact_stats(workspace_id: Optional[str] = None):
    """Get artifact statistics."""
    return artifact_store.get_stats(workspace_id=workspace_id)


@router.get("/{artifact_id}")
def get_artifact(artifact_id: str):
    """Get artifact detail and content."""
    artifact = artifact_store.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _serialize(artifact)


@router.get("/{artifact_id}/versions")
def get_version_history(artifact_id: str):
    """Get version history for an artifact."""
    history = artifact_store.get_version_history(artifact_id)
    if not history:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return [_serialize(a) for a in history]


@router.get("/{artifact_id}/diff/{other_id}")
def diff_versions(artifact_id: str, other_id: str):
    """Diff two artifact versions."""
    art_a = artifact_store.get(artifact_id)
    art_b = artifact_store.get(other_id)
    if art_a is None or art_b is None:
        raise HTTPException(status_code=404, detail="One or both artifacts not found")
    return artifact_store.diff_versions(artifact_id, other_id)


@router.post("/")
def store_artifact(body: StoreArtifactBody):
    """Store an artifact manually."""
    try:
        art_type = ArtifactType(body.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown artifact type: {body.type}")

    try:
        art_format = ArtifactFormat(body.format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown format: {body.format}")

    artifact = artifact_store.store(
        workspace_id=body.workspace_id,
        task_id=body.task_id,
        artifact_type=art_type,
        name=body.name,
        content=body.content,
        format=art_format,
    )
    return _serialize(artifact)
