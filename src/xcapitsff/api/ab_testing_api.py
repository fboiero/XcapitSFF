"""API endpoints for A/B Testing experiments."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.sales.ab_testing import (
    ABTestEngine,
    ExperimentMetric,
    ExperimentStatus,
    Variant,
    ab_test_engine,
)

router = APIRouter(prefix="/experiments", tags=["A/B Testing"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class VariantRequest(BaseModel):
    variant_id: str
    name: str
    content: dict = {}
    weight: float = 0.5


class ExperimentCreateRequest(BaseModel):
    name: str
    description: str = ""
    variants: list[VariantRequest]
    metric: str = "reply_rate"
    min_sample_size: int = 100


class TrackingRequest(BaseModel):
    variant_id: str


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _serialize_variant(v: Variant) -> dict:
    return {
        "variant_id": v.variant_id,
        "name": v.name,
        "content": v.content,
        "weight": round(v.weight, 4),
    }


def _serialize_experiment(e) -> dict:
    return {
        "experiment_id": e.experiment_id,
        "name": e.name,
        "description": e.description,
        "status": e.status.value,
        "metric": e.metric.value,
        "min_sample_size": e.min_sample_size,
        "variants": [_serialize_variant(v) for v in e.variants],
        "start_date": e.start_date.isoformat() if e.start_date else None,
        "end_date": e.end_date.isoformat() if e.end_date else None,
        "created_at": e.created_at.isoformat(),
    }


def _serialize_result(r) -> dict:
    return {
        "experiment_id": r.experiment_id,
        "variant_id": r.variant_id,
        "impressions": r.impressions,
        "conversions": r.conversions,
        "rate": round(r.rate, 6),
        "confidence_interval": {
            "lower": r.confidence_interval[0],
            "upper": r.confidence_interval[1],
        },
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
async def list_experiments():
    """List all experiments."""
    experiments = ab_test_engine.list_experiments()
    return {
        "count": len(experiments),
        "experiments": [_serialize_experiment(e) for e in experiments],
    }


@router.post("/", status_code=201)
async def create_experiment(req: ExperimentCreateRequest):
    """Create a new A/B testing experiment."""
    try:
        variants = [
            Variant(
                variant_id=v.variant_id,
                name=v.name,
                content=v.content,
                weight=v.weight,
            )
            for v in req.variants
        ]
        experiment = ab_test_engine.create_experiment(
            name=req.name,
            variants=variants,
            metric=req.metric,
            min_sample_size=req.min_sample_size,
            description=req.description,
        )
        return _serialize_experiment(experiment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{experiment_id}")
async def get_experiment(experiment_id: str):
    """Get experiment details."""
    experiment = ab_test_engine.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return _serialize_experiment(experiment)


@router.get("/{experiment_id}/results")
async def get_results(experiment_id: str):
    """Get experiment results with statistical analysis."""
    experiment = ab_test_engine.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    try:
        results = ab_test_engine.get_results(experiment_id)
        significant = ab_test_engine.is_significant(experiment_id)
        winner = ab_test_engine.get_winner(experiment_id)

        return {
            "experiment_id": experiment_id,
            "experiment_name": experiment.name,
            "status": experiment.status.value,
            "metric": experiment.metric.value,
            "is_significant": significant,
            "winner": _serialize_variant(winner) if winner else None,
            "results": [_serialize_result(r) for r in results],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{experiment_id}/assign/{lead_id}")
async def assign_variant(experiment_id: str, lead_id: str):
    """Assign a variant to a lead (deterministic based on lead_id hash)."""
    try:
        variant = ab_test_engine.assign_variant(experiment_id, lead_id)
        return {
            "experiment_id": experiment_id,
            "lead_id": lead_id,
            "variant": _serialize_variant(variant),
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{experiment_id}/impression")
async def record_impression(experiment_id: str, req: TrackingRequest):
    """Record an impression (lead saw / was sent this variant)."""
    try:
        ab_test_engine.record_impression(experiment_id, req.variant_id)
        return {"status": "recorded", "experiment_id": experiment_id, "variant_id": req.variant_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{experiment_id}/conversion")
async def record_conversion(experiment_id: str, req: TrackingRequest):
    """Record a conversion (lead replied, opened, converted)."""
    try:
        ab_test_engine.record_conversion(experiment_id, req.variant_id)
        return {"status": "recorded", "experiment_id": experiment_id, "variant_id": req.variant_id}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{experiment_id}/complete")
async def complete_experiment(experiment_id: str):
    """Complete an experiment."""
    try:
        experiment = ab_test_engine.complete_experiment(experiment_id)
        return _serialize_experiment(experiment)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
