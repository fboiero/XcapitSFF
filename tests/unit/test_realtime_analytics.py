"""Tests for the real-time analytics engine."""

from datetime import datetime, timedelta

import pytest

from xcapitsff.core.realtime_analytics import (
    PREDEFINED_METRICS,
    AnalyticsEngine,
    MetricSeries,
    TimeSeriesPoint,
    _bucket_key,
)


@pytest.fixture
def engine():
    return AnalyticsEngine()


# ------------------------------------------------------------------
# 1. Record event
# ------------------------------------------------------------------


def test_record_event_basic(engine):
    event = engine.record_event("t1", "lead.created")
    assert event.tenant_id == "t1"
    assert event.metric_name == "lead.created"
    assert event.value == 1.0
    assert event.timestamp is not None


def test_record_event_with_value_and_dimensions(engine):
    event = engine.record_event(
        "t1", "revenue.won", value=5000.0, dimensions={"source": "organic"}
    )
    assert event.value == 5000.0
    assert event.dimensions == {"source": "organic"}


def test_record_event_custom_timestamp(engine):
    ts = datetime(2025, 6, 15, 10, 30, 0)
    event = engine.record_event("t1", "lead.created", timestamp=ts)
    assert event.timestamp == ts


# ------------------------------------------------------------------
# 2. Query timeseries — hourly granularity
# ------------------------------------------------------------------


def test_query_timeseries_hourly(engine):
    base = datetime(2025, 3, 1, 10, 0, 0)
    for i in range(5):
        engine.record_event("t1", "lead.created", timestamp=base + timedelta(minutes=i * 10))
    # All 5 events fall in the same hour bucket
    series = engine.query_timeseries("t1", "lead.created", base, base + timedelta(hours=1))
    assert isinstance(series, MetricSeries)
    assert len(series.points) == 1
    assert series.points[0].value == 5.0


# ------------------------------------------------------------------
# 3. Query timeseries — daily granularity
# ------------------------------------------------------------------


def test_query_timeseries_daily(engine):
    for day in range(3):
        ts = datetime(2025, 3, 1 + day, 12, 0, 0)
        engine.record_event("t1", "lead.created", timestamp=ts)

    series = engine.query_timeseries(
        "t1", "lead.created",
        datetime(2025, 3, 1), datetime(2025, 3, 3, 23, 59, 59),
        granularity="day",
    )
    assert len(series.points) == 3
    assert all(p.value == 1.0 for p in series.points)


# ------------------------------------------------------------------
# 4. Query timeseries — empty range
# ------------------------------------------------------------------


def test_query_timeseries_empty_range(engine):
    engine.record_event("t1", "lead.created", timestamp=datetime(2025, 1, 1, 10, 0))
    series = engine.query_timeseries(
        "t1", "lead.created",
        datetime(2025, 6, 1), datetime(2025, 6, 30),
    )
    assert len(series.points) == 0


# ------------------------------------------------------------------
# 5. Query timeseries — minute granularity
# ------------------------------------------------------------------


def test_query_timeseries_minute_granularity(engine):
    base = datetime(2025, 3, 1, 10, 0, 0)
    engine.record_event("t1", "ticket.created", timestamp=base)
    engine.record_event("t1", "ticket.created", timestamp=base + timedelta(minutes=1))
    engine.record_event("t1", "ticket.created", timestamp=base + timedelta(minutes=1, seconds=30))

    series = engine.query_timeseries(
        "t1", "ticket.created",
        base, base + timedelta(minutes=5),
        granularity="minute",
    )
    assert len(series.points) == 2
    # First minute has 1 event, second has 2
    assert series.points[0].value == 1.0
    assert series.points[1].value == 2.0


# ------------------------------------------------------------------
# 6. Top N by dimension
# ------------------------------------------------------------------


def test_query_top_n(engine):
    engine.record_event("t1", "lead.created", dimensions={"source": "google"})
    engine.record_event("t1", "lead.created", dimensions={"source": "google"})
    engine.record_event("t1", "lead.created", dimensions={"source": "linkedin"})
    engine.record_event("t1", "lead.created", dimensions={"source": "referral"})
    engine.record_event("t1", "lead.created", dimensions={"source": "referral"})
    engine.record_event("t1", "lead.created", dimensions={"source": "referral"})

    results = engine.query_top_n("t1", "lead.created", "source", n=2)
    assert len(results) == 2
    assert results[0][0] == "referral"
    assert results[0][1] == 3.0
    assert results[1][0] == "google"
    assert results[1][1] == 2.0


def test_query_top_n_missing_dimension(engine):
    engine.record_event("t1", "lead.created")
    engine.record_event("t1", "lead.created", dimensions={"source": "organic"})

    results = engine.query_top_n("t1", "lead.created", "source")
    # One event has no source → "unknown", one has "organic"
    dim_values = {r[0] for r in results}
    assert "unknown" in dim_values
    assert "organic" in dim_values


# ------------------------------------------------------------------
# 7. Funnel conversion rates
# ------------------------------------------------------------------


def test_query_funnel(engine):
    start = datetime(2025, 3, 1)
    end = datetime(2025, 3, 31, 23, 59, 59)

    for i in range(100):
        engine.record_event("t1", "lead.created", timestamp=datetime(2025, 3, 5))
    for i in range(40):
        engine.record_event("t1", "lead.qualified", timestamp=datetime(2025, 3, 10))
    for i in range(10):
        engine.record_event("t1", "lead.converted", timestamp=datetime(2025, 3, 20))

    funnel = engine.query_funnel(
        "t1",
        ["lead.created", "lead.qualified", "lead.converted"],
        start, end,
    )
    assert len(funnel) == 3
    assert funnel[0] == ("lead.created", 100, 100.0)
    assert funnel[1] == ("lead.qualified", 40, 40.0)
    assert funnel[2] == ("lead.converted", 10, 25.0)


def test_query_funnel_empty(engine):
    start = datetime(2025, 3, 1)
    end = datetime(2025, 3, 31)
    funnel = engine.query_funnel("t1", ["lead.created", "lead.qualified"], start, end)
    assert funnel[0] == ("lead.created", 0, 100.0)
    assert funnel[1] == ("lead.qualified", 0, 100.0)  # 0/0 → 100%


# ------------------------------------------------------------------
# 8. Dashboard summary
# ------------------------------------------------------------------


def test_dashboard_summary(engine):
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Create some lead events today
    for _ in range(3):
        engine.record_event("t1", "lead.created", timestamp=today_start + timedelta(hours=1))

    # Create ticket events
    engine.record_event("t1", "ticket.created", timestamp=today_start + timedelta(hours=2))
    engine.record_event("t1", "ticket.resolved", value=4.5, timestamp=today_start + timedelta(hours=3))

    summary = engine.get_dashboard_summary("t1")

    assert summary["leads_today"] == 3
    assert summary["leads_this_week"] >= 3
    assert summary["leads_this_month"] >= 3
    assert summary["tickets_today"] == 1
    assert summary["tickets_open"] == 0  # 1 created, 1 resolved
    assert summary["avg_resolution_hours"] == 4.5
    assert isinstance(summary["top_sources"], list)
    assert isinstance(summary["activity_heatmap"], list)


# ------------------------------------------------------------------
# 9. Period comparison — positive growth
# ------------------------------------------------------------------


def test_compare_periods_positive_growth(engine):
    # Period 1: 10 leads
    for i in range(10):
        engine.record_event("t1", "lead.created", timestamp=datetime(2025, 1, 15))
    # Period 2: 15 leads
    for i in range(15):
        engine.record_event("t1", "lead.created", timestamp=datetime(2025, 2, 15))

    result = engine.compare_periods(
        "t1", "lead.created",
        datetime(2025, 1, 1), datetime(2025, 1, 31),
        datetime(2025, 2, 1), datetime(2025, 2, 28),
    )
    assert result["period1_total"] == 10.0
    assert result["period2_total"] == 15.0
    assert result["delta"] == 5.0
    assert result["pct_change"] == 50.0


# ------------------------------------------------------------------
# 10. Period comparison — negative growth
# ------------------------------------------------------------------


def test_compare_periods_negative_growth(engine):
    for i in range(20):
        engine.record_event("t1", "ticket.created", timestamp=datetime(2025, 1, 10))
    for i in range(10):
        engine.record_event("t1", "ticket.created", timestamp=datetime(2025, 2, 10))

    result = engine.compare_periods(
        "t1", "ticket.created",
        datetime(2025, 1, 1), datetime(2025, 1, 31),
        datetime(2025, 2, 1), datetime(2025, 2, 28),
    )
    assert result["delta"] == -10.0
    assert result["pct_change"] == -50.0


# ------------------------------------------------------------------
# 11. Period comparison — zero baseline
# ------------------------------------------------------------------


def test_compare_periods_zero_baseline(engine):
    engine.record_event("t1", "lead.created", timestamp=datetime(2025, 2, 10))

    result = engine.compare_periods(
        "t1", "lead.created",
        datetime(2025, 1, 1), datetime(2025, 1, 31),
        datetime(2025, 2, 1), datetime(2025, 2, 28),
    )
    assert result["period1_total"] == 0.0
    assert result["pct_change"] == 100.0


# ------------------------------------------------------------------
# 12. Activity heatmap structure (24x7)
# ------------------------------------------------------------------


def test_activity_heatmap_structure(engine):
    # Record some events at known hours/days
    monday_10am = datetime(2025, 3, 3, 10, 0, 0)  # Monday
    engine.record_event("t1", "lead.created", timestamp=monday_10am)

    summary = engine.get_dashboard_summary("t1")
    heatmap = summary["activity_heatmap"]

    # 24 rows (hours), 7 cols (days of week)
    assert len(heatmap) == 24
    for row in heatmap:
        assert len(row) == 7

    # Monday (weekday=0) at hour 10 should have a count
    assert heatmap[10][0] >= 1


# ------------------------------------------------------------------
# 13. Multiple tenants isolated
# ------------------------------------------------------------------


def test_multiple_tenants_isolated(engine):
    engine.record_event("tenant_a", "lead.created")
    engine.record_event("tenant_a", "lead.created")
    engine.record_event("tenant_b", "lead.created")

    summary_a = engine.get_dashboard_summary("tenant_a")
    summary_b = engine.get_dashboard_summary("tenant_b")

    # Tenant A has more leads than Tenant B
    # (exact counts depend on timing but the stores must be separate)
    now = datetime.now()
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)

    ts_a = engine.query_timeseries("tenant_a", "lead.created", start, end, "day")
    ts_b = engine.query_timeseries("tenant_b", "lead.created", start, end, "day")

    total_a = sum(p.value for p in ts_a.points)
    total_b = sum(p.value for p in ts_b.points)
    assert total_a == 2.0
    assert total_b == 1.0


# ------------------------------------------------------------------
# 14. Pre-defined metrics list
# ------------------------------------------------------------------


def test_predefined_metrics_list():
    assert "lead.created" in PREDEFINED_METRICS
    assert "lead.qualified" in PREDEFINED_METRICS
    assert "lead.converted" in PREDEFINED_METRICS
    assert "ticket.created" in PREDEFINED_METRICS
    assert "ticket.resolved" in PREDEFINED_METRICS
    assert "outreach.sent" in PREDEFINED_METRICS
    assert "outreach.opened" in PREDEFINED_METRICS
    assert "outreach.replied" in PREDEFINED_METRICS
    assert "meeting.booked" in PREDEFINED_METRICS
    assert "revenue.won" in PREDEFINED_METRICS
    assert len(PREDEFINED_METRICS) == 10


# ------------------------------------------------------------------
# 15. TimeSeriesPoint dataclass
# ------------------------------------------------------------------


def test_time_series_point_dataclass():
    ts = datetime(2025, 3, 1, 10, 0)
    point = TimeSeriesPoint(timestamp=ts, value=42.0, label="test")
    assert point.timestamp == ts
    assert point.value == 42.0
    assert point.label == "test"


def test_time_series_point_optional_label():
    point = TimeSeriesPoint(timestamp=datetime.now(), value=1.0)
    assert point.label is None


# ------------------------------------------------------------------
# 16. MetricSeries dataclass
# ------------------------------------------------------------------


def test_metric_series_dataclass():
    series = MetricSeries(metric_name="lead.created")
    assert series.metric_name == "lead.created"
    assert series.points == []
    assert series.aggregation == "sum"


def test_metric_series_custom_aggregation():
    series = MetricSeries(metric_name="revenue.won", aggregation="avg")
    assert series.aggregation == "avg"


# ------------------------------------------------------------------
# 17. Bucket key helper
# ------------------------------------------------------------------


def test_bucket_key_hour():
    ts = datetime(2025, 3, 15, 14, 30, 0)
    assert _bucket_key(ts, "hour") == "2025-03-15T14"


def test_bucket_key_day():
    ts = datetime(2025, 3, 15, 14, 30, 0)
    assert _bucket_key(ts, "day") == "2025-03-15"


def test_bucket_key_month():
    ts = datetime(2025, 3, 15, 14, 30, 0)
    assert _bucket_key(ts, "month") == "2025-03"


def test_bucket_key_invalid_granularity():
    with pytest.raises(ValueError, match="Unknown granularity"):
        _bucket_key(datetime.now(), "century")


# ------------------------------------------------------------------
# 18. Query timeseries with value aggregation
# ------------------------------------------------------------------


def test_query_timeseries_value_aggregation(engine):
    ts = datetime(2025, 3, 1, 10, 0, 0)
    engine.record_event("t1", "revenue.won", value=1000.0, timestamp=ts)
    engine.record_event("t1", "revenue.won", value=2500.0, timestamp=ts + timedelta(minutes=15))
    engine.record_event("t1", "revenue.won", value=500.0, timestamp=ts + timedelta(minutes=30))

    series = engine.query_timeseries(
        "t1", "revenue.won", ts, ts + timedelta(hours=1), granularity="hour"
    )
    assert len(series.points) == 1
    assert series.points[0].value == 4000.0


# ------------------------------------------------------------------
# 19. Cohort query
# ------------------------------------------------------------------


def test_query_cohort(engine):
    # Cohort: users signing up in Jan
    engine.record_event(
        "t1", "lead.created",
        timestamp=datetime(2025, 1, 5),
        dimensions={"user_id": "u1"},
    )
    engine.record_event(
        "t1", "lead.created",
        timestamp=datetime(2025, 1, 10),
        dimensions={"user_id": "u2"},
    )
    # Retention: u1 active in Jan and Feb, u2 only Jan
    engine.record_event(
        "t1", "outreach.sent",
        timestamp=datetime(2025, 1, 15),
        dimensions={"user_id": "u1"},
    )
    engine.record_event(
        "t1", "outreach.sent",
        timestamp=datetime(2025, 2, 10),
        dimensions={"user_id": "u1"},
    )
    engine.record_event(
        "t1", "outreach.sent",
        timestamp=datetime(2025, 1, 20),
        dimensions={"user_id": "u2"},
    )

    result = engine.query_cohort("t1", "lead.created", "outreach.sent", periods=3)
    assert result["cohort_metric"] == "lead.created"
    assert result["retention_metric"] == "outreach.sent"
    assert "2025-01" in result["matrix"]
    # Both users active in Jan (100%), only u1 in Feb (50%)
    rates = result["matrix"]["2025-01"]
    assert len(rates) >= 2
    assert rates[0] == 100.0  # Jan retention
    assert rates[1] == 50.0   # Feb retention


# ------------------------------------------------------------------
# 20. Dashboard summary — conversion rate calculation
# ------------------------------------------------------------------


def test_dashboard_summary_conversion_rate(engine):
    now = datetime.now()
    recent = now - timedelta(days=5)

    for _ in range(20):
        engine.record_event("t1", "lead.created", timestamp=recent)
    for _ in range(5):
        engine.record_event("t1", "lead.converted", timestamp=recent)

    summary = engine.get_dashboard_summary("t1")
    assert summary["conversion_rate_30d"] == 25.0


# ------------------------------------------------------------------
# 21. Dashboard summary — revenue pipeline
# ------------------------------------------------------------------


def test_dashboard_summary_revenue_pipeline(engine):
    engine.record_event("t1", "revenue.won", value=10000.0)
    engine.record_event("t1", "revenue.won", value=5000.0)

    summary = engine.get_dashboard_summary("t1")
    assert summary["revenue_pipeline"] == 15000.0


# ------------------------------------------------------------------
# 22. Dashboard summary — empty tenant
# ------------------------------------------------------------------


def test_dashboard_summary_empty_tenant(engine):
    summary = engine.get_dashboard_summary("empty_tenant")
    assert summary["leads_today"] == 0
    assert summary["tickets_open"] == 0
    assert summary["avg_resolution_hours"] == 0.0
    assert summary["conversion_rate_30d"] == 0.0
    assert summary["revenue_pipeline"] == 0.0
    assert summary["top_sources"] == []
    assert len(summary["activity_heatmap"]) == 24


# ------------------------------------------------------------------
# 23. Timeseries — monthly granularity
# ------------------------------------------------------------------


def test_query_timeseries_monthly(engine):
    engine.record_event("t1", "lead.created", timestamp=datetime(2025, 1, 15))
    engine.record_event("t1", "lead.created", timestamp=datetime(2025, 2, 10))
    engine.record_event("t1", "lead.created", timestamp=datetime(2025, 2, 20))

    series = engine.query_timeseries(
        "t1", "lead.created",
        datetime(2025, 1, 1), datetime(2025, 3, 1),
        granularity="month",
    )
    assert len(series.points) == 2
    assert series.points[0].value == 1.0  # Jan
    assert series.points[1].value == 2.0  # Feb
