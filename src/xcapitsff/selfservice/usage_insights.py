"""Usage analytics — weekly insights, daily digests, and feature adoption.

Generates actionable, Spanish-language insights for each tenant so teams
can understand how they are using the product and where to improve.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class UsageInsight:
    insight_type: str
    title: str
    description: str
    value: float
    trend: str  # "up" | "down" | "stable"
    recommendation: str


# ---------------------------------------------------------------------------
# Feature catalogue — used for adoption tracking
# ---------------------------------------------------------------------------

ALL_FEATURES: list[str] = [
    "leads",
    "tickets",
    "outreach",
    "knowledge_base",
    "campaigns",
    "sequences",
    "reports",
    "automations",
    "agents",
    "meetings",
    "templates",
    "playground",
    "workflows",
    "enrichment",
    "dashboard",
]


# ---------------------------------------------------------------------------
# Usage Insights Engine
# ---------------------------------------------------------------------------


class UsageInsightsEngine:
    """Generates per-tenant usage insights from in-memory stats.

    In production the data would come from the database / analytics store;
    this implementation works with a simple dict-based data layer so
    callers can inject tenant metrics directly.
    """

    def __init__(self) -> None:
        # tenant_id -> metrics dict
        self._tenant_data: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Data injection helpers
    # ------------------------------------------------------------------

    def set_tenant_data(self, tenant_id: str, data: dict) -> None:
        """Inject / update raw metrics for a tenant."""
        self._tenant_data[tenant_id] = data

    def _get(self, tenant_id: str) -> dict:
        return self._tenant_data.get(tenant_id, {})

    # ------------------------------------------------------------------
    # Weekly insights
    # ------------------------------------------------------------------

    def generate_weekly_insights(self, tenant_id: str) -> list[UsageInsight]:
        """Generate a list of weekly insights for *tenant_id*.

        Expected keys in tenant data::

            leads_this_week, leads_last_week,
            avg_resolution_hours_this_week, avg_resolution_hours_last_week,
            hot_leads_uncontacted,
            csat_this_week,
            feature_most_used, feature_least_used
        """
        data = self._get(tenant_id)
        insights: list[UsageInsight] = []

        # 1 — Leads qualified
        leads_tw = data.get("leads_this_week", 0)
        leads_lw = data.get("leads_last_week", 0)
        if leads_lw > 0:
            pct_change = round(((leads_tw - leads_lw) / leads_lw) * 100, 1)
        else:
            pct_change = 100.0 if leads_tw > 0 else 0.0

        trend = "up" if pct_change > 0 else ("down" if pct_change < 0 else "stable")
        direction = "más" if pct_change >= 0 else "menos"

        insights.append(UsageInsight(
            insight_type="leads_qualified",
            title="Leads calificados",
            description=(
                f"Tu equipo calificó {leads_tw} leads esta semana, "
                f"{abs(pct_change)}% {direction} que la anterior"
            ),
            value=leads_tw,
            trend=trend,
            recommendation=(
                "Seguí así, la tendencia es positiva."
                if trend == "up"
                else "Revisá la generación de leads para mantener el ritmo."
            ),
        ))

        # 2 — Resolution time
        res_tw = data.get("avg_resolution_hours_this_week", 0)
        res_lw = data.get("avg_resolution_hours_last_week", 0)
        if res_lw > 0:
            res_change = round(((res_tw - res_lw) / res_lw) * 100, 1)
        else:
            res_change = 0.0

        # Lower is better, so "improvement" is negative change
        improved = res_change < 0
        trend = "up" if improved else ("down" if res_change > 0 else "stable")
        verb = "mejoró" if improved else ("empeoró" if res_change > 0 else "se mantuvo")

        insights.append(UsageInsight(
            insight_type="resolution_time",
            title="Tiempo de resolución",
            description=(
                f"El tiempo promedio de resolución {verb} {abs(res_change)}%"
            ),
            value=res_tw,
            trend=trend,
            recommendation=(
                "Excelente, seguí optimizando los tiempos."
                if improved
                else "Considerá respuestas automáticas para tickets frecuentes."
            ),
        ))

        # 3 — Hot leads uncontacted
        hot_uncontacted = data.get("hot_leads_uncontacted", 0)
        insights.append(UsageInsight(
            insight_type="hot_leads_uncontacted",
            title="Leads hot sin contactar",
            description=(
                f"Tenés {hot_uncontacted} leads hot sin contactar — ¡no los pierdas!"
                if hot_uncontacted > 0
                else "Todos tus leads hot fueron contactados. ¡Excelente!"
            ),
            value=hot_uncontacted,
            trend="down" if hot_uncontacted > 0 else "stable",
            recommendation=(
                "Priorizá el contacto con estos leads antes de que se enfríen."
                if hot_uncontacted > 0
                else ""
            ),
        ))

        # 4 — CSAT
        csat = data.get("csat_this_week", 0.0)
        csat_analysis = (
            "Excelente — tus clientes están muy satisfechos."
            if csat >= 4.5
            else (
                "Buen nivel, pero hay margen de mejora."
                if csat >= 3.5
                else "Necesitás mejorar la satisfacción del cliente."
            )
        )
        insights.append(UsageInsight(
            insight_type="csat_weekly",
            title="CSAT semanal",
            description=f"Tu CSAT esta semana es {csat} — {csat_analysis}",
            value=csat,
            trend="up" if csat >= 4.5 else ("stable" if csat >= 3.5 else "down"),
            recommendation=(
                "Mantené el nivel de atención."
                if csat >= 4.5
                else "Revisá los tickets con baja calificación para detectar patrones."
            ),
        ))

        # 5 — Feature usage
        most_used = data.get("feature_most_used", "N/A")
        least_used = data.get("feature_least_used", "N/A")
        insights.append(UsageInsight(
            insight_type="feature_usage",
            title="Uso de features",
            description=(
                f"Feature más usada: {most_used}. Feature sin usar: {least_used}"
            ),
            value=0,
            trend="stable",
            recommendation=(
                f"Explorá '{least_used}' para sacar más provecho de la plataforma."
                if least_used != "N/A"
                else ""
            ),
        ))

        return insights

    # ------------------------------------------------------------------
    # Daily digest
    # ------------------------------------------------------------------

    def generate_daily_digest(self, tenant_id: str) -> dict:
        """Return a compact daily digest for *tenant_id*.

        Expected keys::

            new_leads_today, tickets_resolved_today, outreach_sent_today,
            meetings_scheduled_today, key_actions_needed (list[str])
        """
        data = self._get(tenant_id)

        return {
            "tenant_id": tenant_id,
            "date": date.today().isoformat(),
            "new_leads": data.get("new_leads_today", 0),
            "tickets_resolved": data.get("tickets_resolved_today", 0),
            "outreach_sent": data.get("outreach_sent_today", 0),
            "meetings_scheduled": data.get("meetings_scheduled_today", 0),
            "key_actions_needed": data.get("key_actions_needed", []),
        }

    # ------------------------------------------------------------------
    # Feature adoption
    # ------------------------------------------------------------------

    def get_feature_adoption(self, tenant_id: str) -> dict:
        """Return feature adoption data for *tenant_id*.

        Expected key in tenant data::

            feature_usage: {feature_name: {"usage_count": int, "last_used": str|None}}
        """
        data = self._get(tenant_id)
        raw_usage: dict = data.get("feature_usage", {})

        adoption: dict = {}
        for feature in ALL_FEATURES:
            info = raw_usage.get(feature, {})
            usage_count = info.get("usage_count", 0)
            last_used_raw = info.get("last_used")

            if isinstance(last_used_raw, str):
                try:
                    last_used = date.fromisoformat(last_used_raw)
                except ValueError:
                    last_used = None
            elif isinstance(last_used_raw, (date, datetime)):
                last_used = (
                    last_used_raw.date()
                    if isinstance(last_used_raw, datetime)
                    else last_used_raw
                )
            else:
                last_used = None

            adoption[feature] = {
                "used": usage_count > 0,
                "usage_count": usage_count,
                "last_used": last_used.isoformat() if last_used else None,
            }

        return adoption
