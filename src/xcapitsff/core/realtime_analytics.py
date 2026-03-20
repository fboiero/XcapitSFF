"""Real-time analytics engine — time series, funnels, cohorts, and dashboards.

Provides in-memory event recording and querying for real-time dashboard metrics.
All data is stored per-tenant using defaultdict of lists for fast append/query.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pre-defined metric names
# ---------------------------------------------------------------------------

PREDEFINED_METRICS: list[str] = [
    "lead.created",
    "lead.qualified",
    "lead.converted",
    "ticket.created",
    "ticket.resolved",
    "outreach.sent",
    "outreach.opened",
    "outreach.replied",
    "meeting.booked",
    "revenue.won",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TimeSeriesPoint:
    """A single data point in a time series."""

    timestamp: datetime
    value: float
    label: str | None = None


@dataclass
class MetricSeries:
    """A named series of time-series points with an aggregation method."""

    metric_name: str
    points: list[TimeSeriesPoint] = field(default_factory=list)
    aggregation: str = "sum"  # sum, avg, count, max, min


# ---------------------------------------------------------------------------
# Internal event storage
# ---------------------------------------------------------------------------


@dataclass
class _RawEvent:
    """Internal representation of a recorded event."""

    tenant_id: str
    metric_name: str
    value: float
    timestamp: datetime
    dimensions: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Granularity helpers
# ---------------------------------------------------------------------------

_GRANULARITY_FORMATS: dict[str, str] = {
    "minute": "%Y-%m-%dT%H:%M",
    "hour": "%Y-%m-%dT%H",
    "day": "%Y-%m-%d",
    "week": "%Y-W%W",
    "month": "%Y-%m",
}


def _bucket_key(ts: datetime, granularity: str) -> str:
    """Return a string key that groups *ts* into the requested granularity bucket."""
    fmt = _GRANULARITY_FORMATS.get(granularity)
    if fmt is None:
        raise ValueError(f"Unknown granularity: {granularity}")
    return ts.strftime(fmt)


def _bucket_to_datetime(key: str, granularity: str) -> datetime:
    """Best-effort conversion of a bucket key back to a datetime."""
    fmt = _GRANULARITY_FORMATS[granularity]
    if granularity == "week":
        # ISO week format: parse manually
        year, week = key.split("-W")
        return datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
    return datetime.strptime(key, fmt)


# ---------------------------------------------------------------------------
# Analytics Engine
# ---------------------------------------------------------------------------


class AnalyticsEngine:
    """In-memory real-time analytics engine with multi-tenant isolation."""

    def __init__(self) -> None:
        # tenant_id -> metric_name -> list of _RawEvent
        self._store: dict[str, dict[str, list[_RawEvent]]] = defaultdict(
            lambda: defaultdict(list)
        )

    # --- recording ---

    def record_event(
        self,
        tenant_id: str,
        metric_name: str,
        value: float = 1.0,
        timestamp: datetime | None = None,
        dimensions: dict[str, str] | None = None,
    ) -> _RawEvent:
        """Record a single analytics event."""
        ts = timestamp or datetime.now()
        event = _RawEvent(
            tenant_id=tenant_id,
            metric_name=metric_name,
            value=value,
            timestamp=ts,
            dimensions=dict(dimensions) if dimensions else {},
        )
        self._store[tenant_id][metric_name].append(event)
        logger.debug("Recorded event: tenant=%s metric=%s value=%s", tenant_id, metric_name, value)
        return event

    # --- time-series queries ---

    def query_timeseries(
        self,
        tenant_id: str,
        metric_name: str,
        start: datetime,
        end: datetime,
        granularity: str = "hour",
    ) -> MetricSeries:
        """Query time-series data grouped by time bucket."""
        events = self._store[tenant_id][metric_name]

        # Filter by time range
        filtered = [e for e in events if start <= e.timestamp <= end]

        # Group by bucket
        buckets: dict[str, list[float]] = defaultdict(list)
        for e in filtered:
            key = _bucket_key(e.timestamp, granularity)
            buckets[key].append(e.value)

        # Build sorted points (sum aggregation by default)
        points: list[TimeSeriesPoint] = []
        for key in sorted(buckets.keys()):
            values = buckets[key]
            agg_value = sum(values)
            ts = _bucket_to_datetime(key, granularity)
            points.append(TimeSeriesPoint(timestamp=ts, value=agg_value, label=key))

        return MetricSeries(metric_name=metric_name, points=points, aggregation="sum")

    # --- top-N queries ---

    def query_top_n(
        self,
        tenant_id: str,
        metric_name: str,
        dimension: str,
        n: int = 10,
    ) -> list[tuple[str, float]]:
        """Return the top N dimension values by total value."""
        events = self._store[tenant_id][metric_name]

        totals: dict[str, float] = defaultdict(float)
        for e in events:
            dim_value = e.dimensions.get(dimension, "unknown")
            totals[dim_value] += e.value

        sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:n]

    # --- funnel analysis ---

    def query_funnel(
        self,
        tenant_id: str,
        steps: list[str],
        start: datetime,
        end: datetime,
    ) -> list[tuple[str, int, float]]:
        """Compute funnel conversion rates across a sequence of metric steps.

        Returns a list of (step_name, count, conversion_rate_from_previous).
        The first step always has a conversion rate of 100.0.
        """
        result: list[tuple[str, int, float]] = []
        prev_count: int | None = None

        for step in steps:
            events = self._store[tenant_id][step]
            count = len([e for e in events if start <= e.timestamp <= end])

            if prev_count is None or prev_count == 0:
                rate = 100.0
            else:
                rate = round((count / prev_count) * 100, 2)

            result.append((step, count, rate))
            prev_count = count

        return result

    # --- cohort analysis ---

    def query_cohort(
        self,
        tenant_id: str,
        cohort_metric: str,
        retention_metric: str,
        periods: int = 12,
    ) -> dict[str, Any]:
        """Compute cohort retention analysis.

        Groups users by the month they triggered *cohort_metric*,
        then measures how many triggered *retention_metric* in subsequent months.
        """
        cohort_events = self._store[tenant_id][cohort_metric]
        retention_events = self._store[tenant_id][retention_metric]

        # Build cohort membership: month -> set of dimension "user_id" values
        cohorts: dict[str, set[str]] = defaultdict(set)
        for e in cohort_events:
            month_key = e.timestamp.strftime("%Y-%m")
            user_id = e.dimensions.get("user_id", f"anon-{id(e)}")
            cohorts[month_key].add(user_id)

        # Build retention: user_id -> set of months with activity
        user_months: dict[str, set[str]] = defaultdict(set)
        for e in retention_events:
            user_id = e.dimensions.get("user_id", f"anon-{id(e)}")
            month_key = e.timestamp.strftime("%Y-%m")
            user_months[user_id].add(month_key)

        # Compute retention matrix
        sorted_cohort_months = sorted(cohorts.keys())[:periods]
        matrix: dict[str, list[float]] = {}

        for cohort_month in sorted_cohort_months:
            users = cohorts[cohort_month]
            total = len(users)
            if total == 0:
                matrix[cohort_month] = []
                continue

            retention_rates: list[float] = []
            all_months = sorted(
                set(m for ms in user_months.values() for m in ms) | set(sorted_cohort_months)
            )

            # Find index of cohort_month
            if cohort_month in all_months:
                start_idx = all_months.index(cohort_month)
            else:
                start_idx = 0

            for offset in range(min(periods, len(all_months) - start_idx)):
                target_month = all_months[start_idx + offset]
                retained = sum(1 for u in users if target_month in user_months.get(u, set()))
                retention_rates.append(round((retained / total) * 100, 2))

            matrix[cohort_month] = retention_rates

        return {
            "cohort_metric": cohort_metric,
            "retention_metric": retention_metric,
            "periods": periods,
            "matrix": matrix,
        }

    # --- dashboard summary ---

    def get_dashboard_summary(self, tenant_id: str) -> dict[str, Any]:
        """Return a complete dashboard summary for the given tenant."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        thirty_days_ago = now - timedelta(days=30)

        # Lead metrics
        lead_events = self._store[tenant_id]["lead.created"]
        leads_today = len([e for e in lead_events if e.timestamp >= today_start])
        leads_this_week = len([e for e in lead_events if e.timestamp >= week_start])
        leads_this_month = len([e for e in lead_events if e.timestamp >= month_start])

        # Ticket metrics
        ticket_created = self._store[tenant_id]["ticket.created"]
        ticket_resolved = self._store[tenant_id]["ticket.resolved"]
        tickets_today = len([e for e in ticket_created if e.timestamp >= today_start])
        tickets_open = len(ticket_created) - len(ticket_resolved)
        if tickets_open < 0:
            tickets_open = 0

        # Average resolution hours (from resolved ticket values, which store hours)
        resolved_values = [e.value for e in ticket_resolved]
        avg_resolution_hours = (
            round(sum(resolved_values) / len(resolved_values), 2)
            if resolved_values
            else 0.0
        )

        # Conversion rate (last 30 days)
        leads_30d = [e for e in lead_events if e.timestamp >= thirty_days_ago]
        converted_30d = [
            e
            for e in self._store[tenant_id]["lead.converted"]
            if e.timestamp >= thirty_days_ago
        ]
        conversion_rate_30d = (
            round((len(converted_30d) / len(leads_30d)) * 100, 2)
            if leads_30d
            else 0.0
        )

        # Revenue pipeline
        revenue_events = self._store[tenant_id]["revenue.won"]
        revenue_pipeline = sum(e.value for e in revenue_events)

        # Top sources (dimension "source")
        source_totals: dict[str, int] = defaultdict(int)
        for e in lead_events:
            source = e.dimensions.get("source", "direct")
            source_totals[source] += 1
        top_sources = sorted(source_totals.items(), key=lambda x: x[1], reverse=True)[:5]

        # Activity heatmap (24 hours x 7 days of week)
        heatmap: list[list[int]] = [[0] * 7 for _ in range(24)]
        all_events = []
        for metric_events in self._store[tenant_id].values():
            all_events.extend(metric_events)
        for e in all_events:
            hour = e.timestamp.hour
            dow = e.timestamp.weekday()  # 0=Monday, 6=Sunday
            heatmap[hour][dow] += 1

        return {
            "leads_today": leads_today,
            "leads_this_week": leads_this_week,
            "leads_this_month": leads_this_month,
            "tickets_today": tickets_today,
            "tickets_open": tickets_open,
            "avg_resolution_hours": avg_resolution_hours,
            "conversion_rate_30d": conversion_rate_30d,
            "revenue_pipeline": revenue_pipeline,
            "top_sources": top_sources,
            "activity_heatmap": heatmap,
        }

    # --- period comparison ---

    def compare_periods(
        self,
        tenant_id: str,
        metric: str,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
    ) -> dict[str, Any]:
        """Compare a metric across two time periods.

        Returns delta (absolute difference) and pct_change.
        """
        events = self._store[tenant_id][metric]

        p1_total = sum(e.value for e in events if period1_start <= e.timestamp <= period1_end)
        p2_total = sum(e.value for e in events if period2_start <= e.timestamp <= period2_end)

        delta = p2_total - p1_total

        if p1_total == 0:
            pct_change = 100.0 if p2_total > 0 else 0.0
        else:
            pct_change = round((delta / p1_total) * 100, 2)

        return {
            "metric": metric,
            "period1_total": p1_total,
            "period2_total": p2_total,
            "delta": delta,
            "pct_change": pct_change,
        }


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
analytics_engine = AnalyticsEngine()
