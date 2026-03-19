"""A/B Testing Engine — run experiments on outreach messages and agent responses.

Provides deterministic variant assignment, impression/conversion tracking,
and statistical analysis (z-test for proportions, Wilson confidence intervals)
without requiring scipy.
"""

import hashlib
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"


class ExperimentMetric(str, Enum):
    REPLY_RATE = "reply_rate"
    CONVERSION_RATE = "conversion_rate"
    OPEN_RATE = "open_rate"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Variant:
    """A single variant in an A/B experiment."""
    variant_id: str  # "A", "B", "C", ...
    name: str
    content: dict = field(default_factory=dict)
    weight: float = 0.5  # 0.0 – 1.0

    def __post_init__(self):
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError(f"Variant weight must be between 0.0 and 1.0, got {self.weight}")


@dataclass
class Experiment:
    """An A/B experiment definition."""
    experiment_id: str
    name: str
    description: str
    variants: list[Variant] = field(default_factory=list)
    status: ExperimentStatus = ExperimentStatus.DRAFT
    metric: ExperimentMetric = ExperimentMetric.REPLY_RATE
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_sample_size: int = 100
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExperimentResult:
    """Results for a single variant in an experiment."""
    experiment_id: str
    variant_id: str
    impressions: int = 0  # number sent / shown
    conversions: int = 0  # number of replies / opens / conversions
    rate: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 0.0)


# ---------------------------------------------------------------------------
# Statistical helpers (pure math, no scipy)
# ---------------------------------------------------------------------------

def _normal_cdf(x: float) -> float:
    """Approximate cumulative distribution function for standard normal.

    Uses the Abramowitz & Stegun approximation (formula 26.2.17),
    accurate to ~1.5e-7.
    """
    sign = 1.0 if x >= 0 else -1.0
    x = abs(x)

    # Constants
    b1 = 0.319381530
    b2 = -0.356563782
    b3 = 1.781477937
    b4 = -1.821255978
    b5 = 1.330274429
    p = 0.2316419

    t = 1.0 / (1.0 + p * x)
    t2 = t * t
    t3 = t2 * t
    t4 = t3 * t
    t5 = t4 * t

    phi = 1.0 - (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-x * x / 2.0) * (
        b1 * t + b2 * t2 + b3 * t3 + b4 * t4 + b5 * t5
    )

    return 0.5 + sign * (phi - 0.5)


def z_test_proportions(n1: int, c1: int, n2: int, c2: int) -> tuple[float, float]:
    """Two-proportion z-test.

    Parameters
    ----------
    n1 : int
        Sample size for group 1 (impressions).
    c1 : int
        Successes (conversions) for group 1.
    n2 : int
        Sample size for group 2.
    c2 : int
        Successes for group 2.

    Returns
    -------
    tuple[float, float]
        (z-statistic, two-sided p-value)
    """
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0

    p1 = c1 / n1
    p2 = c2 / n2

    # Pooled proportion
    p_pool = (c1 + c2) / (n1 + n2)

    if p_pool == 0.0 or p_pool == 1.0:
        return 0.0, 1.0

    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return 0.0, 1.0

    z = (p1 - p2) / se

    # Two-tailed p-value
    p_value = 2.0 * (1.0 - _normal_cdf(abs(z)))
    return z, p_value


def wilson_confidence_interval(
    n: int, conversions: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion.

    Parameters
    ----------
    n : int
        Total trials (impressions).
    conversions : int
        Number of successes.
    confidence : float
        Confidence level (default 0.95 for 95% CI).

    Returns
    -------
    tuple[float, float]
        (lower_bound, upper_bound) of the proportion.
    """
    if n == 0:
        return 0.0, 0.0

    # z-value for confidence level (two-tailed)
    # For 0.95 -> 1.96, 0.99 -> 2.576, 0.90 -> 1.645
    # We use an approximation via inverse normal
    alpha = 1.0 - confidence
    # Common z-values
    z_map = {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}
    z = z_map.get(confidence, 1.9600)

    p_hat = conversions / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = p_hat + z2 / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z2 / (4 * n)) / n)

    lower = max(0.0, (centre - margin) / denominator)
    upper = min(1.0, (centre + margin) / denominator)

    return round(lower, 6), round(upper, 6)


# ---------------------------------------------------------------------------
# A/B Test Engine
# ---------------------------------------------------------------------------

class ABTestEngine:
    """Manages experiment lifecycle, variant assignment, and statistical analysis."""

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}
        self._impressions: dict[str, dict[str, int]] = {}   # exp_id -> {variant_id: count}
        self._conversions: dict[str, dict[str, int]] = {}   # exp_id -> {variant_id: count}
        self._assignments: dict[str, dict[str, str]] = {}   # exp_id -> {lead_id: variant_id}
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"EXP-{self._counter:04d}"

    # ----- Experiment CRUD -----

    def create_experiment(
        self,
        name: str,
        variants: list[Variant],
        metric: ExperimentMetric | str = ExperimentMetric.REPLY_RATE,
        min_sample_size: int = 100,
        description: str = "",
    ) -> Experiment:
        """Create a new experiment with the given variants."""
        if isinstance(metric, str):
            metric = ExperimentMetric(metric)

        if len(variants) < 2:
            raise ValueError("An experiment needs at least 2 variants")

        # Normalise weights so they sum to 1.0
        total_weight = sum(v.weight for v in variants)
        if total_weight <= 0:
            raise ValueError("Total variant weight must be > 0")
        for v in variants:
            v.weight = v.weight / total_weight

        experiment_id = self._next_id()
        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variants,
            status=ExperimentStatus.RUNNING,
            metric=metric,
            start_date=datetime.now(),
            min_sample_size=min_sample_size,
        )

        self._experiments[experiment_id] = experiment
        self._impressions[experiment_id] = {v.variant_id: 0 for v in variants}
        self._conversions[experiment_id] = {v.variant_id: 0 for v in variants}
        self._assignments[experiment_id] = {}

        logger.info("Experiment created: %s — %s", experiment_id, name)
        return experiment

    def get_experiment(self, experiment_id: str) -> Experiment | None:
        return self._experiments.get(experiment_id)

    def list_experiments(self) -> list[Experiment]:
        return sorted(
            self._experiments.values(),
            key=lambda e: e.created_at,
            reverse=True,
        )

    def complete_experiment(self, experiment_id: str) -> Experiment:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")
        experiment.status = ExperimentStatus.COMPLETED
        experiment.end_date = datetime.now()
        logger.info("Experiment completed: %s", experiment_id)
        return experiment

    # ----- Variant assignment -----

    def assign_variant(self, experiment_id: str, lead_id: str) -> Variant:
        """Deterministically assign a lead to a variant based on hash.

        The assignment is stable: the same lead_id always gets the same
        variant for a given experiment.  Weights are respected via
        cumulative thresholds on the hash value.
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Return cached assignment if already assigned
        if lead_id in self._assignments.get(experiment_id, {}):
            variant_id = self._assignments[experiment_id][lead_id]
            return next(v for v in experiment.variants if v.variant_id == variant_id)

        # Deterministic hash -> float in [0, 1)
        hash_input = f"{experiment_id}:{lead_id}"
        hash_bytes = hashlib.sha256(hash_input.encode()).hexdigest()
        hash_value = int(hash_bytes[:8], 16) / 0xFFFFFFFF

        # Walk cumulative weights to pick variant
        cumulative = 0.0
        chosen = experiment.variants[-1]  # fallback
        for variant in experiment.variants:
            cumulative += variant.weight
            if hash_value < cumulative:
                chosen = variant
                break

        self._assignments.setdefault(experiment_id, {})[lead_id] = chosen.variant_id
        return chosen

    # ----- Tracking -----

    def record_impression(self, experiment_id: str, variant_id: str) -> None:
        """Record that a lead saw / was sent this variant."""
        if experiment_id not in self._impressions:
            raise ValueError(f"Experiment {experiment_id} not found")
        if variant_id not in self._impressions[experiment_id]:
            raise ValueError(f"Variant {variant_id} not in experiment {experiment_id}")
        self._impressions[experiment_id][variant_id] += 1

    def record_conversion(self, experiment_id: str, variant_id: str) -> None:
        """Record that a lead converted (replied, opened, etc.)."""
        if experiment_id not in self._conversions:
            raise ValueError(f"Experiment {experiment_id} not found")
        if variant_id not in self._conversions[experiment_id]:
            raise ValueError(f"Variant {variant_id} not in experiment {experiment_id}")
        self._conversions[experiment_id][variant_id] += 1

    # ----- Results & Statistics -----

    def get_results(self, experiment_id: str) -> list[ExperimentResult]:
        """Return per-variant results with conversion rates and CIs."""
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        results: list[ExperimentResult] = []
        for variant in experiment.variants:
            vid = variant.variant_id
            impressions = self._impressions[experiment_id].get(vid, 0)
            conversions = self._conversions[experiment_id].get(vid, 0)
            rate = conversions / impressions if impressions > 0 else 0.0
            ci = wilson_confidence_interval(impressions, conversions)

            results.append(ExperimentResult(
                experiment_id=experiment_id,
                variant_id=vid,
                impressions=impressions,
                conversions=conversions,
                rate=round(rate, 6),
                confidence_interval=ci,
            ))

        return results

    def is_significant(self, experiment_id: str) -> bool:
        """Check whether the experiment has enough data for a conclusion.

        Requires all variants to have at least min_sample_size impressions
        AND the z-test between the best and second-best to be p < 0.05.
        """
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError(f"Experiment {experiment_id} not found")

        # Check minimum sample size
        for variant in experiment.variants:
            vid = variant.variant_id
            if self._impressions[experiment_id].get(vid, 0) < experiment.min_sample_size:
                return False

        # Check statistical significance between best two
        results = self.get_results(experiment_id)
        if len(results) < 2:
            return False

        sorted_results = sorted(results, key=lambda r: r.rate, reverse=True)
        best = sorted_results[0]
        second = sorted_results[1]

        _, p_value = z_test_proportions(
            best.impressions, best.conversions,
            second.impressions, second.conversions,
        )
        return p_value < 0.05

    def get_winner(self, experiment_id: str) -> Variant | None:
        """Return the winning variant if statistically significant, else None."""
        if not self.is_significant(experiment_id):
            return None

        experiment = self._experiments[experiment_id]
        results = self.get_results(experiment_id)
        best_result = max(results, key=lambda r: r.rate)

        return next(
            v for v in experiment.variants if v.variant_id == best_result.variant_id
        )


# ---------------------------------------------------------------------------
# Singleton engine instance
# ---------------------------------------------------------------------------

ab_test_engine = ABTestEngine()


# ---------------------------------------------------------------------------
# Pre-configured experiments
# ---------------------------------------------------------------------------

def create_default_experiments(engine: ABTestEngine | None = None) -> list[Experiment]:
    """Create standard experiments for common outreach scenarios."""
    engine = engine or ab_test_engine
    experiments = []

    # 1. Email subject line test: direct vs question
    email_subject_exp = engine.create_experiment(
        name="email_subject_test",
        description="Test directo vs pregunta approach for email subject lines",
        variants=[
            Variant(
                variant_id="A",
                name="directo",
                content={
                    "subject_template": "Soluciones de {product} para {company}",
                    "style": "direct_value_proposition",
                },
                weight=0.5,
            ),
            Variant(
                variant_id="B",
                name="pregunta",
                content={
                    "subject_template": "Como maneja {company} su {pain_point}?",
                    "style": "question_based",
                },
                weight=0.5,
            ),
        ],
        metric=ExperimentMetric.REPLY_RATE,
        min_sample_size=200,
    )
    experiments.append(email_subject_exp)

    # 2. Channel preference test
    channel_pref_exp = engine.create_experiment(
        name="channel_preference",
        description="Test initial outreach channel: email vs LinkedIn vs WhatsApp",
        variants=[
            Variant(
                variant_id="A",
                name="email",
                content={"channel": "email", "followup_channel": "linkedin"},
                weight=0.34,
            ),
            Variant(
                variant_id="B",
                name="linkedin",
                content={"channel": "linkedin", "followup_channel": "email"},
                weight=0.33,
            ),
            Variant(
                variant_id="C",
                name="whatsapp",
                content={"channel": "whatsapp", "followup_channel": "email"},
                weight=0.33,
            ),
        ],
        metric=ExperimentMetric.CONVERSION_RATE,
        min_sample_size=150,
    )
    experiments.append(channel_pref_exp)

    return experiments
