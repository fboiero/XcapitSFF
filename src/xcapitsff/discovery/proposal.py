"""Generador de propuestas comerciales desde descubrimiento y requerimientos."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from .requirements import (
    EFFORT_HOURS,
    EffortSize,
    Requirement,
    RequirementsDocument,
    RequirementsGenerator,
)
from .session import DiscoverySession, _get_answer_text


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ProjectPhase:
    """Fase del plan de proyecto."""

    name: str
    description: str
    duration_weeks: int
    deliverables: list[str] = field(default_factory=list)
    milestones: str = ""


@dataclass
class Proposal:
    """Propuesta comercial completa."""

    proposal_id: str
    client_name: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executive_summary: str = ""
    scope: str = ""
    modules_included: list[str] = field(default_factory=list)
    timeline: str = ""
    investment: dict = field(default_factory=dict)
    phases: list[ProjectPhase] = field(default_factory=list)
    terms: str = ""


# ---------------------------------------------------------------------------
# Planes y precios
# ---------------------------------------------------------------------------

PLAN_PRICING: dict[str, dict] = {
    "free": {
        "name": "Plan Gratuito",
        "monthly_cost_usd": 0,
        "annual_cost_usd": 0,
        "max_users": 2,
        "max_leads": 100,
        "features": [
            "CRM básico",
            "Hasta 2 usuarios",
            "100 leads",
            "Dashboard básico",
            "Soporte por email",
        ],
    },
    "pro": {
        "name": "Plan Profesional",
        "monthly_cost_usd": 99,
        "annual_cost_usd": 79,
        "max_users": 10,
        "max_leads": 5000,
        "features": [
            "CRM completo",
            "Hasta 10 usuarios",
            "5.000 leads",
            "Dashboard avanzado",
            "Automatizaciones",
            "Integraciones",
            "Secuencias de outreach",
            "Analytics avanzado",
            "Soporte prioritario",
        ],
    },
    "enterprise": {
        "name": "Plan Enterprise",
        "monthly_cost_usd": 499,
        "annual_cost_usd": 399,
        "max_users": -1,  # ilimitado
        "max_leads": -1,
        "features": [
            "Todo lo del Plan Pro",
            "Usuarios ilimitados",
            "Leads ilimitados",
            "Agente IA dedicado",
            "SLA garantizado",
            "White label",
            "API completa",
            "Soporte 24/7",
            "Manager de cuenta dedicado",
        ],
    },
}


# ---------------------------------------------------------------------------
# Generador de propuestas
# ---------------------------------------------------------------------------


class ProposalGenerator:
    """Genera propuestas comerciales a partir del descubrimiento y requerimientos."""

    def generate_proposal(
        self, session: DiscoverySession, requirements: RequirementsDocument
    ) -> Proposal:
        """Genera una propuesta comercial completa."""
        proposal_id = uuid.uuid4().hex[:16]
        recommended_plan = self.estimate_plan(requirements)
        plan_info = PLAN_PRICING[recommended_plan]

        executive_summary = self._build_executive_summary(session, requirements)
        scope = self._build_scope(requirements)
        modules = [r.module for r in requirements.requirements if r.module]
        modules = sorted(set(modules))
        phases = self._build_phases(requirements, recommended_plan)
        timeline = self._build_timeline(phases)
        investment = self._build_investment(recommended_plan, phases)
        terms = self._build_terms()

        return Proposal(
            proposal_id=proposal_id,
            client_name=session.client_name,
            executive_summary=executive_summary,
            scope=scope,
            modules_included=modules,
            timeline=timeline,
            investment=investment,
            phases=phases,
            terms=terms,
        )

    def estimate_plan(self, requirements: RequirementsDocument) -> str:
        """Recomienda qué plan de precios se ajusta según los requerimientos."""
        total_reqs = len(requirements.requirements) + len(requirements.non_functional)
        has_integrations = any(
            "integra" in r.description.lower() for r in requirements.requirements
        )
        has_security = any(
            r.module == "security" for r in requirements.non_functional
        )
        has_mobile = any(
            "mobile" in r.title.lower() or "móvil" in r.title.lower()
            for r in requirements.non_functional
        )

        # Lógica de recomendación
        score = 0

        if total_reqs > 10:
            score += 3
        elif total_reqs > 5:
            score += 2
        else:
            score += 1

        if has_integrations:
            score += 2
        if has_security:
            score += 2
        if has_mobile:
            score += 1

        if len(requirements.user_stories) > 5:
            score += 1

        if score >= 7:
            return "enterprise"
        elif score >= 3:
            return "pro"
        else:
            return "free"

    def _build_executive_summary(
        self, session: DiscoverySession, requirements: RequirementsDocument
    ) -> str:
        """Construye el resumen ejecutivo de la propuesta."""
        company = session.client_name
        industry = session.industry or _get_answer_text(session, "intro_02") or "tecnología"
        problem = _get_answer_text(session, "prob_01") or "optimizar sus procesos"
        impact = _get_answer_text(session, "prob_03") or "mejora operativa"

        total_reqs = len(requirements.requirements)
        total_stories = len(requirements.user_stories)

        return (
            f"Propuesta de desarrollo de software para {company}, empresa del sector "
            f"{industry}. El proyecto busca {problem}, abordando el impacto actual: "
            f"{impact}. La solución contempla {total_reqs} requerimientos funcionales "
            f"y {total_stories} historias de usuario, implementados sobre la plataforma "
            f"XcapitSFF."
        )

    def _build_scope(self, requirements: RequirementsDocument) -> str:
        """Construye la definición de alcance."""
        sections: list[str] = []

        if requirements.requirements:
            sections.append("Requerimientos funcionales:")
            for req in requirements.requirements:
                sections.append(f"  - {req.title}: {req.description}")

        if requirements.non_functional:
            sections.append("\nRequerimientos no funcionales:")
            for req in requirements.non_functional:
                sections.append(f"  - {req.title}: {req.description}")

        if requirements.constraints:
            sections.append("\nRestricciones:")
            for c in requirements.constraints:
                sections.append(f"  - {c}")

        if requirements.assumptions:
            sections.append("\nSupuestos:")
            for a in requirements.assumptions:
                sections.append(f"  - {a}")

        if requirements.out_of_scope:
            sections.append("\nFuera de alcance:")
            for o in requirements.out_of_scope:
                sections.append(f"  - {o}")

        return "\n".join(sections)

    def _build_phases(
        self, requirements: RequirementsDocument, plan: str
    ) -> list[ProjectPhase]:
        """Construye las fases del proyecto."""
        phases: list[ProjectPhase] = []

        # Fase 1: Descubrimiento y Diseño
        phases.append(
            ProjectPhase(
                name="Fase 1: Descubrimiento y Diseño",
                description=(
                    "Relevamiento detallado, diseño de arquitectura y "
                    "wireframes de la solución."
                ),
                duration_weeks=2,
                deliverables=[
                    "Documento de arquitectura",
                    "Wireframes / mockups",
                    "Plan de proyecto detallado",
                    "Definición de sprints",
                ],
                milestones="Aprobación del diseño por parte del cliente",
            )
        )

        # Fase 2: MVP / Desarrollo Core
        must_reqs = [r for r in requirements.requirements if r.priority.value == "must"]
        mvp_duration = max(4, len(must_reqs) * 2)  # mínimo 4 semanas
        if mvp_duration > 12:
            mvp_duration = 12

        phases.append(
            ProjectPhase(
                name="Fase 2: Desarrollo MVP",
                description=(
                    "Desarrollo de funcionalidades core y requerimientos "
                    "priorizados como MUST."
                ),
                duration_weeks=mvp_duration,
                deliverables=[
                    "MVP funcional desplegado",
                    "Requerimientos MUST implementados",
                    "Tests automatizados",
                    "Documentación técnica",
                ],
                milestones="Demo de MVP al cliente y aprobación para continuar",
            )
        )

        # Fase 3: Iteración y mejoras
        should_reqs = [r for r in requirements.requirements if r.priority.value == "should"]
        if should_reqs:
            iter_duration = max(3, len(should_reqs) * 2)
            if iter_duration > 8:
                iter_duration = 8

            phases.append(
                ProjectPhase(
                    name="Fase 3: Iteración y Mejoras",
                    description=(
                        "Desarrollo de funcionalidades SHOULD y mejoras "
                        "basadas en feedback del MVP."
                    ),
                    duration_weeks=iter_duration,
                    deliverables=[
                        "Funcionalidades SHOULD implementadas",
                        "Mejoras de UX basadas en feedback",
                        "Integraciones completadas",
                    ],
                    milestones="Release de versión completa",
                )
            )

        # Fase 4: QA y Lanzamiento
        phases.append(
            ProjectPhase(
                name="Fase 4: QA y Lanzamiento",
                description=(
                    "Testing integral, corrección de bugs, "
                    "deployment a producción y capacitación."
                ),
                duration_weeks=2,
                deliverables=[
                    "Testing completo (funcional, carga, seguridad)",
                    "Deployment a producción",
                    "Documentación de usuario",
                    "Capacitación del equipo",
                    "Plan de soporte post-lanzamiento",
                ],
                milestones="Go-live en producción",
            )
        )

        return phases

    def _build_timeline(self, phases: list[ProjectPhase]) -> str:
        """Construye la línea de tiempo resumida."""
        total_weeks = sum(p.duration_weeks for p in phases)
        total_months = round(total_weeks / 4, 1)

        lines: list[str] = [
            f"Duración total estimada: {total_weeks} semanas ({total_months} meses)",
            "",
        ]

        week_start = 1
        for phase in phases:
            week_end = week_start + phase.duration_weeks - 1
            lines.append(
                f"  {phase.name}: Semanas {week_start}-{week_end} "
                f"({phase.duration_weeks} semanas)"
            )
            week_start = week_end + 1

        return "\n".join(lines)

    def _build_investment(self, plan: str, phases: list[ProjectPhase]) -> dict:
        """Construye el detalle de inversión."""
        plan_info = PLAN_PRICING[plan]
        total_weeks = sum(p.duration_weeks for p in phases)

        # Costo de desarrollo (estimado por semana)
        dev_rate_per_week = 2500  # USD por semana por equipo
        development_cost = total_weeks * dev_rate_per_week

        return {
            "plan": plan_info["name"],
            "monthly_subscription_usd": plan_info["monthly_cost_usd"],
            "annual_subscription_usd": plan_info["annual_cost_usd"],
            "development_cost_usd": development_cost,
            "total_project_cost_usd": development_cost,
            "ongoing_monthly_cost_usd": plan_info["monthly_cost_usd"],
            "total_weeks": total_weeks,
            "currency": "USD",
            "payment_terms": "50% al inicio, 25% en hito intermedio, 25% al cierre",
        }

    def _build_terms(self) -> str:
        """Construye los términos y condiciones estándar."""
        return (
            "TÉRMINOS Y CONDICIONES\n"
            "\n"
            "1. ALCANCE: El proyecto se limita a lo descrito en esta propuesta. "
            "Cambios de alcance serán evaluados y presupuestados por separado.\n"
            "\n"
            "2. PAGOS: Según el esquema de pagos detallado en la sección de inversión. "
            "Los pagos se realizan contra entrega de hitos.\n"
            "\n"
            "3. PLAZOS: Los plazos son estimados y pueden variar según la "
            "disponibilidad del cliente para validaciones y feedback.\n"
            "\n"
            "4. PROPIEDAD INTELECTUAL: El código desarrollado específicamente para "
            "el cliente es de su propiedad. Los módulos base de XcapitSFF se "
            "licencian según el plan contratado.\n"
            "\n"
            "5. GARANTÍA: Se incluyen 30 días de garantía post-lanzamiento para "
            "corrección de bugs.\n"
            "\n"
            "6. SOPORTE: El soporte post-lanzamiento se incluye según el plan "
            "contratado (email, prioritario o 24/7).\n"
            "\n"
            "7. CONFIDENCIALIDAD: Ambas partes se comprometen a mantener la "
            "confidencialidad de la información compartida durante el proyecto.\n"
            "\n"
            "8. VALIDEZ: Esta propuesta tiene una validez de 30 días desde su "
            "fecha de emisión."
        )

    # -- Renderizado --

    def to_markdown(self, proposal: Proposal) -> str:
        """Renderiza la propuesta como documento Markdown."""
        lines: list[str] = []

        lines.append(f"# Propuesta Comercial — {proposal.client_name}")
        lines.append("")
        lines.append(
            f"**Fecha:** {proposal.created_at.strftime('%d/%m/%Y')}"
        )
        lines.append(f"**ID:** {proposal.proposal_id}")
        lines.append("")

        # Resumen ejecutivo
        lines.append("## Resumen Ejecutivo")
        lines.append("")
        lines.append(proposal.executive_summary)
        lines.append("")

        # Alcance
        lines.append("## Alcance del Proyecto")
        lines.append("")
        lines.append(proposal.scope)
        lines.append("")

        # Módulos
        if proposal.modules_included:
            lines.append("## Módulos Incluidos")
            lines.append("")
            for mod in proposal.modules_included:
                lines.append(f"- {mod}")
            lines.append("")

        # Fases
        lines.append("## Plan de Implementación")
        lines.append("")
        for phase in proposal.phases:
            lines.append(f"### {phase.name}")
            lines.append("")
            lines.append(phase.description)
            lines.append("")
            lines.append(f"**Duración:** {phase.duration_weeks} semanas")
            lines.append("")
            lines.append("**Entregables:**")
            for d in phase.deliverables:
                lines.append(f"- {d}")
            lines.append("")
            lines.append(f"**Hito:** {phase.milestones}")
            lines.append("")

        # Timeline
        lines.append("## Cronograma")
        lines.append("")
        lines.append(proposal.timeline)
        lines.append("")

        # Inversión
        lines.append("## Inversión")
        lines.append("")
        inv = proposal.investment
        lines.append(f"| Concepto | Valor |")
        lines.append(f"|---|---|")
        lines.append(f"| Plan recomendado | {inv.get('plan', '')} |")
        lines.append(
            f"| Suscripción mensual | USD {inv.get('monthly_subscription_usd', 0)}/mes |"
        )
        lines.append(
            f"| Costo de desarrollo | USD {inv.get('development_cost_usd', 0)} |"
        )
        lines.append(
            f"| Duración del proyecto | {inv.get('total_weeks', 0)} semanas |"
        )
        lines.append(
            f"| Condiciones de pago | {inv.get('payment_terms', '')} |"
        )
        lines.append("")

        # Términos
        lines.append("## Términos y Condiciones")
        lines.append("")
        lines.append(proposal.terms)
        lines.append("")

        # Firma
        lines.append("---")
        lines.append("")
        lines.append("**XcapitSFF — Software Factory**")
        lines.append("")
        lines.append("_Esta propuesta fue generada automáticamente por el sistema "
                      "de descubrimiento de XcapitSFF._")

        return "\n".join(lines)
