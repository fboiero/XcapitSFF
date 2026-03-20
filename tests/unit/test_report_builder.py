"""Tests for the Custom Report Builder."""

import json

import pytest

from xcapitsff.core.report_builder import (
    GeneratedReport,
    ReportBuilder,
    ReportColumn,
    ReportConfig,
    ReportFilter,
    ReportFormat,
    ReportType,
)


@pytest.fixture
def builder():
    """Fresh ReportBuilder instance for each test."""
    return ReportBuilder()


@pytest.fixture
def sample_columns():
    return [
        ReportColumn(field="stage", label="Stage"),
        ReportColumn(field="lead_count", label="Lead Count", aggregation="sum"),
        ReportColumn(field="value", label="Value", aggregation="sum", format="currency"),
    ]


# ---------------------------------------------------------------------------
# Config CRUD
# ---------------------------------------------------------------------------


def test_create_config(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1",
        name="My Sales Report",
        type=ReportType.SALES_PIPELINE,
        columns=sample_columns,
    )
    assert isinstance(config, ReportConfig)
    assert config.tenant_id == "t1"
    assert config.name == "My Sales Report"
    assert config.type == ReportType.SALES_PIPELINE
    assert len(config.columns) == 3
    assert config.is_template is False
    assert config.period_days == 30


def test_update_config(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="Original", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    updated = builder.update_config(config.id, name="Updated Name", period_days=60)
    assert updated.name == "Updated Name"
    assert updated.period_days == 60
    # id should not change
    assert updated.id == config.id


def test_update_config_not_found(builder):
    with pytest.raises(ValueError, match="not found"):
        builder.update_config("nonexistent-id", name="X")


def test_delete_config(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="To Delete", type=ReportType.CUSTOM, columns=sample_columns
    )
    assert builder.delete_config(config.id) is True
    # listing should be empty
    assert len(builder.list_configs("t1")) == 0


def test_delete_config_not_found(builder):
    assert builder.delete_config("nonexistent") is False


def test_delete_template_raises(builder):
    templates = builder.get_report_templates()
    assert len(templates) > 0
    with pytest.raises(ValueError, match="Cannot delete a template"):
        builder.delete_config(templates[0].id)


def test_list_configs(builder, sample_columns):
    builder.create_config(tenant_id="t1", name="R1", type=ReportType.SALES_PIPELINE, columns=sample_columns)
    builder.create_config(tenant_id="t1", name="R2", type=ReportType.TICKET_SUMMARY, columns=sample_columns)
    builder.create_config(tenant_id="t2", name="R3", type=ReportType.CUSTOM, columns=sample_columns)
    configs = builder.list_configs("t1")
    assert len(configs) == 2
    assert all(c.tenant_id == "t1" for c in configs)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def test_generate_report_produces_data(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="Pipeline", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    report = builder.generate_report(config.id)
    assert isinstance(report, GeneratedReport)
    assert report.row_count > 0
    assert len(report.data) > 0
    assert report.format == ReportFormat.JSON
    assert report.tenant_id == "t1"


def test_generate_report_with_grouping(builder):
    columns = [
        ReportColumn(field="region", label="Region"),
        ReportColumn(field="score_icp", label="Avg Score", aggregation="avg"),
        ReportColumn(field="engagement", label="Total Engagement", aggregation="sum"),
    ]
    config = builder.create_config(
        tenant_id="t1",
        name="Grouped",
        type=ReportType.LEAD_PERFORMANCE,
        columns=columns,
        group_by=["region"],
    )
    report = builder.generate_report(config.id)
    # grouped by region — LATAM and Iberia and USA
    regions = {row["region"] for row in report.data}
    assert len(regions) >= 2
    # Check aggregations applied
    for row in report.data:
        assert "score_icp" in row
        assert "engagement" in row


def test_generate_summary_statistics(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="Summary Test", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    report = builder.generate_report(config.id)
    assert "totals" in report.summary
    assert "averages" in report.summary
    # lead_count should have a total
    assert "lead_count" in report.summary["totals"]
    assert report.summary["totals"]["lead_count"] > 0


# ---------------------------------------------------------------------------
# Export formats
# ---------------------------------------------------------------------------


def test_export_json(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="JSON Export", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    report = builder.generate_report(config.id, format=ReportFormat.JSON)
    content = builder.export_report(report.id, ReportFormat.JSON)
    parsed = json.loads(content)
    assert "title" in parsed
    assert "data" in parsed
    assert "summary" in parsed


def test_export_csv(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="CSV Export", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    report = builder.generate_report(config.id)
    content = builder.export_report(report.id, ReportFormat.CSV)
    lines = content.strip().split("\n")
    # First line is header
    assert "Stage" in lines[0]
    assert "Lead Count" in lines[0]
    # Data rows
    assert len(lines) > 1


def test_export_markdown(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="MD Export", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    report = builder.generate_report(config.id)
    content = builder.export_report(report.id, ReportFormat.MARKDOWN)
    assert "# MD Export" in content
    assert "| Stage" in content
    assert "---" in content
    assert "Summary" in content


def test_export_html(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="HTML Export", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    report = builder.generate_report(config.id)
    content = builder.export_report(report.id, ReportFormat.HTML)
    assert "<html>" in content
    assert "<table>" in content
    assert "<th>Stage</th>" in content
    assert "HTML Export" in content


def test_export_report_not_found(builder):
    with pytest.raises(ValueError, match="not found"):
        builder.export_report("nonexistent", ReportFormat.JSON)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def test_templates_exist(builder):
    templates = builder.get_report_templates()
    assert len(templates) == 8
    types_covered = {t.type for t in templates}
    assert ReportType.SALES_PIPELINE in types_covered
    assert ReportType.LEAD_PERFORMANCE in types_covered
    assert ReportType.TICKET_SUMMARY in types_covered
    assert ReportType.AGENT_PERFORMANCE in types_covered
    assert ReportType.CAMPAIGN_ROI in types_covered
    assert ReportType.CONVERSION_FUNNEL in types_covered
    assert ReportType.SLA_COMPLIANCE in types_covered
    assert ReportType.REVENUE_FORECAST in types_covered


def test_clone_template(builder):
    templates = builder.get_report_templates()
    template = templates[0]
    cloned = builder.clone_template(template.id, "t1", "My Cloned Report")
    assert cloned.id != template.id
    assert cloned.tenant_id == "t1"
    assert cloned.name == "My Cloned Report"
    assert cloned.type == template.type
    assert cloned.is_template is False
    assert len(cloned.columns) == len(template.columns)
    # Cloned config should be in tenant configs
    configs = builder.list_configs("t1")
    assert any(c.id == cloned.id for c in configs)


def test_clone_non_template_raises(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="Not a template", type=ReportType.CUSTOM, columns=sample_columns
    )
    with pytest.raises(ValueError, match="not a template"):
        builder.clone_template(config.id, "t1", "Clone")


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


def test_schedule_report(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="Scheduled", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    assert config.schedule is None
    updated = builder.schedule_report(config.id, "0 9 * * 1")
    assert updated.schedule == "0 9 * * 1"


def test_schedule_report_not_found(builder):
    with pytest.raises(ValueError, match="not found"):
        builder.schedule_report("nonexistent", "0 9 * * 1")


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filter_application(builder):
    columns = [
        ReportColumn(field="stage", label="Stage"),
        ReportColumn(field="lead_count", label="Count", aggregation="sum"),
        ReportColumn(field="value", label="Value", aggregation="sum", format="currency"),
    ]
    filters = [ReportFilter(field="lead_count", operator="gte", value=50)]
    config = builder.create_config(
        tenant_id="t1",
        name="Filtered",
        type=ReportType.SALES_PIPELINE,
        columns=columns,
        filters=filters,
    )
    report = builder.generate_report(config.id)
    # All rows should have lead_count >= 50
    for row in report.data:
        assert row["lead_count"] >= 50


def test_filter_eq_operator(builder):
    columns = [
        ReportColumn(field="category", label="Category"),
        ReportColumn(field="total", label="Total", aggregation="sum"),
    ]
    filters = [ReportFilter(field="category", operator="eq", value="billing")]
    config = builder.create_config(
        tenant_id="t1",
        name="Eq Filter",
        type=ReportType.TICKET_SUMMARY,
        columns=columns,
        filters=filters,
    )
    report = builder.generate_report(config.id)
    assert report.row_count == 1
    assert report.data[0]["category"] == "billing"


# ---------------------------------------------------------------------------
# Column aggregations
# ---------------------------------------------------------------------------


def test_column_aggregations(builder):
    columns = [
        ReportColumn(field="region", label="Region"),
        ReportColumn(field="score_icp", label="Score Sum", aggregation="sum"),
        ReportColumn(field="engagement", label="Engagement Avg", aggregation="avg"),
        ReportColumn(field="days_in_pipeline", label="Min Days", aggregation="min"),
        ReportColumn(field="days_in_pipeline", label="Max Days", aggregation="max"),
    ]
    config = builder.create_config(
        tenant_id="t1",
        name="Aggregations",
        type=ReportType.LEAD_PERFORMANCE,
        columns=columns,
        group_by=["region"],
    )
    report = builder.generate_report(config.id)
    # Check that LATAM group has aggregated values
    latam_rows = [r for r in report.data if r.get("region") == "LATAM"]
    assert len(latam_rows) == 1
    latam = latam_rows[0]
    # sum of score_icp for LATAM leads (92 + 78 = 170)
    assert latam["score_icp"] == 170
    # avg of engagement for LATAM (85 + 60) / 2 = 72.5
    assert latam["engagement"] == 72.5


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


def test_multi_tenant_isolation(builder, sample_columns):
    c1 = builder.create_config(
        tenant_id="tenant-a", name="A Report", type=ReportType.SALES_PIPELINE, columns=sample_columns
    )
    c2 = builder.create_config(
        tenant_id="tenant-b", name="B Report", type=ReportType.TICKET_SUMMARY, columns=sample_columns
    )

    # Generate reports
    r1 = builder.generate_report(c1.id)
    r2 = builder.generate_report(c2.id)

    # Configs are isolated
    a_configs = builder.list_configs("tenant-a")
    b_configs = builder.list_configs("tenant-b")
    assert len(a_configs) == 1
    assert len(b_configs) == 1
    assert a_configs[0].id != b_configs[0].id

    # Reports are isolated
    a_reports = builder.get_generated_reports("tenant-a")
    b_reports = builder.get_generated_reports("tenant-b")
    assert len(a_reports) == 1
    assert len(b_reports) == 1
    assert a_reports[0].id == r1.id
    assert b_reports[0].id == r2.id


# ---------------------------------------------------------------------------
# ReportFilter / ReportColumn validation
# ---------------------------------------------------------------------------


def test_invalid_filter_operator():
    with pytest.raises(ValueError, match="Invalid operator"):
        ReportFilter(field="x", operator="INVALID", value=1)


def test_invalid_column_aggregation():
    with pytest.raises(ValueError, match="Invalid aggregation"):
        ReportColumn(field="x", label="X", aggregation="INVALID")


# ---------------------------------------------------------------------------
# Generated reports listing
# ---------------------------------------------------------------------------


def test_get_generated_reports_limit(builder, sample_columns):
    config = builder.create_config(
        tenant_id="t1", name="Limit Test", type=ReportType.CUSTOM, columns=sample_columns
    )
    for _ in range(5):
        builder.generate_report(config.id)
    reports = builder.get_generated_reports("t1", limit=3)
    assert len(reports) == 3
