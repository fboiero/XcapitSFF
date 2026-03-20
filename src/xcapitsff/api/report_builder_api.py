"""API endpoints for Custom Report Builder."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from xcapitsff.core.report_builder import (
    ReportBuilder,
    ReportColumn,
    ReportFilter,
    ReportFormat,
    ReportType,
    report_builder,
)

router = APIRouter(prefix="/report-builder", tags=["Report Builder"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ReportFilterSchema(BaseModel):
    field: str
    operator: str
    value: object


class ReportColumnSchema(BaseModel):
    field: str
    label: str
    aggregation: str = "none"
    format: str | None = None


class ConfigCreateSchema(BaseModel):
    tenant_id: str
    name: str
    type: str
    columns: list[ReportColumnSchema]
    filters: list[ReportFilterSchema] = Field(default_factory=list)
    group_by: list[str] | None = None
    sort_by: str | None = None
    sort_order: str = "asc"
    period_days: int = 30
    created_by: str | None = None


class ConfigUpdateSchema(BaseModel):
    name: str | None = None
    columns: list[ReportColumnSchema] | None = None
    filters: list[ReportFilterSchema] | None = None
    group_by: list[str] | None = None
    sort_by: str | None = None
    sort_order: str | None = None
    period_days: int | None = None


class CloneTemplateSchema(BaseModel):
    tenant_id: str
    name: str


class ScheduleSchema(BaseModel):
    schedule: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config_to_dict(config) -> dict:
    return {
        "id": config.id,
        "tenant_id": config.tenant_id,
        "name": config.name,
        "type": config.type.value if hasattr(config.type, "value") else config.type,
        "columns": [
            {"field": c.field, "label": c.label, "aggregation": c.aggregation, "format": c.format}
            for c in config.columns
        ],
        "filters": [
            {"field": f.field, "operator": f.operator, "value": f.value}
            for f in config.filters
        ],
        "group_by": config.group_by,
        "sort_by": config.sort_by,
        "sort_order": config.sort_order,
        "period_days": config.period_days,
        "created_by": config.created_by,
        "created_at": config.created_at.isoformat(),
        "is_template": config.is_template,
        "schedule": config.schedule,
    }


def _report_to_dict(report) -> dict:
    return {
        "id": report.id,
        "config_id": report.config_id,
        "tenant_id": report.tenant_id,
        "title": report.title,
        "generated_at": report.generated_at.isoformat(),
        "row_count": report.row_count,
        "format": report.format.value if hasattr(report.format, "value") else report.format,
        "summary": report.summary,
        "data": report.data,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/configs")
async def create_config(body: ConfigCreateSchema):
    """Create a new report configuration."""
    try:
        report_type = ReportType(body.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid report type: {body.type}")

    columns = [
        ReportColumn(field=c.field, label=c.label, aggregation=c.aggregation, format=c.format)
        for c in body.columns
    ]
    filters = [
        ReportFilter(field=f.field, operator=f.operator, value=f.value)
        for f in body.filters
    ]

    config = report_builder.create_config(
        tenant_id=body.tenant_id,
        name=body.name,
        type=report_type,
        columns=columns,
        filters=filters,
        group_by=body.group_by,
        sort_by=body.sort_by,
        sort_order=body.sort_order,
        period_days=body.period_days,
        created_by=body.created_by,
    )
    return _config_to_dict(config)


@router.get("/configs")
async def list_configs(tenant_id: str = Query(...)):
    """List report configurations for a tenant."""
    configs = report_builder.list_configs(tenant_id)
    return [_config_to_dict(c) for c in configs]


@router.put("/configs/{config_id}")
async def update_config(config_id: str, body: ConfigUpdateSchema):
    """Update an existing report configuration."""
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if "columns" in kwargs:
        kwargs["columns"] = [
            ReportColumn(field=c["field"], label=c["label"], aggregation=c["aggregation"], format=c["format"])
            for c in kwargs["columns"]
        ]
    if "filters" in kwargs:
        kwargs["filters"] = [
            ReportFilter(field=f["field"], operator=f["operator"], value=f["value"])
            for f in kwargs["filters"]
        ]
    try:
        config = report_builder.update_config(config_id, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _config_to_dict(config)


@router.delete("/configs/{config_id}")
async def delete_config(config_id: str):
    """Delete a report configuration."""
    try:
        deleted = report_builder.delete_config(config_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"deleted": True}


@router.post("/generate/{config_id}")
async def generate_report(config_id: str, format: str = Query(default="json")):
    """Generate a report from a configuration."""
    try:
        report_format = ReportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}")
    try:
        report = report_builder.generate_report(config_id, format=report_format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _report_to_dict(report)


@router.get("/reports")
async def list_reports(tenant_id: str = Query(...), limit: int = Query(default=20, ge=1, le=100)):
    """List generated reports for a tenant."""
    reports = report_builder.get_generated_reports(tenant_id, limit=limit)
    return [_report_to_dict(r) for r in reports]


@router.get("/reports/{report_id}/export")
async def export_report(report_id: str, format: str = Query(default="json")):
    """Export a generated report in the specified format."""
    try:
        report_format = ReportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid format: {format}")
    try:
        content = report_builder.export_report(report_id, format=report_format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"content": content, "format": format}


@router.get("/templates")
async def list_templates():
    """List all pre-built report templates."""
    templates = report_builder.get_report_templates()
    return [_config_to_dict(t) for t in templates]


@router.post("/templates/{template_id}/clone")
async def clone_template(template_id: str, body: CloneTemplateSchema):
    """Clone a template into a tenant-specific configuration."""
    try:
        config = report_builder.clone_template(template_id, body.tenant_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _config_to_dict(config)
