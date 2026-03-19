"""Metrics API — expose collected metrics as JSON and Prometheus text format."""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from xcapitsff.core.metrics import metrics_collector

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("")
async def get_all_metrics():
    """Return all metrics as JSON."""
    return {
        "metrics": [
            {
                "name": m.name,
                "type": m.type.value,
                "value": m.value,
                "labels": m.labels,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in metrics_collector.get_all_metrics()
        ],
        "total": len(metrics_collector.get_all_metrics()),
    }


@router.get("/prometheus")
async def get_prometheus_metrics():
    """Return metrics in Prometheus text exposition format."""
    text = metrics_collector.format_prometheus()
    return PlainTextResponse(content=text, media_type="text/plain")


@router.get("/summary")
async def get_metrics_summary():
    """Return a summary view of all metrics grouped by type."""
    return metrics_collector.get_summary()
