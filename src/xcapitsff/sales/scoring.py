"""ICP Scoring Engine — weighted multi-factor model for lead scoring.

This module implements a sophisticated scoring engine that evaluates leads
across multiple dimensions (region, seniority, affinity, engagement, and
company fit) using configurable weights.  Each factor is scored independently
on a 0-100 scale and then combined into a single composite score via a
weighted sum.

The engine also provides:
- Classification with confidence levels based on data completeness.
- Batch scoring with summary statistics.
- Score recalculation via exponential moving average for incremental updates.
- Full backward compatibility with the legacy ``calculate_icp_score`` API.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Sequence

from xcapitsff.core.schemas import AfinidadEnum, LeadResponse

# ---------------------------------------------------------------------------
# Configurable weights -- must sum to 1.0
# ---------------------------------------------------------------------------

WEIGHTS: dict[str, float] = {
    "region": 0.15,
    "c_level": 0.25,
    "afinidad": 0.30,
    "engagement": 0.15,
    "company_fit": 0.15,
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FactorBreakdown:
    """Detailed breakdown of each factor's raw and weighted contribution."""

    factor: str
    raw_score: float
    weight: float
    weighted_score: float


@dataclass
class ScoringResult:
    """Complete result of scoring a single lead.

    Attributes:
        score: Composite score in the range 0-100.
        classification: One of ``"hot"``, ``"warm"``, ``"cool"``, ``"cold"``.
        confidence: A value between 0.0 and 1.0 indicating how much data was
            available to compute the score.  Higher is more reliable.
        factor_breakdown: Per-factor detail (raw score, weight, contribution).
        recommendations: Actionable next-step suggestions for the sales team.
    """

    score: float
    classification: str
    confidence: float
    factor_breakdown: list[FactorBreakdown] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class BatchScoringResult:
    """Result of scoring a batch of leads.

    Attributes:
        results: Individual ``ScoringResult`` for each lead, in order.
        total: Number of leads scored.
        mean_score: Average composite score.
        median_score: Median composite score.
        std_dev: Standard deviation of composite scores.
        distribution: Count of leads in each classification bucket.
    """

    results: list[ScoringResult]
    total: int
    mean_score: float
    median_score: float
    std_dev: float
    distribution: dict[str, int]


# ---------------------------------------------------------------------------
# Per-factor scoring functions
# ---------------------------------------------------------------------------


def score_region(region: str) -> float:
    """Score a lead's region on a 0-100 scale.

    LATAM is the primary market for Xcapit and receives the highest score.
    Iberia is a secondary market.  All other regions receive a baseline score.

    Args:
        region: Region identifier (e.g. ``"LATAM"``, ``"Iberia"``).

    Returns:
        A score between 0 and 100.
    """
    region_upper = region.strip().upper()
    if region_upper == "LATAM":
        return 90.0
    if region_upper in ("IBERIA", "IBÉRIA"):
        return 60.0
    return 30.0


def score_c_level(is_c_level: bool) -> float:
    """Score a lead based on executive seniority.

    C-level contacts are significantly more valuable because they can make
    purchasing decisions.

    Args:
        is_c_level: Whether the contact holds a C-level position.

    Returns:
        100.0 if C-level, 30.0 otherwise.
    """
    return 100.0 if is_c_level else 30.0


def score_afinidad(afinidad: str) -> float:
    """Score a lead's brand/product affinity.

    Args:
        afinidad: One of ``"HIGH"``, ``"MEDIUM"``, or ``"LOW"``.

    Returns:
        A score between 0 and 100.
    """
    mapping: dict[str, float] = {
        "HIGH": 100.0,
        "MEDIUM": 50.0,
        "LOW": 10.0,
    }
    return mapping.get(afinidad.strip().upper(), 10.0)


def score_engagement(interactions: int = 0, days_since_last: int | None = None) -> float:
    """Score engagement using an interaction-count base with time-decay.

    The formula rewards more interactions (up to a saturation point) and
    penalises stale contacts via an exponential decay based on the number of
    days since the last interaction.

    Interaction base (0-100):
        ``min(interactions / 10, 1.0) * 100``

    Decay factor:
        ``exp(-0.03 * days_since_last)``  (half-life ~ 23 days)

    If interactions=0 and days_since_last is None (new lead), a moderate
    baseline of 40.0 is applied (benefit of the doubt, not penalized for
    lack of data). Otherwise, if *days_since_last* is ``None``, a moderate
    default penalty of 0.5 is applied.

    Args:
        interactions: Total number of recorded interactions.
        days_since_last: Calendar days since the most recent interaction,
            or ``None`` if unknown.

    Returns:
        A score between 0 and 100.
    """
    if interactions < 0:
        interactions = 0

    # New lead baseline -- not penalized for lack of data
    if interactions == 0 and days_since_last is None:
        return 40.0

    # Saturating interaction score
    base = min(interactions / 10.0, 1.0) * 100.0

    # Time-decay
    if days_since_last is None:
        decay = 0.5
    elif days_since_last <= 0:
        decay = 1.0
    else:
        decay = math.exp(-0.03 * days_since_last)

    return round(min(max(base * decay, 0.0), 100.0), 2)


def score_company_fit(score_icp_manual: float | None) -> float:
    """Normalise a manually-assigned ICP score to the 0-100 range.

    If the manual score is ``None`` or negative, a benefit-of-the-doubt
    default of 70.0 is returned so that new leads are not unfairly penalized
    for lacking manual evaluation data.

    Args:
        score_icp_manual: Raw manual score (expected 0-100) or ``None``.

    Returns:
        A score clamped to 0-100.
    """
    if score_icp_manual is None:
        return 70.0  # Changed from 50.0 — give new leads benefit of doubt
    return min(max(float(score_icp_manual), 0.0), 100.0)


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------

# Each key maps to the weight that factor contributes toward "data
# completeness".  If the data for a factor is present we add its weight.
# NOTE: engagement and company_fit now provide reasonable defaults for new
# leads (40.0 and 70.0 respectively) so they do not artificially penalize
# leads with missing data. Confidence still reflects data completeness.
_CONFIDENCE_COMPONENTS: dict[str, float] = {
    "region": 0.15,
    "c_level": 0.15,
    "afinidad": 0.20,
    "engagement": 0.25,
    "company_fit": 0.25,
}


def _compute_confidence(
    *,
    region_known: bool = True,
    c_level_known: bool = True,
    afinidad_known: bool = True,
    engagement_known: bool = False,
    company_fit_known: bool = False,
) -> float:
    """Return a 0.0-1.0 confidence value based on data completeness.

    Args:
        region_known: Whether the region field is populated.
        c_level_known: Whether the c_level field is populated.
        afinidad_known: Whether the afinidad field is populated.
        engagement_known: Whether engagement data (interactions) is available.
        company_fit_known: Whether a manual ICP score has been assigned.

    Returns:
        A float between 0.0 and 1.0.
    """
    flags = {
        "region": region_known,
        "c_level": c_level_known,
        "afinidad": afinidad_known,
        "engagement": engagement_known,
        "company_fit": company_fit_known,
    }
    return round(
        sum(
            _CONFIDENCE_COMPONENTS[k] for k, present in flags.items() if present
        ),
        2,
    )


# ---------------------------------------------------------------------------
# Recommendations engine
# ---------------------------------------------------------------------------


def _generate_recommendations(
    classification: str,
    factor_breakdown: list[FactorBreakdown],
    confidence: float,
) -> list[str]:
    """Generate actionable recommendations based on the scoring result.

    Args:
        classification: The lead classification (hot/warm/cool/cold).
        factor_breakdown: Per-factor scoring details.
        confidence: Data-completeness confidence value.

    Returns:
        A list of human-readable recommendation strings.
    """
    recs: list[str] = []

    factor_map = {fb.factor: fb for fb in factor_breakdown}

    # Low confidence -- ask for more data
    if confidence < 0.6:
        recs.append("Gather more data to improve scoring confidence.")

    # Engagement is the most actionable lever
    engagement_fb = factor_map.get("engagement")
    if engagement_fb and engagement_fb.raw_score < 30:
        recs.append("Increase engagement: schedule a call or send personalised content.")

    # Company fit
    company_fb = factor_map.get("company_fit")
    if company_fb and company_fb.raw_score == 50.0:
        recs.append("Assign a manual ICP score to improve scoring accuracy.")

    # Classification-based
    if classification == "hot":
        recs.append("Prioritise for immediate outreach and meeting scheduling.")
    elif classification == "warm":
        recs.append("Nurture with targeted content and follow-up within the week.")
    elif classification == "cool":
        recs.append("Add to drip campaign and monitor for engagement signals.")
    elif classification == "cold":
        recs.append("Park for now; revisit when new signals emerge.")

    return recs


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_lead(score: float) -> str:
    """Classify a lead based on its composite ICP score.

    Thresholds:
        - **hot**: score >= 70
        - **warm**: 45 <= score < 70
        - **cool**: 25 <= score < 45
        - **cold**: score < 25

    Args:
        score: Composite ICP score (0-100).

    Returns:
        A classification string.
    """
    if score >= 70:
        return "hot"
    if score >= 45:
        return "warm"
    if score >= 25:
        return "cool"
    return "cold"


# ---------------------------------------------------------------------------
# Core scoring engine
# ---------------------------------------------------------------------------


def score_lead(
    *,
    region: str = "LATAM",
    c_level: bool = False,
    afinidad: str = "MEDIUM",
    interactions: int = 0,
    days_since_last: int | None = None,
    score_icp_manual: float | None = None,
    weights: dict[str, float] | None = None,
) -> ScoringResult:
    """Score a single lead using the weighted multi-factor model.

    This is the primary entry point for the new scoring engine.  Each factor
    is evaluated independently, then combined via a configurable weighted sum.

    Args:
        region: Lead region identifier.
        c_level: Whether the contact is C-level.
        afinidad: Affinity level (``"HIGH"``, ``"MEDIUM"``, ``"LOW"``).
        interactions: Number of recorded interactions (for engagement).
        days_since_last: Days since last interaction, or ``None``.
        score_icp_manual: Manually assigned ICP score, or ``None``.
        weights: Optional override for the global ``WEIGHTS`` dict.

    Returns:
        A ``ScoringResult`` with the composite score, classification,
        confidence, factor breakdown, and recommendations.
    """
    w = weights if weights is not None else WEIGHTS

    # Compute raw factor scores
    raw: dict[str, float] = {
        "region": score_region(region),
        "c_level": score_c_level(c_level),
        "afinidad": score_afinidad(afinidad),
        "engagement": score_engagement(interactions, days_since_last),
        "company_fit": score_company_fit(score_icp_manual),
    }

    # Build breakdown and composite score
    breakdown: list[FactorBreakdown] = []
    composite = 0.0
    for factor, raw_val in raw.items():
        weight = w.get(factor, 0.0)
        weighted = raw_val * weight
        composite += weighted
        breakdown.append(
            FactorBreakdown(
                factor=factor,
                raw_score=round(raw_val, 2),
                weight=weight,
                weighted_score=round(weighted, 2),
            )
        )

    composite = round(min(max(composite, 0.0), 100.0), 1)

    classification = classify_lead(composite)

    # Confidence
    engagement_known = interactions > 0 or days_since_last is not None
    company_fit_known = score_icp_manual is not None
    confidence = _compute_confidence(
        region_known=True,
        c_level_known=True,
        afinidad_known=True,
        engagement_known=engagement_known,
        company_fit_known=company_fit_known,
    )

    recommendations = _generate_recommendations(classification, breakdown, confidence)

    return ScoringResult(
        score=composite,
        classification=classification,
        confidence=confidence,
        factor_breakdown=breakdown,
        recommendations=recommendations,
    )


# ---------------------------------------------------------------------------
# Batch scoring
# ---------------------------------------------------------------------------


def score_leads_batch(
    leads: Sequence[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> BatchScoringResult:
    """Score a sequence of leads and compute summary statistics.

    Each element in *leads* should be a dict whose keys match the keyword
    arguments of :func:`score_lead` (``region``, ``c_level``, ``afinidad``,
    ``interactions``, ``days_since_last``, ``score_icp_manual``).  Missing
    keys will fall back to the defaults in ``score_lead``.

    Args:
        leads: Iterable of lead data dicts.
        weights: Optional weight override passed to each ``score_lead`` call.

    Returns:
        A ``BatchScoringResult`` with individual results and aggregate stats.
    """
    results: list[ScoringResult] = []
    scores: list[float] = []
    distribution: dict[str, int] = {"hot": 0, "warm": 0, "cool": 0, "cold": 0}

    for lead_data in leads:
        result = score_lead(**lead_data, weights=weights)
        results.append(result)
        scores.append(result.score)
        distribution[result.classification] += 1

    total = len(scores)
    if total == 0:
        return BatchScoringResult(
            results=[],
            total=0,
            mean_score=0.0,
            median_score=0.0,
            std_dev=0.0,
            distribution=distribution,
        )

    mean = statistics.mean(scores)
    median = statistics.median(scores)
    std = statistics.pstdev(scores) if total > 1 else 0.0

    return BatchScoringResult(
        results=results,
        total=total,
        mean_score=round(mean, 2),
        median_score=round(median, 2),
        std_dev=round(std, 2),
        distribution=distribution,
    )


# ---------------------------------------------------------------------------
# Score recalculation (exponential moving average)
# ---------------------------------------------------------------------------


def recalculate_score(
    existing_score: float,
    new_data: dict[str, Any],
    alpha: float = 0.4,
    weights: dict[str, float] | None = None,
) -> ScoringResult:
    """Update an existing score with new data using exponential moving average.

    The updated score is computed as::

        updated = alpha * new_score + (1 - alpha) * existing_score

    This allows the score to gradually adapt to new information without
    discarding historical assessments entirely.

    Args:
        existing_score: The lead's current composite score (0-100).
        new_data: Dict of keyword arguments for :func:`score_lead`.
        alpha: Smoothing factor in the range (0, 1].  Higher values give
            more weight to the new data.  Defaults to 0.4.
        weights: Optional weight override for the underlying scoring call.

    Returns:
        A ``ScoringResult`` whose ``score`` is the EMA-blended value.
    """
    alpha = min(max(alpha, 0.0), 1.0)

    new_result = score_lead(**new_data, weights=weights)
    blended = round(alpha * new_result.score + (1 - alpha) * existing_score, 1)
    blended = min(max(blended, 0.0), 100.0)

    classification = classify_lead(blended)

    return ScoringResult(
        score=blended,
        classification=classification,
        confidence=new_result.confidence,
        factor_breakdown=new_result.factor_breakdown,
        recommendations=_generate_recommendations(
            classification, new_result.factor_breakdown, new_result.confidence
        ),
    )


# ---------------------------------------------------------------------------
# Backward-compatible legacy API
# ---------------------------------------------------------------------------


def calculate_icp_score(
    region: str,
    c_level: bool,
    existing_score: float | None = None,
    afinidad: str = "MEDIUM",
) -> float:
    """Calculate an ICP score -- backward-compatible wrapper.

    This function preserves the original signature so that existing callers
    (e.g. ``pipeline.py``, ``importer.py``) continue to work without changes.
    Internally it delegates to the new multi-factor engine.

    When *existing_score* is provided and positive, the result is blended
    using :func:`recalculate_score` with alpha=0.4 (same 60/40 weighting
    as the legacy implementation).

    Args:
        region: Lead region identifier.
        c_level: Whether the contact is C-level.
        existing_score: Previously stored manual score, or ``None``.
        afinidad: Affinity level string.

    Returns:
        A float score in the range 0-100.
    """
    new_data: dict[str, Any] = {
        "region": region,
        "c_level": c_level,
        "afinidad": afinidad,
    }

    if existing_score is not None and existing_score > 0:
        result = recalculate_score(
            existing_score=existing_score,
            new_data=new_data,
            alpha=0.4,
        )
        return result.score

    result = score_lead(**new_data)
    return result.score


# ---------------------------------------------------------------------------
# Legacy helpers (unchanged public API)
# ---------------------------------------------------------------------------


def should_auto_qualify(lead: LeadResponse) -> bool:
    """Determine whether a lead should be auto-qualified.

    A lead qualifies automatically when either:
    - It has an ICP score >= 60 **and** is C-level, or
    - Its affinity is ``HIGH`` and it is C-level.

    Args:
        lead: A ``LeadResponse`` instance.

    Returns:
        ``True`` if the lead should be auto-qualified.
    """
    if lead.score_icp is not None and lead.score_icp >= 60 and lead.c_level:
        return True
    if lead.afinidad == AfinidadEnum.HIGH and lead.c_level:
        return True
    return False


def segment_leads(leads: list[LeadResponse]) -> dict[str, list[LeadResponse]]:
    """Segment leads into classification buckets for outreach prioritisation.

    Args:
        leads: List of ``LeadResponse`` instances.

    Returns:
        A dict mapping classification names (``"hot"``, ``"warm"``, ``"cool"``,
        ``"cold"``, ``"no_score"``) to lists of leads.
    """
    segments: dict[str, list[LeadResponse]] = {
        "hot": [],
        "warm": [],
        "cool": [],
        "cold": [],
        "no_score": [],
    }

    for lead in leads:
        if lead.score_icp is None:
            segments["no_score"].append(lead)
        else:
            category = classify_lead(lead.score_icp)
            segments[category].append(lead)

    return segments
