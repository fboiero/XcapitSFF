"""Metrics collection system — counters, gauges, histograms, and timers.

Provides in-process metrics collection with Prometheus-compatible output.
Integrates with the event bus to auto-increment business metrics.
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    name: str
    type: MetricType
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


def _metric_key(name: str, labels: dict[str, str] | None = None) -> str:
    """Build a unique key from metric name + sorted label pairs."""
    if not labels:
        return name
    sorted_parts = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{name}{{{sorted_parts}}}"


class MetricsCollector:
    """In-process metrics collector supporting counters, gauges, histograms, and timers."""

    def __init__(self) -> None:
        self._metrics: dict[str, Metric] = {}
        self._histogram_observations: dict[str, list[float]] = {}

    # --- mutators ---

    def increment(self, name: str, amount: float = 1, labels: dict[str, str] | None = None) -> Metric:
        """Increment (or create) a counter metric."""
        key = _metric_key(name, labels)
        if key in self._metrics:
            self._metrics[key].value += amount
            self._metrics[key].timestamp = datetime.now()
        else:
            self._metrics[key] = Metric(
                name=name,
                type=MetricType.COUNTER,
                value=amount,
                labels=dict(labels) if labels else {},
            )
        return self._metrics[key]

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None) -> Metric:
        """Set a gauge to an absolute value."""
        key = _metric_key(name, labels)
        if key in self._metrics:
            self._metrics[key].value = value
            self._metrics[key].timestamp = datetime.now()
        else:
            self._metrics[key] = Metric(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                labels=dict(labels) if labels else {},
            )
        return self._metrics[key]

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None) -> Metric:
        """Record a histogram observation."""
        key = _metric_key(name, labels)
        if key not in self._histogram_observations:
            self._histogram_observations[key] = []
        self._histogram_observations[key].append(value)

        observations = self._histogram_observations[key]
        count = len(observations)
        total = sum(observations)

        if key in self._metrics:
            self._metrics[key].value = total
            self._metrics[key].timestamp = datetime.now()
        else:
            self._metrics[key] = Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                value=total,
                labels=dict(labels) if labels else {},
            )
        return self._metrics[key]

    @contextmanager
    def timer(self, name: str, labels: dict[str, str] | None = None):
        """Context manager that records elapsed wall-clock milliseconds as a histogram observation."""
        start = time.monotonic()
        try:
            yield
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            key = _metric_key(name, labels)
            if key not in self._histogram_observations:
                self._histogram_observations[key] = []
            self._histogram_observations[key].append(elapsed_ms)

            total = sum(self._histogram_observations[key])
            if key in self._metrics:
                self._metrics[key].value = total
                self._metrics[key].timestamp = datetime.now()
            else:
                self._metrics[key] = Metric(
                    name=name,
                    type=MetricType.TIMER,
                    value=total,
                    labels=dict(labels) if labels else {},
                )

    # --- queries ---

    def get_metric(self, name: str, labels: dict[str, str] | None = None) -> Metric | None:
        """Return a single metric by name and optional labels, or None."""
        key = _metric_key(name, labels)
        return self._metrics.get(key)

    def get_all_metrics(self) -> list[Metric]:
        """Return every recorded metric."""
        return list(self._metrics.values())

    def get_histogram_observations(self, name: str, labels: dict[str, str] | None = None) -> list[float]:
        """Return raw histogram/timer observations for a metric."""
        key = _metric_key(name, labels)
        return list(self._histogram_observations.get(key, []))

    def get_summary(self) -> dict[str, Any]:
        """Return a summary dict grouped by metric type."""
        counters: dict[str, Any] = {}
        gauges: dict[str, Any] = {}
        histograms: dict[str, Any] = {}
        timers: dict[str, Any] = {}

        for key, metric in self._metrics.items():
            entry: dict[str, Any] = {
                "value": metric.value,
                "labels": metric.labels,
                "timestamp": metric.timestamp.isoformat(),
            }
            if metric.type == MetricType.COUNTER:
                counters[key] = entry
            elif metric.type == MetricType.GAUGE:
                gauges[key] = entry
            elif metric.type in (MetricType.HISTOGRAM, MetricType.TIMER):
                obs = self._histogram_observations.get(key, [])
                entry["count"] = len(obs)
                entry["sum"] = sum(obs) if obs else 0
                entry["min"] = min(obs) if obs else 0
                entry["max"] = max(obs) if obs else 0
                entry["avg"] = entry["sum"] / entry["count"] if obs else 0
                if metric.type == MetricType.HISTOGRAM:
                    histograms[key] = entry
                else:
                    timers[key] = entry

        return {
            "total_metrics": len(self._metrics),
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
            "timers": timers,
        }

    def format_prometheus(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: list[str] = []
        seen_help: set[str] = set()

        for key, metric in sorted(self._metrics.items()):
            prom_name = metric.name.replace(".", "_")
            prom_type = metric.type.value
            if metric.type == MetricType.TIMER:
                prom_type = "histogram"

            if metric.name not in seen_help:
                lines.append(f"# HELP {prom_name} {prom_name}")
                lines.append(f"# TYPE {prom_name} {prom_type}")
                seen_help.add(metric.name)

            if metric.labels:
                label_str = ",".join(
                    f'{k}="{v}"' for k, v in sorted(metric.labels.items())
                )
                label_part = f"{{{label_str}}}"
            else:
                label_part = ""

            if metric.type in (MetricType.HISTOGRAM, MetricType.TIMER):
                obs = self._histogram_observations.get(key, [])
                count = len(obs)
                total = sum(obs) if obs else 0
                lines.append(f"{prom_name}_count{label_part} {count}")
                lines.append(f"{prom_name}_sum{label_part} {total}")
            else:
                lines.append(f"{prom_name}{label_part} {metric.value}")

        return "\n".join(lines) + "\n" if lines else ""

    def reset(self) -> None:
        """Clear all metrics and histogram observations."""
        self._metrics.clear()
        self._histogram_observations.clear()


# ---------------------------------------------------------------------------
# Singleton collector
# ---------------------------------------------------------------------------
metrics_collector = MetricsCollector()


# ---------------------------------------------------------------------------
# Pre-defined business metrics helpers
# ---------------------------------------------------------------------------

_PREDEFINED_COUNTERS = [
    "leads.created",
    "leads.qualified",
    "leads.imported",
    "tickets.created",
    "tickets.resolved",
    "tickets.sla_breached",
    "outreach.sent",
    "outreach.replied",
    "agents.tasks_completed",
    "agents.tasks_failed",
]


def _init_predefined_metrics(collector: MetricsCollector) -> None:
    """Ensure all pre-defined counters exist at zero."""
    for name in _PREDEFINED_COUNTERS:
        collector.increment(name, amount=0)


_init_predefined_metrics(metrics_collector)


# ---------------------------------------------------------------------------
# Event-bus integration
# ---------------------------------------------------------------------------

def setup_metrics_event_handlers(event_bus) -> None:  # noqa: ANN001
    """Subscribe to the event bus and auto-increment the matching business metrics.

    Call this once at application startup after both the event bus and the
    metrics collector are initialised.
    """
    from xcapitsff.core.events import EventType

    _EVENT_TO_METRIC: dict[EventType, str] = {
        EventType.LEAD_CREATED: "leads.created",
        EventType.LEAD_QUALIFIED: "leads.qualified",
        EventType.LEADS_IMPORTED: "leads.imported",
        EventType.TICKET_CREATED: "tickets.created",
        EventType.TICKET_RESOLVED: "tickets.resolved",
        EventType.TICKET_SLA_BREACHED: "tickets.sla_breached",
        EventType.OUTREACH_SENT: "outreach.sent",
        EventType.OUTREACH_REPLIED: "outreach.replied",
        EventType.AGENT_TASK_COMPLETED: "agents.tasks_completed",
        EventType.AGENT_TASK_FAILED: "agents.tasks_failed",
    }

    for event_type, metric_name in _EVENT_TO_METRIC.items():
        # Use a default-argument closure to capture *metric_name* at definition
        # time rather than at call time.
        async def _handler(event, _name: str = metric_name) -> None:
            metrics_collector.increment(_name)
            logger.debug("Metric %s incremented via event %s", _name, event.type.value)

        event_bus.subscribe(event_type, _handler)

    logger.info("Metrics event handlers registered (%d events)", len(_EVENT_TO_METRIC))
