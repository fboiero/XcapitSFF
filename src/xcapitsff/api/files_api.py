"""API endpoints for file/document management."""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from xcapitsff.core.files import EntityType, FileManager, TenantPlan, file_manager


router = APIRouter(prefix="/files", tags=["Files"])


# --- Response schemas ---


class FileMetadataResponse(BaseModel):
    id: str
    tenant_id: str
    filename: str
    content_type: str
    size_bytes: int
    uploaded_by: str
    uploaded_at: str
    entity_type: str
    entity_id: str | None
    tags: list[str]
    description: str | None
    checksum: str
    storage_path: str


class StorageUsageResponse(BaseModel):
    total_files: int
    total_bytes: int
    by_type: dict[str, int]


class AttachRequest(BaseModel):
    entity_type: str
    entity_id: str


# --- Helpers ---


def _meta_to_response(meta) -> dict:
    return {
        "id": meta.id,
        "tenant_id": meta.tenant_id,
        "filename": meta.filename,
        "content_type": meta.content_type,
        "size_bytes": meta.size_bytes,
        "uploaded_by": meta.uploaded_by,
        "uploaded_at": meta.uploaded_at.isoformat(),
        "entity_type": meta.entity_type.value,
        "entity_id": meta.entity_id,
        "tags": meta.tags,
        "description": meta.description,
        "checksum": meta.checksum,
        "storage_path": meta.storage_path,
    }


def _get_manager() -> FileManager:
    return file_manager


# --- Endpoints ---


@router.post("/upload", response_model=FileMetadataResponse)
async def upload_file(
    file: UploadFile = File(...),
    tenant_id: str = Query(...),
    uploaded_by: str = Query(...),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    description: str | None = Query(default=None),
    tags: str | None = Query(default=None, description="Comma-separated tags"),
    tenant_plan: str = Query(default="FREE"),
):
    """Upload a file."""
    mgr = _get_manager()
    content = await file.read()
    filename = file.filename or "unnamed"

    # Validate
    valid, error = mgr.validate_upload(filename, len(content), tenant_plan)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    meta = mgr.upload(
        tenant_id=tenant_id,
        filename=filename,
        content=content,
        uploaded_by=uploaded_by,
        content_type=file.content_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        tags=tag_list,
    )
    return _meta_to_response(meta)


@router.get("", response_model=list[FileMetadataResponse])
async def list_files(
    tenant_id: str = Query(...),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
):
    """List files for a tenant."""
    mgr = _get_manager()
    files = mgr.list_files(tenant_id, entity_type=entity_type, entity_id=entity_id)
    return [_meta_to_response(m) for m in files]


@router.get("/usage", response_model=StorageUsageResponse)
async def storage_usage(tenant_id: str = Query(...)):
    """Get storage usage stats for a tenant."""
    mgr = _get_manager()
    return mgr.get_storage_usage(tenant_id)


@router.get("/search", response_model=list[FileMetadataResponse])
async def search_files(
    tenant_id: str = Query(...),
    q: str = Query(..., min_length=1),
):
    """Search files by filename, description, or tags."""
    mgr = _get_manager()
    results = mgr.search_files(tenant_id, q)
    return [_meta_to_response(m) for m in results]


@router.get("/{file_id}", response_model=FileMetadataResponse)
async def get_file_metadata(file_id: str):
    """Get file metadata."""
    mgr = _get_manager()
    meta = mgr.get_metadata(file_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="File not found")
    return _meta_to_response(meta)


@router.get("/{file_id}/download")
async def download_file(file_id: str):
    """Download file content."""
    mgr = _get_manager()
    result = mgr.download(file_id)
    if result is None:
        raise HTTPException(status_code=404, detail="File not found")
    meta, content = result
    return Response(
        content=content,
        media_type=meta.content_type,
        headers={"Content-Disposition": f"attachment; filename={meta.filename}"},
    )


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """Delete a file."""
    mgr = _get_manager()
    deleted = mgr.delete(file_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")
    return {"deleted": True, "file_id": file_id}


@router.post("/{file_id}/attach", response_model=FileMetadataResponse)
async def attach_to_entity(file_id: str, body: AttachRequest):
    """Attach a file to an entity."""
    mgr = _get_manager()
    meta = mgr.attach_to_entity(file_id, body.entity_type, body.entity_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="File not found")
    return _meta_to_response(meta)
