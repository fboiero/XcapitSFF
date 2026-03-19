"""Tests for the metrics collection system."""

import time

import pytest

from xcapitsff.core.events import Event, EventBus, EventType
from xcapitsff.core.metrics import (
    Metric,
    MetricType,
    MetricsCollector,
    _metric_key,
    metrics_collector,
    setup_metrics_event_handlers,
)


@pytest.fixture
def collector():
    c = MetricsCollector()
    return c


# ------------------------------------------------------------------
# 1. Counter increment
# ------------------------------------------------------------------

def test_counter_increment(collector):
    collector.increment("leads.created")
    m = collector.get_metric("leads.created")
    assert m is not None
    assert m.type == MetricType.COUNTER
    assert m.value == 1


def test_counter_increment_by_amount(collector):
    collector.increment("leads.imported", amount=5)
    collector.increment("leads.imported", amount=3)
    m = collector.get_metric("leads.imported")
    assert m.value == 8


# ------------------------------------------------------------------
# 2. Gauge set
# ------------------------------------------------------------------

def test_gauge_set(collector):
    collector.gauge("cpu_usage", 45.5)
    m = collector.get_metric("cpu_usage")
    assert m is not None
    assert m.type == MetricType.GAUGE
    assert m.value == 45.5


def test_gauge_overwrite(collector):
    collector.gauge("memory", 100)
    collector.gauge("memory", 200)
    m = collector.get_metric("memory")
    assert m.value == 200


# ------------------------------------------------------------------
# 3. Histogram observe
# ------------------------------------------------------------------

def test_histogram_observe(collector):
    collector.histogram("api.latency_ms", 12.5)
    collector.histogram("api.latency_ms", 25.0)
    obs = collector.get_histogram_observations("api.latency_ms")
    assert obs == [12.5, 25.0]
    m = collector.get_metric("api.latency_ms")
    assert m.type == MetricType.HISTOGRAM
    assert m.value == pytest.approx(37.5)


# ------------------------------------------------------------------
# 4. Timer context manager
# ------------------------------------------------------------------

def test_timer_context_manager(collector):
    with collector.timer("request.duration"):
        time.sleep(0.01)  # ~10 ms
    m = collector.get_metric("request.duration")
    assert m is not None
    assert m.type == MetricType.TIMER
    assert m.value > 0
    obs = collector.get_histogram_observations("request.duration")
    assert len(obs) == 1
    assert obs[0] >= 5  # at least 5 ms


def test_timer_multiple_invocations(collector):
    for _ in range(3):
        with collector.timer("multi.timer"):
            time.sleep(0.005)
    obs = collector.get_histogram_observations("multi.timer")
    assert len(obs) == 3


# ------------------------------------------------------------------
# 5. Labels filtering
# ------------------------------------------------------------------

def test_counter_with_labels(collector):
    collector.increment("api.requests", labels={"method": "GET", "path": "/leads", "status": "200"})
    collector.increment("api.requests", labels={"method": "POST", "path": "/leads", "status": "201"})
    collector.increment("api.requests", labels={"method": "GET", "path": "/leads", "status": "200"})

    m_get = collector.get_metric("api.requests", labels={"method": "GET", "path": "/leads", "status": "200"})
    m_post = collector.get_metric("api.requests", labels={"method": "POST", "path": "/leads", "status": "201"})
    assert m_get.value == 2
    assert m_post.value == 1


def test_labels_do_not_collide(collector):
    collector.gauge("connections", 10, labels={"db": "primary"})
    collector.gauge("connections", 3, labels={"db": "replica"})
    assert collector.get_metric("connections", labels={"db": "primary"}).value == 10
    assert collector.get_metric("connections", labels={"db": "replica"}).value == 3


# ------------------------------------------------------------------
# 6. get_all_metrics
# ------------------------------------------------------------------

def test_get_all_metrics(collector):
    collector.increment("a")
    collector.gauge("b", 1)
    collector.histogram("c", 5)
    all_m = collector.get_all_metrics()
    names = {m.name for m in all_m}
    assert names == {"a", "b", "c"}


# ------------------------------------------------------------------
# 7. get_summary
# ------------------------------------------------------------------

def test_get_summary_structure(collector):
    collector.increment("leads.created")
    collector.gauge("cpu", 50)
    collector.histogram("latency", 10)
    with collector.timer("dur"):
        pass

    summary = collector.get_summary()
    assert summary["total_metrics"] == 4
    assert "leads.created" in summary["counters"]
    assert "cpu" in summary["gauges"]
    assert "latency" in summary["histograms"]
    assert "dur" in summary["timers"]


def test_summary_histogram_stats(collector):
    collector.histogram("lat", 10)
    collector.histogram("lat", 20)
    collector.histogram("lat", 30)
    summary = collector.get_summary()
    h = summary["histograms"]["lat"]
    assert h["count"] == 3
    assert h["sum"] == pytest.approx(60)
    assert h["min"] == pytest.approx(10)
    assert h["max"] == pytest.approx(30)
    assert h["avg"] == pytest.approx(20)


# ------------------------------------------------------------------
# 8. Prometheus format output
# ------------------------------------------------------------------

def test_prometheus_format_counter(collector):
    collector.increment("leads.created", amount=5)
    text = collector.format_prometheus()
    assert "# HELP leads_created" in text
    assert "# TYPE leads_created counter" in text
    assert "leads_created 5" in text


def test_prometheus_format_with_labels(collector):
    collector.increment("api.requests", labels={"method": "GET", "status": "200"})
    text = collector.format_prometheus()
    assert 'api_requests{method="GET",status="200"} 1' in text


def test_prometheus_format_histogram(collector):
    collector.histogram("api.latency_ms", 15)
    collector.histogram("api.latency_ms", 25)
    text = collector.format_prometheus()
    assert "api_latency_ms_count 2" in text
    assert "api_latency_ms_sum 40" in text


# ------------------------------------------------------------------
# 9. Reset
# ------------------------------------------------------------------

def test_reset(collector):
    collector.increment("a")
    collector.gauge("b", 1)
    collector.histogram("c", 5)
    collector.reset()
    assert collector.get_all_metrics() == []
    assert collector.get_histogram_observations("c") == []


# ------------------------------------------------------------------
# 10. Metric key helper
# ------------------------------------------------------------------

def test_metric_key_without_labels():
    assert _metric_key("foo") == "foo"


def test_metric_key_with_labels():
    key = _metric_key("req", {"b": "2", "a": "1"})
    assert key == "req{a=1,b=2}"


# ------------------------------------------------------------------
# 11. get_metric returns None for unknown
# ------------------------------------------------------------------

def test_get_metric_unknown(collector):
    assert collector.get_metric("nonexistent") is None


# ------------------------------------------------------------------
# 12. Predefined metrics exist on the singleton
# ------------------------------------------------------------------

def test_predefined_metrics_exist():
    names = {m.name for m in metrics_collector.get_all_metrics()}
    for expected in [
        "leads.created", "leads.qualified", "leads.imported",
        "tickets.created", "tickets.resolved", "tickets.sla_breached",
        "outreach.sent", "outreach.replied",
        "agents.tasks_completed", "agents.tasks_failed",
    ]:
        assert expected in names, f"{expected} not found in predefined metrics"


# ------------------------------------------------------------------
# 13. Event-bus integration
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_event_handler_increments_counter():
    collector = MetricsCollector()
    # Monkey-patch the module-level collector used by the handler
    import xcapitsff.core.metrics as metrics_mod
    original = metrics_mod.metrics_collector
    metrics_mod.metrics_collector = collector

    bus = EventBus()
    setup_metrics_event_handlers(bus)

    # Pre-init so we can track the delta
    collector.increment("leads.created", amount=0)
    await bus.emit(Event(type=EventType.LEAD_CREATED, data={"id": 1}))

    m = collector.get_metric("leads.created")
    assert m is not None
    assert m.value == 1

    metrics_mod.metrics_collector = original


@pytest.mark.asyncio
async def test_event_handler_multiple_events():
    collector = MetricsCollector()
    import xcapitsff.core.metrics as metrics_mod
    original = metrics_mod.metrics_collector
    metrics_mod.metrics_collector = collector

    bus = EventBus()
    setup_metrics_event_handlers(bus)

    collector.increment("tickets.created", amount=0)
    collector.increment("tickets.resolved", amount=0)

    await bus.emit(Event(type=EventType.TICKET_CREATED, data={}))
    await bus.emit(Event(type=EventType.TICKET_CREATED, data={}))
    await bus.emit(Event(type=EventType.TICKET_RESOLVED, data={}))

    assert collector.get_metric("tickets.created").value == 2
    assert collector.get_metric("tickets.resolved").value == 1

    metrics_mod.metrics_collector = original


# ------------------------------------------------------------------
# 14. Metric dataclass fields
# ------------------------------------------------------------------

def test_metric_dataclass():
    m = Metric(name="test", type=MetricType.COUNTER, value=42, labels={"env": "prod"})
    assert m.name == "test"
    assert m.type == MetricType.COUNTER
    assert m.value == 42
    assert m.labels == {"env": "prod"}
    assert m.timestamp is not None


# ------------------------------------------------------------------
# 15. Prometheus format empty
# ------------------------------------------------------------------

def test_prometheus_format_empty(collector):
    text = collector.format_prometheus()
    assert text == ""
