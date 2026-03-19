"""Tests for A/B Testing Engine."""

import math

import pytest

from xcapitsff.sales.ab_testing import (
    ABTestEngine,
    Experiment,
    ExperimentMetric,
    ExperimentResult,
    ExperimentStatus,
    Variant,
    create_default_experiments,
    wilson_confidence_interval,
    z_test_proportions,
)


@pytest.fixture
def engine():
    return ABTestEngine()


@pytest.fixture
def simple_experiment(engine):
    """Create a basic two-variant experiment."""
    return engine.create_experiment(
        name="test_experiment",
        variants=[
            Variant(variant_id="A", name="control", content={"msg": "Hello"}, weight=0.5),
            Variant(variant_id="B", name="treatment", content={"msg": "Hi there"}, weight=0.5),
        ],
        metric=ExperimentMetric.REPLY_RATE,
        min_sample_size=50,
    )


# ---------------------------------------------------------------------------
# Experiment creation
# ---------------------------------------------------------------------------

def test_create_experiment(engine):
    exp = engine.create_experiment(
        name="subject_line_test",
        variants=[
            Variant(variant_id="A", name="direct", weight=0.5),
            Variant(variant_id="B", name="question", weight=0.5),
        ],
        metric="reply_rate",
        min_sample_size=100,
        description="Test direct vs question subjects",
    )
    assert exp.experiment_id.startswith("EXP-")
    assert exp.name == "subject_line_test"
    assert exp.status == ExperimentStatus.RUNNING
    assert exp.metric == ExperimentMetric.REPLY_RATE
    assert len(exp.variants) == 2
    assert exp.min_sample_size == 100


def test_create_experiment_requires_two_variants(engine):
    with pytest.raises(ValueError, match="at least 2 variants"):
        engine.create_experiment(
            name="bad",
            variants=[Variant(variant_id="A", name="only_one")],
        )


def test_create_experiment_with_valid_weights(engine):
    exp = engine.create_experiment(
        name="weighted",
        variants=[
            Variant(variant_id="A", name="a", weight=0.3),
            Variant(variant_id="B", name="b", weight=0.7),
        ],
    )
    assert math.isclose(exp.variants[0].weight, 0.3, rel_tol=1e-6)
    assert math.isclose(exp.variants[1].weight, 0.7, rel_tol=1e-6)
    assert math.isclose(sum(v.weight for v in exp.variants), 1.0, rel_tol=1e-6)


def test_variant_weight_validation():
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        Variant(variant_id="X", name="bad", weight=1.5)


# ---------------------------------------------------------------------------
# Variant assignment
# ---------------------------------------------------------------------------

def test_deterministic_assignment(engine, simple_experiment):
    """Same lead always gets the same variant."""
    v1 = engine.assign_variant(simple_experiment.experiment_id, "lead-001")
    v2 = engine.assign_variant(simple_experiment.experiment_id, "lead-001")
    assert v1.variant_id == v2.variant_id


def test_different_leads_may_get_different_variants(engine, simple_experiment):
    """With enough leads and 50/50 weights, both variants should appear."""
    variants_seen = set()
    for i in range(100):
        v = engine.assign_variant(simple_experiment.experiment_id, f"lead-{i:04d}")
        variants_seen.add(v.variant_id)
    assert len(variants_seen) == 2, "Expected both variants to be assigned across 100 leads"


def test_assignment_respects_weights(engine):
    """Heavily skewed weights should produce mostly the heavy variant."""
    exp = engine.create_experiment(
        name="skewed",
        variants=[
            Variant(variant_id="A", name="heavy", weight=0.95),
            Variant(variant_id="B", name="light", weight=0.05),
        ],
        min_sample_size=10,
    )
    counts = {"A": 0, "B": 0}
    for i in range(500):
        v = engine.assign_variant(exp.experiment_id, f"lead-{i}")
        counts[v.variant_id] += 1

    # With 95/5 split over 500 leads, A should dominate
    assert counts["A"] > counts["B"] * 3


def test_assign_variant_unknown_experiment(engine):
    with pytest.raises(ValueError, match="not found"):
        engine.assign_variant("EXP-9999", "lead-001")


# ---------------------------------------------------------------------------
# Impression & conversion tracking
# ---------------------------------------------------------------------------

def test_record_impressions(engine, simple_experiment):
    eid = simple_experiment.experiment_id
    engine.record_impression(eid, "A")
    engine.record_impression(eid, "A")
    engine.record_impression(eid, "B")

    results = engine.get_results(eid)
    a_result = next(r for r in results if r.variant_id == "A")
    b_result = next(r for r in results if r.variant_id == "B")
    assert a_result.impressions == 2
    assert b_result.impressions == 1


def test_record_conversions(engine, simple_experiment):
    eid = simple_experiment.experiment_id
    engine.record_impression(eid, "A")
    engine.record_conversion(eid, "A")

    results = engine.get_results(eid)
    a_result = next(r for r in results if r.variant_id == "A")
    assert a_result.conversions == 1
    assert a_result.rate == 1.0


def test_record_impression_unknown_variant(engine, simple_experiment):
    with pytest.raises(ValueError, match="Variant"):
        engine.record_impression(simple_experiment.experiment_id, "Z")


def test_record_conversion_unknown_experiment(engine):
    with pytest.raises(ValueError, match="Experiment"):
        engine.record_conversion("EXP-9999", "A")


# ---------------------------------------------------------------------------
# Results calculation
# ---------------------------------------------------------------------------

def test_results_calculation(engine, simple_experiment):
    eid = simple_experiment.experiment_id
    # Variant A: 100 impressions, 20 conversions (20%)
    for _ in range(100):
        engine.record_impression(eid, "A")
    for _ in range(20):
        engine.record_conversion(eid, "A")

    # Variant B: 100 impressions, 10 conversions (10%)
    for _ in range(100):
        engine.record_impression(eid, "B")
    for _ in range(10):
        engine.record_conversion(eid, "B")

    results = engine.get_results(eid)
    a_result = next(r for r in results if r.variant_id == "A")
    b_result = next(r for r in results if r.variant_id == "B")

    assert math.isclose(a_result.rate, 0.20, rel_tol=1e-4)
    assert math.isclose(b_result.rate, 0.10, rel_tol=1e-4)


def test_results_zero_impressions(engine, simple_experiment):
    results = engine.get_results(simple_experiment.experiment_id)
    for r in results:
        assert r.rate == 0.0
        assert r.confidence_interval == (0.0, 0.0)


# ---------------------------------------------------------------------------
# Wilson confidence interval
# ---------------------------------------------------------------------------

def test_wilson_interval_basic():
    lower, upper = wilson_confidence_interval(100, 50)
    # 50% rate with n=100, interval should be roughly (0.40, 0.60)
    assert 0.35 < lower < 0.45
    assert 0.55 < upper < 0.65


def test_wilson_interval_zero_trials():
    assert wilson_confidence_interval(0, 0) == (0.0, 0.0)


def test_wilson_interval_bounds():
    """Lower bound should be >= 0 and upper bound should be <= 1."""
    lower, upper = wilson_confidence_interval(10, 0)
    assert lower >= 0.0
    assert upper >= 0.0

    lower, upper = wilson_confidence_interval(10, 10)
    assert lower <= 1.0
    assert upper <= 1.0


def test_wilson_interval_symmetry():
    """Interval around 50% should be approximately symmetric."""
    lower, upper = wilson_confidence_interval(1000, 500)
    centre = 0.5
    assert math.isclose(centre - lower, upper - centre, abs_tol=0.005)


# ---------------------------------------------------------------------------
# Z-test
# ---------------------------------------------------------------------------

def test_z_test_identical_proportions():
    z, p = z_test_proportions(100, 50, 100, 50)
    assert math.isclose(z, 0.0, abs_tol=1e-6)
    assert math.isclose(p, 1.0, abs_tol=0.01)


def test_z_test_known_significant():
    """Large difference with large samples should be significant."""
    # Group 1: 30% conversion, Group 2: 10% conversion, n=500 each
    z, p = z_test_proportions(500, 150, 500, 50)
    assert abs(z) > 2.0  # should be well beyond z=1.96
    assert p < 0.05


def test_z_test_known_not_significant():
    """Very small difference with small samples should not be significant."""
    z, p = z_test_proportions(20, 5, 20, 4)
    assert p > 0.05


def test_z_test_zero_samples():
    z, p = z_test_proportions(0, 0, 0, 0)
    assert z == 0.0
    assert p == 1.0


# ---------------------------------------------------------------------------
# Significance & winner
# ---------------------------------------------------------------------------

def test_is_significant_not_enough_data(engine, simple_experiment):
    """Below min_sample_size, should not be significant."""
    eid = simple_experiment.experiment_id
    # Only 10 impressions each (min_sample_size is 50)
    for _ in range(10):
        engine.record_impression(eid, "A")
        engine.record_impression(eid, "B")
    for _ in range(5):
        engine.record_conversion(eid, "A")

    assert engine.is_significant(eid) is False


def test_is_significant_with_enough_data(engine):
    """Clear winner with enough data should be significant."""
    exp = engine.create_experiment(
        name="clear_winner",
        variants=[
            Variant(variant_id="A", name="good", weight=0.5),
            Variant(variant_id="B", name="bad", weight=0.5),
        ],
        min_sample_size=50,
    )
    eid = exp.experiment_id

    # A: 200 impressions, 80 conversions (40%)
    for _ in range(200):
        engine.record_impression(eid, "A")
    for _ in range(80):
        engine.record_conversion(eid, "A")

    # B: 200 impressions, 20 conversions (10%)
    for _ in range(200):
        engine.record_impression(eid, "B")
    for _ in range(20):
        engine.record_conversion(eid, "B")

    assert engine.is_significant(eid) is True


def test_get_winner_returns_best_variant(engine):
    exp = engine.create_experiment(
        name="winner_test",
        variants=[
            Variant(variant_id="A", name="winner", weight=0.5),
            Variant(variant_id="B", name="loser", weight=0.5),
        ],
        min_sample_size=50,
    )
    eid = exp.experiment_id

    for _ in range(200):
        engine.record_impression(eid, "A")
    for _ in range(80):
        engine.record_conversion(eid, "A")
    for _ in range(200):
        engine.record_impression(eid, "B")
    for _ in range(20):
        engine.record_conversion(eid, "B")

    winner = engine.get_winner(eid)
    assert winner is not None
    assert winner.variant_id == "A"


def test_get_winner_returns_none_when_not_significant(engine, simple_experiment):
    assert engine.get_winner(simple_experiment.experiment_id) is None


# ---------------------------------------------------------------------------
# Experiment lifecycle
# ---------------------------------------------------------------------------

def test_list_experiments(engine):
    engine.create_experiment(
        name="exp1",
        variants=[
            Variant(variant_id="A", name="a", weight=0.5),
            Variant(variant_id="B", name="b", weight=0.5),
        ],
    )
    engine.create_experiment(
        name="exp2",
        variants=[
            Variant(variant_id="A", name="a", weight=0.5),
            Variant(variant_id="B", name="b", weight=0.5),
        ],
    )
    assert len(engine.list_experiments()) == 2


def test_complete_experiment(engine, simple_experiment):
    completed = engine.complete_experiment(simple_experiment.experiment_id)
    assert completed.status == ExperimentStatus.COMPLETED
    assert completed.end_date is not None


def test_complete_unknown_experiment(engine):
    with pytest.raises(ValueError, match="not found"):
        engine.complete_experiment("EXP-9999")


# ---------------------------------------------------------------------------
# Pre-configured experiments
# ---------------------------------------------------------------------------

def test_create_default_experiments():
    engine = ABTestEngine()
    experiments = create_default_experiments(engine)
    assert len(experiments) == 2

    names = {e.name for e in experiments}
    assert "email_subject_test" in names
    assert "channel_preference" in names

    # Channel preference should have 3 variants
    channel_exp = next(e for e in experiments if e.name == "channel_preference")
    assert len(channel_exp.variants) == 3


def test_three_variant_experiment(engine):
    """Experiment with 3 variants should work correctly."""
    exp = engine.create_experiment(
        name="triple",
        variants=[
            Variant(variant_id="A", name="a", weight=0.34),
            Variant(variant_id="B", name="b", weight=0.33),
            Variant(variant_id="C", name="c", weight=0.33),
        ],
        min_sample_size=20,
    )
    variants_seen = set()
    for i in range(200):
        v = engine.assign_variant(exp.experiment_id, f"lead-{i}")
        variants_seen.add(v.variant_id)
    assert len(variants_seen) == 3
