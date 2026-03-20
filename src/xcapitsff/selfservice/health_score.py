"""Workspace Health Score — show users how well they're using the product.

Runs a suite of health checks across data quality, pipeline, support,
agent utilisation, configuration and engagement, producing an overall
score (0-100) and actionable recommendations in Spanish.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & data classes
# ---------------------------------------------------------------------------


class HealthCategory(str, Enum):
    DATA_QUALITY = "data_quality"
    PIPELINE_HEALTH = "pipeline_health"
    SUPPORT_EFFICIENCY = "support_efficiency"
    AGENT_UTILIZATION = "agent_utilization"
    CONFIGURATION = "configuration"
    ENGAGEMENT = "engagement"


@dataclass
class HealthCheck:
    category: HealthCategory
    name: str
    score: int  # 0-100
    status: str  # good / warning / critical
    recommendation: str
    weight: float


@dataclass
class WorkspaceHealth:
    overall_score: int  # 0-100
    grade: str  # A / B / C / D / F
    checks: list[HealthCheck] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    last_checked: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Category weights
# ---------------------------------------------------------------------------

CATEGORY_WEIGHTS: dict[HealthCategory, float] = {
    HealthCategory.DATA_QUALITY: 0.15,
    HealthCategory.PIPELINE_HEALTH: 0.25,
    HealthCategory.SUPPORT_EFFICIENCY: 0.20,
    HealthCategory.AGENT_UTILIZATION: 0.15,
    HealthCategory.CONFIGURATION: 0.15,
    HealthCategory.ENGAGEMENT: 0.10,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _status(score: int) -> str:
    if score >= 75:
        return "good"
    if score >= 40:
        return "warning"
    return "critical"


def _clamp(value: int | float) -> int:
    return max(0, min(100, int(value)))


# ---------------------------------------------------------------------------
# Health Score Calculator
# ---------------------------------------------------------------------------


class HealthScoreCalculator:
    """Calculates a comprehensive workspace health score."""

    # === Grade mapping ===

    @staticmethod
    def get_grade(score: int) -> str:
        """Map numeric score to letter grade."""
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"

    # === Main entry point ===

    async def calculate_health(self, db: AsyncSession) -> WorkspaceHealth:
        """Run every health check and produce the workspace health report."""
        checks: list[HealthCheck] = []

        checks.extend(await self._check_data_quality(db))
        checks.extend(await self._check_pipeline_health(db))
        checks.extend(await self._check_support_efficiency(db))
        checks.extend(await self._check_agent_utilization(db))
        checks.extend(await self._check_configuration(db))
        checks.extend(await self._check_engagement(db))

        overall = self._weighted_score(checks)
        grade = self.get_grade(overall)
        recs = self.get_recommendations_from_checks(checks)

        return WorkspaceHealth(
            overall_score=overall,
            grade=grade,
            checks=checks,
            recommendations=recs,
            last_checked=datetime.now(tz=None),
        )

    # === Recommendations ===

    @staticmethod
    def get_recommendations(health: WorkspaceHealth) -> list[str]:
        """Return actionable recommendations in Spanish from a health report."""
        return health.recommendations

    @staticmethod
    def get_recommendations_from_checks(checks: list[HealthCheck]) -> list[str]:
        """Derive recommendations from individual checks."""
        recs: list[str] = []
        for check in checks:
            if check.status in ("warning", "critical") and check.recommendation:
                recs.append(check.recommendation)
        return recs

    # === Weighted score ===

    @staticmethod
    def _weighted_score(checks: list[HealthCheck]) -> int:
        """Compute the overall weighted score from all checks."""
        cat_scores: dict[HealthCategory, list[int]] = {}
        for ch in checks:
            cat_scores.setdefault(ch.category, []).append(ch.score)

        total = 0.0
        weight_sum = 0.0
        for cat, weight in CATEGORY_WEIGHTS.items():
            scores = cat_scores.get(cat, [])
            if scores:
                avg = sum(scores) / len(scores)
                total += avg * weight
                weight_sum += weight

        if weight_sum == 0:
            return 0
        return _clamp(total / weight_sum)

    # ------------------------------------------------------------------
    # DATA QUALITY (weight 15%)
    # ------------------------------------------------------------------

    async def _check_data_quality(self, db: AsyncSession) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        weight = CATEGORY_WEIGHTS[HealthCategory.DATA_QUALITY]
        cat = HealthCategory.DATA_QUALITY

        # leads_with_email
        total, with_email = await self._count_leads_field(db, "email")
        pct = (with_email / total * 100) if total else 0
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="leads_with_email",
            score=score,
            status=_status(score),
            recommendation=(
                "Agregá emails a tus leads para mejorar el alcance de outreach."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # leads_with_company
        total, with_company = await self._count_leads_field(db, "company_name")
        pct = (with_company / total * 100) if total else 0
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="leads_with_company",
            score=score,
            status=_status(score),
            recommendation=(
                "Complet\u00e1 el nombre de empresa en tus leads para mejor segmentaci\u00f3n."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # scoring_coverage
        total, with_score = await self._count_leads_field(db, "score_icp")
        pct = (with_score / total * 100) if total else 0
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="scoring_coverage",
            score=score,
            status=_status(score),
            recommendation=(
                "Ejecut\u00e1 el scoring ICP para priorizar mejor tus leads."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        return checks

    # ------------------------------------------------------------------
    # PIPELINE HEALTH (weight 25%)
    # ------------------------------------------------------------------

    async def _check_pipeline_health(self, db: AsyncSession) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        weight = CATEGORY_WEIGHTS[HealthCategory.PIPELINE_HEALTH]
        cat = HealthCategory.PIPELINE_HEALTH

        # pipeline_velocity — avg days to move between stages
        avg_days = await self._pipeline_avg_days(db)
        score = _clamp(100 - avg_days * 3) if avg_days is not None else 50
        checks.append(HealthCheck(
            category=cat,
            name="pipeline_velocity",
            score=score,
            status=_status(score),
            recommendation=(
                "Tus leads tardan mucho en avanzar. Revis\u00e1 los cuellos de botella del pipeline."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # stale_leads_ratio
        total_leads = await self._total_leads(db)
        stale = await self._stale_leads_count(db, days=30)
        pct_stale = (stale / total_leads * 100) if total_leads else 0
        score = _clamp(100 - pct_stale)
        checks.append(HealthCheck(
            category=cat,
            name="stale_leads_ratio",
            score=score,
            status=_status(score),
            recommendation=(
                "Ten\u00e9s muchos leads estancados (>30 d\u00edas). "
                "Considerá reactivarlos o archivarlos."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # conversion_rate
        won, total = await self._conversion_counts(db)
        pct = (won / total * 100) if total else 0
        score = _clamp(min(pct * 5, 100))  # 20% conversion → 100
        checks.append(HealthCheck(
            category=cat,
            name="conversion_rate",
            score=score,
            status=_status(score),
            recommendation=(
                "La tasa de conversi\u00f3n es baja. "
                "Revis\u00e1 la calificaci\u00f3n de leads y el proceso de ventas."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # hot_leads_actioned
        hot_total, hot_contacted = await self._hot_leads_actioned(db)
        pct = (hot_contacted / hot_total * 100) if hot_total else 100
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="hot_leads_actioned",
            score=score,
            status=_status(score),
            recommendation=(
                "Hay leads hot sin contactar. \u00a1No pierdas oportunidades!"
                if score < 75 else ""
            ),
            weight=weight,
        ))

        return checks

    # ------------------------------------------------------------------
    # SUPPORT EFFICIENCY (weight 20%)
    # ------------------------------------------------------------------

    async def _check_support_efficiency(self, db: AsyncSession) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        weight = CATEGORY_WEIGHTS[HealthCategory.SUPPORT_EFFICIENCY]
        cat = HealthCategory.SUPPORT_EFFICIENCY

        # sla_compliance
        total_tickets, within_sla = await self._sla_counts(db)
        pct = (within_sla / total_tickets * 100) if total_tickets else 100
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="sla_compliance",
            score=score,
            status=_status(score),
            recommendation=(
                "El cumplimiento de SLA es bajo. "
                "Revis\u00e1 los tiempos de respuesta y asignaci\u00f3n."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # avg_resolution_time
        avg_hours = await self._avg_resolution_hours(db)
        score = _clamp(100 - avg_hours * 2) if avg_hours is not None else 50
        checks.append(HealthCheck(
            category=cat,
            name="avg_resolution_time",
            score=score,
            status=_status(score),
            recommendation=(
                "El tiempo de resoluci\u00f3n es alto. "
                "Consider\u00e1 usar respuestas autom\u00e1ticas para tickets comunes."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # unassigned_tickets
        unassigned = await self._unassigned_ticket_count(db)
        score = _clamp(100 - unassigned * 10)
        checks.append(HealthCheck(
            category=cat,
            name="unassigned_tickets",
            score=score,
            status=_status(score),
            recommendation=(
                f"Hay {unassigned} tickets sin asignar. "
                "Activ\u00e1 el auto-routing para mejorar la eficiencia."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # response_rate
        total_tickets_rr, with_reply = await self._response_rate(db)
        pct = (with_reply / total_tickets_rr * 100) if total_tickets_rr else 100
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="response_rate",
            score=score,
            status=_status(score),
            recommendation=(
                "Hay tickets sin respuesta. "
                "Asegurate de que todos los tickets tengan al menos una respuesta."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        return checks

    # ------------------------------------------------------------------
    # AGENT UTILIZATION (weight 15%)
    # ------------------------------------------------------------------

    async def _check_agent_utilization(self, db: AsyncSession) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        weight = CATEGORY_WEIGHTS[HealthCategory.AGENT_UTILIZATION]
        cat = HealthCategory.AGENT_UTILIZATION

        # agents_active
        active = await self._agents_active(db)
        score = 100 if active else 0
        checks.append(HealthCheck(
            category=cat,
            name="agents_active",
            score=score,
            status=_status(score),
            recommendation=(
                "No est\u00e1s usando agentes de IA. "
                "Activalos para automatizar tareas repetitivas."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # outreach_sent
        sent = await self._outreach_sent_count(db)
        score = _clamp(min(sent * 5, 100))  # 20 messages → 100
        checks.append(HealthCheck(
            category=cat,
            name="outreach_sent",
            score=score,
            status=_status(score),
            recommendation=(
                "Se enviaron pocos mensajes de outreach este mes. "
                "Us\u00e1 el agente de outreach para generar m\u00e1s contactos."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # auto_responses
        total_t, auto_t = await self._auto_response_rate(db)
        pct = (auto_t / total_t * 100) if total_t else 0
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="auto_responses",
            score=score,
            status=_status(score),
            recommendation=(
                "Pocas respuestas autom\u00e1ticas. "
                "Configur\u00e1 el agente de soporte para responder tickets frecuentes."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        return checks

    # ------------------------------------------------------------------
    # CONFIGURATION (weight 15%)
    # ------------------------------------------------------------------

    async def _check_configuration(self, db: AsyncSession) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        weight = CATEGORY_WEIGHTS[HealthCategory.CONFIGURATION]
        cat = HealthCategory.CONFIGURATION

        # pipeline_configured
        configured = await self._has_custom_pipeline(db)
        score = 100 if configured else 0
        checks.append(HealthCheck(
            category=cat,
            name="pipeline_configured",
            score=score,
            status=_status(score),
            recommendation=(
                "No configuraste etapas personalizadas del pipeline. "
                "Adaptalo a tu proceso de ventas."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # templates_customized
        has_templates = await self._has_custom_templates(db)
        score = 100 if has_templates else 0
        checks.append(HealthCheck(
            category=cat,
            name="templates_customized",
            score=score,
            status=_status(score),
            recommendation=(
                "No ten\u00e9s templates personalizados. "
                "Cre\u00e1 templates para acelerar la comunicaci\u00f3n."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # integrations_connected
        has_integrations = await self._has_integrations(db)
        score = 100 if has_integrations else 0
        checks.append(HealthCheck(
            category=cat,
            name="integrations_connected",
            score=score,
            status=_status(score),
            recommendation=(
                "No ten\u00e9s integraciones conectadas (CRM/Slack). "
                "Conect\u00e1 tus herramientas para centralizar la informaci\u00f3n."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # kb_articles
        count = await self._kb_article_count(db)
        score = _clamp(min(count * 10, 100))  # 10 articles → 100
        checks.append(HealthCheck(
            category=cat,
            name="kb_articles",
            score=score,
            status=_status(score),
            recommendation=(
                "Tu base de conocimiento tiene pocos art\u00edculos. "
                "Agreg\u00e1 m\u00e1s para que el agente de soporte sea m\u00e1s efectivo."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        return checks

    # ------------------------------------------------------------------
    # ENGAGEMENT (weight 10%)
    # ------------------------------------------------------------------

    async def _check_engagement(self, db: AsyncSession) -> list[HealthCheck]:
        checks: list[HealthCheck] = []
        weight = CATEGORY_WEIGHTS[HealthCategory.ENGAGEMENT]
        cat = HealthCategory.ENGAGEMENT

        # daily_active
        api_calls = await self._api_calls_this_week(db)
        score = _clamp(min(api_calls, 100))
        checks.append(HealthCheck(
            category=cat,
            name="daily_active",
            score=score,
            status=_status(score),
            recommendation=(
                "Baja actividad esta semana. "
                "Explor\u00e1 el playground para descubrir nuevas funcionalidades."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        # features_used
        used, total_features = await self._features_usage(db)
        pct = (used / total_features * 100) if total_features else 0
        score = _clamp(pct)
        checks.append(HealthCheck(
            category=cat,
            name="features_used",
            score=score,
            status=_status(score),
            recommendation=(
                "Est\u00e1s usando pocas funcionalidades. "
                "Revis\u00e1 el onboarding para aprovechar todo el producto."
                if score < 75 else ""
            ),
            weight=weight,
        ))

        return checks

    # ------------------------------------------------------------------
    # Database query helpers (safe fallbacks on missing tables)
    # ------------------------------------------------------------------

    async def _safe_scalar(self, db: AsyncSession, query: str) -> int | float | None:
        """Execute a raw SQL scalar query, returning None on error."""
        try:
            result = await db.execute(text(query))
            val = result.scalar()
            return val if val is not None else 0
        except Exception:
            logger.debug("Health check query failed: %s", query, exc_info=True)
            return None

    async def _count_leads_field(
        self, db: AsyncSession, field_name: str
    ) -> tuple[int, int]:
        total = await self._safe_scalar(db, "SELECT COUNT(*) FROM leads") or 0
        with_field = await self._safe_scalar(
            db,
            f"SELECT COUNT(*) FROM leads WHERE {field_name} IS NOT NULL "
            f"AND {field_name} != ''",
        ) or 0
        return int(total), int(with_field)

    async def _total_leads(self, db: AsyncSession) -> int:
        val = await self._safe_scalar(db, "SELECT COUNT(*) FROM leads")
        return int(val) if val is not None else 0

    async def _pipeline_avg_days(self, db: AsyncSession) -> float | None:
        val = await self._safe_scalar(
            db,
            "SELECT AVG(JULIANDAY(updated_at) - JULIANDAY(created_at)) FROM leads "
            "WHERE status != 'new'",
        )
        return float(val) if val is not None else None

    async def _stale_leads_count(self, db: AsyncSession, days: int = 30) -> int:
        val = await self._safe_scalar(
            db,
            f"SELECT COUNT(*) FROM leads "
            f"WHERE updated_at < datetime('now', '-{days} days') "
            f"AND status NOT IN ('won', 'lost', 'archived')",
        )
        return int(val) if val is not None else 0

    async def _conversion_counts(self, db: AsyncSession) -> tuple[int, int]:
        total = await self._safe_scalar(db, "SELECT COUNT(*) FROM leads") or 0
        won = await self._safe_scalar(
            db, "SELECT COUNT(*) FROM leads WHERE status = 'won'"
        ) or 0
        return int(won), int(total)

    async def _hot_leads_actioned(self, db: AsyncSession) -> tuple[int, int]:
        hot = await self._safe_scalar(
            db, "SELECT COUNT(*) FROM leads WHERE classification = 'hot'"
        ) or 0
        contacted = await self._safe_scalar(
            db,
            "SELECT COUNT(*) FROM leads WHERE classification = 'hot' "
            "AND status NOT IN ('new', 'uncontacted')",
        ) or 0
        return int(hot), int(contacted)

    async def _sla_counts(self, db: AsyncSession) -> tuple[int, int]:
        total = await self._safe_scalar(db, "SELECT COUNT(*) FROM tickets") or 0
        within = await self._safe_scalar(
            db,
            "SELECT COUNT(*) FROM tickets WHERE sla_breached = 0 OR sla_breached IS NULL",
        ) or 0
        return int(total), int(within)

    async def _avg_resolution_hours(self, db: AsyncSession) -> float | None:
        val = await self._safe_scalar(
            db,
            "SELECT AVG((JULIANDAY(resolved_at) - JULIANDAY(created_at)) * 24) "
            "FROM tickets WHERE resolved_at IS NOT NULL",
        )
        return float(val) if val is not None else None

    async def _unassigned_ticket_count(self, db: AsyncSession) -> int:
        val = await self._safe_scalar(
            db,
            "SELECT COUNT(*) FROM tickets "
            "WHERE assigned_to IS NULL AND status != 'closed'",
        )
        return int(val) if val is not None else 0

    async def _response_rate(self, db: AsyncSession) -> tuple[int, int]:
        total = await self._safe_scalar(db, "SELECT COUNT(*) FROM tickets") or 0
        with_reply = await self._safe_scalar(
            db,
            "SELECT COUNT(DISTINCT ticket_id) FROM ticket_messages "
            "WHERE role = 'agent'",
        ) or 0
        return int(total), int(with_reply)

    async def _agents_active(self, db: AsyncSession) -> bool:
        val = await self._safe_scalar(
            db,
            "SELECT COUNT(*) FROM audit_log "
            "WHERE entity_type = 'agent_dispatch' "
            "AND created_at > datetime('now', '-30 days')",
        )
        return (val or 0) > 0

    async def _outreach_sent_count(self, db: AsyncSession) -> int:
        val = await self._safe_scalar(
            db,
            "SELECT COUNT(*) FROM outreach_messages "
            "WHERE created_at > datetime('now', '-30 days')",
        )
        return int(val) if val is not None else 0

    async def _auto_response_rate(self, db: AsyncSession) -> tuple[int, int]:
        total = await self._safe_scalar(db, "SELECT COUNT(*) FROM tickets") or 0
        auto = await self._safe_scalar(
            db,
            "SELECT COUNT(*) FROM tickets WHERE auto_responded = 1",
        ) or 0
        return int(total), int(auto)

    async def _has_custom_pipeline(self, db: AsyncSession) -> bool:
        val = await self._safe_scalar(
            db, "SELECT COUNT(*) FROM pipeline_stages WHERE is_custom = 1"
        )
        return (val or 0) > 0

    async def _has_custom_templates(self, db: AsyncSession) -> bool:
        val = await self._safe_scalar(
            db, "SELECT COUNT(*) FROM templates WHERE is_default = 0"
        )
        return (val or 0) > 0

    async def _has_integrations(self, db: AsyncSession) -> bool:
        val = await self._safe_scalar(
            db, "SELECT COUNT(*) FROM integrations WHERE active = 1"
        )
        return (val or 0) > 0

    async def _kb_article_count(self, db: AsyncSession) -> int:
        val = await self._safe_scalar(
            db, "SELECT COUNT(*) FROM knowledge_articles"
        )
        return int(val) if val is not None else 0

    async def _api_calls_this_week(self, db: AsyncSession) -> int:
        val = await self._safe_scalar(
            db,
            "SELECT COUNT(*) FROM audit_log "
            "WHERE created_at > datetime('now', '-7 days')",
        )
        return int(val) if val is not None else 0

    async def _features_usage(self, db: AsyncSession) -> tuple[int, int]:
        total_features = 12  # leads, tickets, knowledge, outreach, etc.
        val = await self._safe_scalar(
            db,
            "SELECT COUNT(DISTINCT entity_type) FROM audit_log "
            "WHERE created_at > datetime('now', '-30 days')",
        )
        used = int(val) if val is not None else 0
        return used, total_features
