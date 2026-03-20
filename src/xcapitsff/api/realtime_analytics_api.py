"""API endpoints for Real-time Analytics — time series, funnels, and dashboards.

Provides HTTP access to the in-memory analytics engine for frontend dashboards
and event tracking.
"""

from datetime import datetime

from fastapi import APIRouter, Query

from xcapitsff.core.realtime_analytics import analytics_engine

router = APIRouter(prefix="/analytics/realtime", tags=["Real-time Analytics"])


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/realtime/timeseries
# ---------------------------------------------------------------------------


@router.get("/timeseries")
async def api_query_timeseries(
    tenant_id: str = Query(..., description="Tenant identifier"),
    metric_name: str = Query(..., description="Metric name to query"),
    start: datetime = Query(..., description="Start of time range (ISO 8601)"),
    end: datetime = Query(..., description="End of time range (ISO 8601)"),
    granularity: str = Query("hour", description="Granularity: minute, hour, day, week, month"),
):
    """Query time-series data for a metric, grouped by granularity bucket."""
    series = analytics_engine.query_timeseries(tenant_id, metric_name, start, end, granularity)
    return {
        "metric_name": series.metric_name,
        "aggregation": series.aggregation,
        "points": [
            {
                "timestamp": p.timestamp.isoformat(),
                "value": p.value,
                "label": p.label,
            }
            for p in series.points
        ],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/realtime/top
# ---------------------------------------------------------------------------


@router.get("/top")
async def api_query_top_n(
    tenant_id: str = Query(..., description="Tenant identifier"),
    metric_name: str = Query(..., description="Metric name to query"),
    dimension: str = Query(..., description="Dimension to rank by"),
    n: int = Query(10, ge=1, le=100, description="Number of top results"),
):
    """Query top N dimension values for a metric."""
    results = analytics_engine.query_top_n(tenant_id, metric_name, dimension, n)
    return {
        "metric_name": metric_name,
        "dimension": dimension,
        "results": [{"value": dim_val, "total": total} for dim_val, total in results],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/realtime/funnel
# ---------------------------------------------------------------------------


@router.get("/funnel")
async def api_query_funnel(
    tenant_id: str = Query(..., description="Tenant identifier"),
    steps: str = Query(..., description="Comma-separated metric names for funnel steps"),
    start: datetime = Query(..., description="Start of time range (ISO 8601)"),
    end: datetime = Query(..., description="End of time range (ISO 8601)"),
):
    """Funnel analysis across a sequence of metric steps."""
    step_list = [s.strip() for s in steps.split(",") if s.strip()]
    results = analytics_engine.query_funnel(tenant_id, step_list, start, end)
    return {
        "steps": [
            {"step": step_name, "count": count, "conversion_rate": rate}
            for step_name, count, rate in results
        ],
    }


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/realtime/dashboard-summary
# ---------------------------------------------------------------------------


@router.get("/dashboard-summary")
async def api_dashboard_summary(
    tenant_id: str = Query(..., description="Tenant identifier"),
):
    """Full dashboard summary with leads, tickets, conversion, and heatmap."""
    return analytics_engine.get_dashboard_summary(tenant_id)


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/realtime/compare
# ---------------------------------------------------------------------------


@router.get("/compare")
async def api_compare_periods(
    tenant_id: str = Query(..., description="Tenant identifier"),
    metric: str = Query(..., description="Metric name to compare"),
    period1_start: datetime = Query(..., description="Period 1 start (ISO 8601)"),
    period1_end: datetime = Query(..., description="Period 1 end (ISO 8601)"),
    period2_start: datetime = Query(..., description="Period 2 start (ISO 8601)"),
    period2_end: datetime = Query(..., description="Period 2 end (ISO 8601)"),
):
    """Compare a metric across two time periods (delta and pct_change)."""
    return analytics_engine.compare_periods(
        tenant_id, metric, period1_start, period1_end, period2_start, period2_end
    )


# ---------------------------------------------------------------------------
# POST /api/v1/analytics/realtime/track
# ---------------------------------------------------------------------------


@router.post("/track")
async def api_track_event(
    tenant_id: str = Query(..., description="Tenant identifier"),
    metric_name: str = Query(..., description="Metric name"),
    value: float = Query(1.0, description="Event value"),
    dimensions: str = Query("", description="Comma-separated key=value pairs for dimensions"),
):
    """Record a single analytics event (for frontend tracking)."""
    dim_dict: dict[str, str] = {}
    if dimensions:
        for pair in dimensions.split(","):
            pair = pair.strip()
            if "=" in pair:
                k, v = pair.split("=", 1)
                dim_dict[k.strip()] = v.strip()

    event = analytics_engine.record_event(
        tenant_id=tenant_id,
        metric_name=metric_name,
        value=value,
        dimensions=dim_dict if dim_dict else None,
    )
    return {
        "status": "recorded",
        "metric_name": event.metric_name,
        "value": event.value,
        "timestamp": event.timestamp.isoformat(),
    }
