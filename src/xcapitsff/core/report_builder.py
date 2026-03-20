"""Custom Report Builder — configurable report generation with templates.

Allows tenants to create, configure, and generate custom reports across
all modules: sales, support, campaigns, agents, and more. Supports
JSON, CSV, Markdown, and HTML output formats with in-memory storage.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ReportType(str, Enum):
    SALES_PIPELINE = "sales_pipeline"
    LEAD_PERFORMANCE = "lead_performance"
    TICKET_SUMMARY = "ticket_summary"
    AGENT_PERFORMANCE = "agent_performance"
    CAMPAIGN_ROI = "campaign_roi"
    CONVERSION_FUNNEL = "conversion_funnel"
    SLA_COMPLIANCE = "sla_compliance"
    REVENUE_FORECAST = "revenue_forecast"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ReportFilter:
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, not_in, contains, between
    value: Any

    VALID_OPERATORS = {"eq", "ne", "gt", "lt", "gte", "lte", "in", "not_in", "contains", "between"}

    def __post_init__(self):
        if self.operator not in self.VALID_OPERATORS:
            raise ValueError(f"Invalid operator '{self.operator}'. Must be one of {self.VALID_OPERATORS}")


@dataclass
class ReportColumn:
    field: str
    label: str
    aggregation: str = "none"  # none, sum, avg, count, min, max
    format: str | None = None  # currency, percentage, etc.

    VALID_AGGREGATIONS = {"none", "sum", "avg", "count", "min", "max"}

    def __post_init__(self):
        if self.aggregation not in self.VALID_AGGREGATIONS:
            raise ValueError(
                f"Invalid aggregation '{self.aggregation}'. Must be one of {self.VALID_AGGREGATIONS}"
            )


@dataclass
class ReportConfig:
    id: str
    tenant_id: str
    name: str
    type: ReportType
    columns: list[ReportColumn]
    filters: list[ReportFilter] = field(default_factory=list)
    group_by: list[str] | None = None
    sort_by: str | None = None
    sort_order: str = "asc"
    period_days: int = 30
    created_by: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    is_template: bool = False
    schedule: str | None = None  # cron expression


@dataclass
class GeneratedReport:
    id: str
    config_id: str
    tenant_id: str
    title: str
    generated_at: datetime
    data: list[dict]
    summary: dict
    row_count: int
    format: ReportFormat
    content: str


# ---------------------------------------------------------------------------
# Sample data generators per report type
# ---------------------------------------------------------------------------

_SAMPLE_DATA: dict[ReportType, list[dict]] = {
    ReportType.SALES_PIPELINE: [
        {"stage": "raw", "lead_count": 120, "value": 240000, "conversion_rate": 0.45, "avg_days": 5},
        {"stage": "qualified", "lead_count": 85, "value": 195000, "conversion_rate": 0.55, "avg_days": 8},
        {"stage": "contacted", "lead_count": 60, "value": 150000, "conversion_rate": 0.60, "avg_days": 12},
        {"stage": "meeting", "lead_count": 35, "value": 105000, "conversion_rate": 0.70, "avg_days": 15},
        {"stage": "proposal", "lead_count": 20, "value": 80000, "conversion_rate": 0.75, "avg_days": 20},
        {"stage": "negotiation", "lead_count": 12, "value": 60000, "conversion_rate": 0.80, "avg_days": 25},
        {"stage": "won", "lead_count": 8, "value": 48000, "conversion_rate": 1.0, "avg_days": 30},
    ],
    ReportType.LEAD_PERFORMANCE: [
        {"lead_name": "Acme Corp", "score_icp": 92, "region": "LATAM", "stage": "proposal", "days_in_pipeline": 18, "engagement": 85},
        {"lead_name": "TechGlobal", "score_icp": 87, "region": "Iberia", "stage": "meeting", "days_in_pipeline": 12, "engagement": 72},
        {"lead_name": "InnovaLab", "score_icp": 78, "region": "LATAM", "stage": "qualified", "days_in_pipeline": 8, "engagement": 60},
        {"lead_name": "DataFlow Inc", "score_icp": 75, "region": "USA", "stage": "contacted", "days_in_pipeline": 22, "engagement": 55},
        {"lead_name": "CloudNet", "score_icp": 65, "region": "Iberia", "stage": "raw", "days_in_pipeline": 3, "engagement": 30},
    ],
    ReportType.TICKET_SUMMARY: [
        {"category": "billing", "total": 45, "open": 12, "resolved": 33, "avg_resolution_hours": 4.2, "satisfaction": 4.5},
        {"category": "technical", "total": 78, "open": 25, "resolved": 53, "avg_resolution_hours": 8.1, "satisfaction": 4.1},
        {"category": "onboarding", "total": 30, "open": 8, "resolved": 22, "avg_resolution_hours": 6.5, "satisfaction": 4.3},
        {"category": "feature_request", "total": 22, "open": 18, "resolved": 4, "avg_resolution_hours": 24.0, "satisfaction": 3.8},
    ],
    ReportType.AGENT_PERFORMANCE: [
        {"agent_name": "Sales Qualifier", "tasks_completed": 150, "avg_response_time": 2.3, "accuracy": 0.92, "cost": 45.0},
        {"agent_name": "Support Responder", "tasks_completed": 220, "avg_response_time": 1.8, "accuracy": 0.88, "cost": 66.0},
        {"agent_name": "Outreach Composer", "tasks_completed": 95, "avg_response_time": 3.5, "accuracy": 0.90, "cost": 28.5},
        {"agent_name": "Ticket Router", "tasks_completed": 180, "avg_response_time": 0.5, "accuracy": 0.95, "cost": 18.0},
    ],
    ReportType.CAMPAIGN_ROI: [
        {"campaign": "Q1 Email Blast", "sent": 5000, "opened": 1250, "clicked": 375, "converted": 45, "revenue": 135000, "cost": 2500},
        {"campaign": "LinkedIn Outreach", "sent": 800, "opened": 320, "clicked": 96, "converted": 12, "revenue": 48000, "cost": 1200},
        {"campaign": "Webinar Series", "sent": 2000, "opened": 600, "clicked": 180, "converted": 25, "revenue": 75000, "cost": 5000},
    ],
    ReportType.CONVERSION_FUNNEL: [
        {"stage": "visitors", "count": 10000, "rate": 1.0, "drop_off": 0.0},
        {"stage": "leads", "count": 1200, "rate": 0.12, "drop_off": 0.88},
        {"stage": "qualified", "count": 480, "rate": 0.40, "drop_off": 0.60},
        {"stage": "opportunity", "count": 144, "rate": 0.30, "drop_off": 0.70},
        {"stage": "closed_won", "count": 43, "rate": 0.30, "drop_off": 0.70},
    ],
    ReportType.SLA_COMPLIANCE: [
        {"priority": "critical", "total": 25, "within_sla": 22, "breached": 3, "compliance_rate": 0.88, "avg_response_minutes": 12},
        {"priority": "high", "total": 60, "within_sla": 54, "breached": 6, "compliance_rate": 0.90, "avg_response_minutes": 28},
        {"priority": "medium", "total": 120, "within_sla": 114, "breached": 6, "compliance_rate": 0.95, "avg_response_minutes": 55},
        {"priority": "low", "total": 80, "within_sla": 78, "breached": 2, "compliance_rate": 0.975, "avg_response_minutes": 120},
    ],
    ReportType.REVENUE_FORECAST: [
        {"month": "2026-01", "pipeline_value": 320000, "weighted_value": 160000, "closed_revenue": 95000, "forecast_accuracy": 0.85},
        {"month": "2026-02", "pipeline_value": 280000, "weighted_value": 140000, "closed_revenue": 110000, "forecast_accuracy": 0.88},
        {"month": "2026-03", "pipeline_value": 350000, "weighted_value": 175000, "closed_revenue": 0, "forecast_accuracy": 0.0},
        {"month": "2026-04", "pipeline_value": 400000, "weighted_value": 200000, "closed_revenue": 0, "forecast_accuracy": 0.0},
    ],
    ReportType.CUSTOM: [
        {"item": "Item A", "value": 100, "category": "alpha"},
        {"item": "Item B", "value": 200, "category": "beta"},
        {"item": "Item C", "value": 150, "category": "alpha"},
    ],
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _apply_filters(data: list[dict], filters: list[ReportFilter]) -> list[dict]:
    """Apply filters to a list of row dicts."""
    result = data
    for f in filters:
        filtered: list[dict] = []
        for row in result:
            val = row.get(f.field)
            if val is None:
                continue
            if f.operator == "eq" and val == f.value:
                filtered.append(row)
            elif f.operator == "ne" and val != f.value:
                filtered.append(row)
            elif f.operator == "gt" and val > f.value:
                filtered.append(row)
            elif f.operator == "lt" and val < f.value:
                filtered.append(row)
            elif f.operator == "gte" and val >= f.value:
                filtered.append(row)
            elif f.operator == "lte" and val <= f.value:
                filtered.append(row)
            elif f.operator == "in" and val in f.value:
                filtered.append(row)
            elif f.operator == "not_in" and val not in f.value:
                filtered.append(row)
            elif f.operator == "contains" and isinstance(val, str) and f.value in val:
                filtered.append(row)
            elif f.operator == "between" and isinstance(f.value, (list, tuple)) and len(f.value) == 2:
                if f.value[0] <= val <= f.value[1]:
                    filtered.append(row)
        result = filtered
    return result


def _apply_grouping(data: list[dict], group_by: list[str], columns: list[ReportColumn]) -> list[dict]:
    """Group data by specified fields and compute aggregations."""
    groups: dict[tuple, list[dict]] = {}
    for row in data:
        key = tuple(row.get(g, None) for g in group_by)
        groups.setdefault(key, []).append(row)

    result: list[dict] = []
    for key, rows in groups.items():
        grouped_row: dict[str, Any] = {}
        for i, g in enumerate(group_by):
            grouped_row[g] = key[i]
        for col in columns:
            if col.field in group_by:
                continue
            values = [r.get(col.field) for r in rows if r.get(col.field) is not None]
            numeric_values = [v for v in values if isinstance(v, (int, float))]
            if col.aggregation == "sum":
                grouped_row[col.field] = sum(numeric_values) if numeric_values else 0
            elif col.aggregation == "avg":
                grouped_row[col.field] = (
                    round(sum(numeric_values) / len(numeric_values), 2) if numeric_values else 0
                )
            elif col.aggregation == "count":
                grouped_row[col.field] = len(values)
            elif col.aggregation == "min":
                grouped_row[col.field] = min(numeric_values) if numeric_values else 0
            elif col.aggregation == "max":
                grouped_row[col.field] = max(numeric_values) if numeric_values else 0
            else:
                # none — take first value
                grouped_row[col.field] = values[0] if values else None
        result.append(grouped_row)
    return result


def _compute_summary(data: list[dict], columns: list[ReportColumn]) -> dict:
    """Compute summary statistics for the data."""
    summary: dict[str, Any] = {"totals": {}, "averages": {}}
    for col in columns:
        values = [row.get(col.field) for row in data if row.get(col.field) is not None]
        numeric = [v for v in values if isinstance(v, (int, float))]
        if numeric:
            summary["totals"][col.field] = round(sum(numeric), 2)
            summary["averages"][col.field] = round(sum(numeric) / len(numeric), 2)
    return summary


def _format_json(title: str, data: list[dict], summary: dict) -> str:
    """Format report as JSON string."""
    return json.dumps({"title": title, "data": data, "summary": summary}, indent=2, default=str)


def _format_csv(columns: list[ReportColumn], data: list[dict]) -> str:
    """Format report as CSV string."""
    output = io.StringIO()
    headers = [col.label for col in columns]
    fields = [col.field for col in columns]
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in data:
        writer.writerow([row.get(f, "") for f in fields])
    return output.getvalue()


def _format_markdown(title: str, columns: list[ReportColumn], data: list[dict], summary: dict) -> str:
    """Format report as Markdown table."""
    lines: list[str] = [f"# {title}", ""]
    if not data:
        lines.append("*No data available.*")
        return "\n".join(lines)

    headers = [col.label for col in columns]
    fields = [col.field for col in columns]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in data:
        cells = [str(row.get(f, "")) for f in fields]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    if summary.get("totals"):
        lines.append("**Summary:**")
        for k, v in summary["totals"].items():
            lines.append(f"- Total {k}: {v}")
    return "\n".join(lines)


def _format_html(title: str, columns: list[ReportColumn], data: list[dict], summary: dict) -> str:
    """Format report as styled HTML table."""
    html_parts: list[str] = [
        "<!DOCTYPE html>",
        "<html><head>",
        f"<title>{title}</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; margin: 20px; }",
        "table { border-collapse: collapse; width: 100%; }",
        "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
        "th { background-color: #4CAF50; color: white; }",
        "tr:nth-child(even) { background-color: #f2f2f2; }",
        ".summary { margin-top: 20px; padding: 10px; background: #e8f5e9; border-radius: 4px; }",
        "</style>",
        "</head><body>",
        f"<h1>{title}</h1>",
        "<table>",
        "<thead><tr>",
    ]
    headers = [col.label for col in columns]
    fields = [col.field for col in columns]
    for h in headers:
        html_parts.append(f"<th>{h}</th>")
    html_parts.append("</tr></thead>")
    html_parts.append("<tbody>")
    for row in data:
        html_parts.append("<tr>")
        for f_name in fields:
            html_parts.append(f"<td>{row.get(f_name, '')}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table>")
    if summary.get("totals"):
        html_parts.append('<div class="summary">')
        html_parts.append("<h3>Summary</h3>")
        html_parts.append("<ul>")
        for k, v in summary["totals"].items():
            html_parts.append(f"<li>Total {k}: {v}</li>")
        html_parts.append("</ul></div>")
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


# ---------------------------------------------------------------------------
# Pre-built templates
# ---------------------------------------------------------------------------

_TEMPLATES: list[ReportConfig] = [
    ReportConfig(
        id="tmpl-sales-pipeline",
        tenant_id="__template__",
        name="Sales Pipeline Overview",
        type=ReportType.SALES_PIPELINE,
        columns=[
            ReportColumn(field="stage", label="Stage"),
            ReportColumn(field="lead_count", label="Lead Count", aggregation="sum"),
            ReportColumn(field="value", label="Value", aggregation="sum", format="currency"),
            ReportColumn(field="conversion_rate", label="Conversion Rate", format="percentage"),
            ReportColumn(field="avg_days", label="Avg Days", aggregation="avg"),
        ],
        is_template=True,
    ),
    ReportConfig(
        id="tmpl-lead-performance",
        tenant_id="__template__",
        name="Lead Performance Report",
        type=ReportType.LEAD_PERFORMANCE,
        columns=[
            ReportColumn(field="lead_name", label="Lead Name"),
            ReportColumn(field="score_icp", label="ICP Score", aggregation="avg"),
            ReportColumn(field="region", label="Region"),
            ReportColumn(field="stage", label="Stage"),
            ReportColumn(field="days_in_pipeline", label="Days in Pipeline", aggregation="avg"),
            ReportColumn(field="engagement", label="Engagement", format="percentage"),
        ],
        sort_by="score_icp",
        sort_order="desc",
        is_template=True,
    ),
    ReportConfig(
        id="tmpl-ticket-summary",
        tenant_id="__template__",
        name="Ticket Summary Report",
        type=ReportType.TICKET_SUMMARY,
        columns=[
            ReportColumn(field="category", label="Category"),
            ReportColumn(field="total", label="Total Tickets", aggregation="sum"),
            ReportColumn(field="open", label="Open", aggregation="sum"),
            ReportColumn(field="resolved", label="Resolved", aggregation="sum"),
            ReportColumn(field="avg_resolution_hours", label="Avg Resolution (h)", aggregation="avg"),
            ReportColumn(field="satisfaction", label="Satisfaction", aggregation="avg"),
        ],
        is_template=True,
    ),
    ReportConfig(
        id="tmpl-agent-performance",
        tenant_id="__template__",
        name="Agent Performance Report",
        type=ReportType.AGENT_PERFORMANCE,
        columns=[
            ReportColumn(field="agent_name", label="Agent"),
            ReportColumn(field="tasks_completed", label="Tasks Completed", aggregation="sum"),
            ReportColumn(field="avg_response_time", label="Avg Response Time (s)", aggregation="avg"),
            ReportColumn(field="accuracy", label="Accuracy", format="percentage"),
            ReportColumn(field="cost", label="Cost", aggregation="sum", format="currency"),
        ],
        is_template=True,
    ),
    ReportConfig(
        id="tmpl-campaign-roi",
        tenant_id="__template__",
        name="Campaign ROI Report",
        type=ReportType.CAMPAIGN_ROI,
        columns=[
            ReportColumn(field="campaign", label="Campaign"),
            ReportColumn(field="sent", label="Sent", aggregation="sum"),
            ReportColumn(field="opened", label="Opened", aggregation="sum"),
            ReportColumn(field="clicked", label="Clicked", aggregation="sum"),
            ReportColumn(field="converted", label="Converted", aggregation="sum"),
            ReportColumn(field="revenue", label="Revenue", aggregation="sum", format="currency"),
            ReportColumn(field="cost", label="Cost", aggregation="sum", format="currency"),
        ],
        is_template=True,
    ),
    ReportConfig(
        id="tmpl-conversion-funnel",
        tenant_id="__template__",
        name="Conversion Funnel Report",
        type=ReportType.CONVERSION_FUNNEL,
        columns=[
            ReportColumn(field="stage", label="Stage"),
            ReportColumn(field="count", label="Count", aggregation="sum"),
            ReportColumn(field="rate", label="Rate", format="percentage"),
            ReportColumn(field="drop_off", label="Drop-off", format="percentage"),
        ],
        is_template=True,
    ),
    ReportConfig(
        id="tmpl-sla-compliance",
        tenant_id="__template__",
        name="SLA Compliance Report",
        type=ReportType.SLA_COMPLIANCE,
        columns=[
            ReportColumn(field="priority", label="Priority"),
            ReportColumn(field="total", label="Total", aggregation="sum"),
            ReportColumn(field="within_sla", label="Within SLA", aggregation="sum"),
            ReportColumn(field="breached", label="Breached", aggregation="sum"),
            ReportColumn(field="compliance_rate", label="Compliance Rate", format="percentage"),
            ReportColumn(field="avg_response_minutes", label="Avg Response (min)", aggregation="avg"),
        ],
        is_template=True,
    ),
    ReportConfig(
        id="tmpl-revenue-forecast",
        tenant_id="__template__",
        name="Revenue Forecast Report",
        type=ReportType.REVENUE_FORECAST,
        columns=[
            ReportColumn(field="month", label="Month"),
            ReportColumn(field="pipeline_value", label="Pipeline Value", aggregation="sum", format="currency"),
            ReportColumn(field="weighted_value", label="Weighted Value", aggregation="sum", format="currency"),
            ReportColumn(field="closed_revenue", label="Closed Revenue", aggregation="sum", format="currency"),
            ReportColumn(field="forecast_accuracy", label="Forecast Accuracy", format="percentage"),
        ],
        is_template=True,
    ),
]


# ---------------------------------------------------------------------------
# ReportBuilder class
# ---------------------------------------------------------------------------


class ReportBuilder:
    """Configurable report builder with in-memory storage."""

    def __init__(self) -> None:
        self._configs: dict[str, ReportConfig] = {}
        self._reports: dict[str, GeneratedReport] = {}
        # Load templates
        for tmpl in _TEMPLATES:
            self._configs[tmpl.id] = tmpl

    # -- Config CRUD --------------------------------------------------------

    def create_config(
        self,
        tenant_id: str,
        name: str,
        type: ReportType,
        columns: list[ReportColumn],
        filters: list[ReportFilter] | None = None,
        group_by: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        period_days: int = 30,
        created_by: str | None = None,
    ) -> ReportConfig:
        config = ReportConfig(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            type=type,
            columns=columns,
            filters=filters or [],
            group_by=group_by,
            sort_by=sort_by,
            sort_order=sort_order,
            period_days=period_days,
            created_by=created_by,
            created_at=datetime.now(),
            is_template=False,
        )
        self._configs[config.id] = config
        return config

    def update_config(self, config_id: str, **kwargs: Any) -> ReportConfig:
        config = self._configs.get(config_id)
        if not config:
            raise ValueError(f"Config '{config_id}' not found")
        if config.is_template:
            raise ValueError("Cannot update a template config")
        for key, value in kwargs.items():
            if hasattr(config, key) and key not in ("id", "created_at", "is_template"):
                setattr(config, key, value)
        return config

    def delete_config(self, config_id: str) -> bool:
        config = self._configs.get(config_id)
        if not config:
            return False
        if config.is_template:
            raise ValueError("Cannot delete a template config")
        del self._configs[config_id]
        return True

    def list_configs(self, tenant_id: str) -> list[ReportConfig]:
        return [c for c in self._configs.values() if c.tenant_id == tenant_id and not c.is_template]

    # -- Report generation --------------------------------------------------

    def generate_report(
        self, config_id: str, format: ReportFormat = ReportFormat.JSON
    ) -> GeneratedReport:
        config = self._configs.get(config_id)
        if not config:
            raise ValueError(f"Config '{config_id}' not found")

        # Get sample data for the report type
        raw_data = [dict(row) for row in _SAMPLE_DATA.get(config.type, _SAMPLE_DATA[ReportType.CUSTOM])]

        # Apply filters
        data = _apply_filters(raw_data, config.filters)

        # Apply grouping
        if config.group_by:
            data = _apply_grouping(data, config.group_by, config.columns)

        # Apply sorting
        if config.sort_by:
            reverse = config.sort_order == "desc"
            data.sort(key=lambda r: r.get(config.sort_by, 0) or 0, reverse=reverse)

        # Compute summary
        summary = _compute_summary(data, config.columns)

        # Format output
        title = config.name
        if format == ReportFormat.JSON:
            content = _format_json(title, data, summary)
        elif format == ReportFormat.CSV:
            content = _format_csv(config.columns, data)
        elif format == ReportFormat.MARKDOWN:
            content = _format_markdown(title, config.columns, data, summary)
        elif format == ReportFormat.HTML:
            content = _format_html(title, config.columns, data, summary)
        else:
            content = _format_json(title, data, summary)

        report = GeneratedReport(
            id=str(uuid.uuid4()),
            config_id=config.id,
            tenant_id=config.tenant_id,
            title=title,
            generated_at=datetime.now(),
            data=data,
            summary=summary,
            row_count=len(data),
            format=format,
            content=content,
        )
        self._reports[report.id] = report
        return report

    # -- Export -------------------------------------------------------------

    def export_report(self, report_id: str, format: ReportFormat) -> str:
        report = self._reports.get(report_id)
        if not report:
            raise ValueError(f"Report '{report_id}' not found")

        config = self._configs.get(report.config_id)
        if not config:
            raise ValueError(f"Config '{report.config_id}' not found")

        title = report.title
        data = report.data
        summary = report.summary

        if format == ReportFormat.JSON:
            return _format_json(title, data, summary)
        elif format == ReportFormat.CSV:
            return _format_csv(config.columns, data)
        elif format == ReportFormat.MARKDOWN:
            return _format_markdown(title, config.columns, data, summary)
        elif format == ReportFormat.HTML:
            return _format_html(title, config.columns, data, summary)
        return _format_json(title, data, summary)

    # -- Templates ----------------------------------------------------------

    def get_report_templates(self) -> list[ReportConfig]:
        return [c for c in self._configs.values() if c.is_template]

    def clone_template(self, template_id: str, tenant_id: str, name: str) -> ReportConfig:
        template = self._configs.get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' not found")
        if not template.is_template:
            raise ValueError(f"Config '{template_id}' is not a template")

        cloned = ReportConfig(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            type=template.type,
            columns=list(template.columns),
            filters=list(template.filters),
            group_by=list(template.group_by) if template.group_by else None,
            sort_by=template.sort_by,
            sort_order=template.sort_order,
            period_days=template.period_days,
            created_by=None,
            created_at=datetime.now(),
            is_template=False,
        )
        self._configs[cloned.id] = cloned
        return cloned

    # -- Schedule -----------------------------------------------------------

    def schedule_report(self, config_id: str, schedule: str) -> ReportConfig:
        config = self._configs.get(config_id)
        if not config:
            raise ValueError(f"Config '{config_id}' not found")
        config.schedule = schedule
        return config

    # -- Generated reports listing ------------------------------------------

    def get_generated_reports(self, tenant_id: str, limit: int = 20) -> list[GeneratedReport]:
        reports = [r for r in self._reports.values() if r.tenant_id == tenant_id]
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        return reports[:limit]


# Module-level singleton
report_builder = ReportBuilder()
