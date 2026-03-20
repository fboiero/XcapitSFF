"""Bulk Operations API v2 — create, execute, and monitor bulk jobs + data imports."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from xcapitsff.core.bulk_operations import (
    BulkJobStatus,
    BulkOperationType,
    EntityType,
    PlanTier,
    bulk_engine,
)
from xcapitsff.core.data_import import ImportConfig, import_engine

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


# --- Request / Response schemas ---


class CreateBulkJobRequest(BaseModel):
    tenant_id: str
    operation: BulkOperationType
    entity_type: EntityType
    entity_ids: list[int]
    params: dict = {}
    created_by: str = ""
    plan: PlanTier = PlanTier.FREE


class BulkJobResponse(BaseModel):
    id: str
    tenant_id: str
    operation: str
    entity_type: str
    status: str
    total_count: int
    processed_count: int
    success_count: int
    error_count: int
    errors: list[dict]
    result_summary: dict
    created_by: str
    created_at: str
    started_at: str | None
    completed_at: str | None


class CreateImportRequest(BaseModel):
    tenant_id: str
    filename: str
    raw_data: str
    entity_type: str
    delimiter: str = ","
    has_header: bool = True
    field_mapping: dict[str, str] = {}
    skip_duplicates: bool = True
    update_existing: bool = False
    dry_run: bool = False


class PreviewImportRequest(BaseModel):
    raw_data: str
    delimiter: str = ","
    has_header: bool = True
    field_mapping: dict[str, str] = {}
    rows: int = 5


class FieldSuggestionsRequest(BaseModel):
    raw_data: str
    entity_type: str


# --- Helpers ---


def _job_to_response(job) -> dict:
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "operation": job.operation.value,
        "entity_type": job.entity_type.value,
        "status": job.status.value,
        "total_count": job.total_count,
        "processed_count": job.processed_count,
        "success_count": job.success_count,
        "error_count": job.error_count,
        "errors": job.errors,
        "result_summary": job.result_summary,
        "created_by": job.created_by,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


def _import_to_response(job) -> dict:
    return {
        "id": job.id,
        "tenant_id": job.tenant_id,
        "filename": job.filename,
        "entity_type": job.entity_type,
        "status": job.status,
        "total_rows": job.total_rows,
        "imported_rows": job.imported_rows,
        "skipped_rows": job.skipped_rows,
        "error_rows": job.error_rows,
        "errors": job.errors,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


# --- Bulk Job endpoints ---


@router.post("/jobs")
async def create_bulk_job(req: CreateBulkJobRequest):
    """Create a new bulk operation job."""
    try:
        job = bulk_engine.create_job(
            tenant_id=req.tenant_id,
            operation=req.operation,
            entity_type=req.entity_type,
            entity_ids=req.entity_ids,
            params=req.params,
            created_by=req.created_by,
            plan=req.plan,
        )
        return _job_to_response(job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/jobs/{job_id}/execute")
async def execute_bulk_job(job_id: str):
    """Execute a previously created bulk job."""
    try:
        job = bulk_engine.execute_job(job_id)
        return _job_to_response(job)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/jobs/{job_id}/cancel")
async def cancel_bulk_job(job_id: str):
    """Cancel a pending or processing bulk job."""
    try:
        job = bulk_engine.cancel_job(job_id)
        return _job_to_response(job)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/jobs")
async def list_bulk_jobs(
    tenant_id: str = Query(...),
    status: BulkJobStatus | None = Query(None),
):
    """List bulk jobs for a tenant, optionally filtered by status."""
    jobs = bulk_engine.list_jobs(tenant_id, status=status)
    return {"jobs": [_job_to_response(j) for j in jobs]}


@router.get("/jobs/{job_id}")
async def get_bulk_job(job_id: str):
    """Get details of a specific bulk job."""
    try:
        job = bulk_engine.get_job(job_id)
        return _job_to_response(job)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs/{job_id}/progress")
async def get_bulk_job_progress(job_id: str):
    """Get progress info for a bulk job."""
    try:
        return bulk_engine.get_job_progress(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# --- Import endpoints ---


@router.post("/import")
async def create_import_job(req: CreateImportRequest):
    """Create a new data import job."""
    config = ImportConfig(
        delimiter=req.delimiter,
        has_header=req.has_header,
        field_mapping=req.field_mapping,
        skip_duplicates=req.skip_duplicates,
        update_existing=req.update_existing,
        dry_run=req.dry_run,
    )
    try:
        job = import_engine.create_import(
            tenant_id=req.tenant_id,
            filename=req.filename,
            raw_data=req.raw_data,
            entity_type=req.entity_type,
            config=config,
        )
        return _import_to_response(job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/import/preview")
async def preview_import(req: PreviewImportRequest):
    """Preview parsed rows without importing."""
    config = ImportConfig(
        delimiter=req.delimiter,
        has_header=req.has_header,
        field_mapping=req.field_mapping,
    )
    try:
        preview = import_engine.preview_import(
            raw_data=req.raw_data,
            config=config,
            rows=req.rows,
        )
        return {"rows": preview, "count": len(preview)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/import/{job_id}/execute")
async def execute_import_job(job_id: str):
    """Execute a previously created import job."""
    try:
        job = import_engine.execute_import(job_id)
        return _import_to_response(job)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/import/field-suggestions")
async def get_field_suggestions(req: FieldSuggestionsRequest):
    """Get auto-mapped field suggestions for CSV column headers."""
    try:
        suggestions = import_engine.get_field_suggestions(
            raw_data=req.raw_data,
            entity_type=req.entity_type,
        )
        return {"suggestions": suggestions}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
