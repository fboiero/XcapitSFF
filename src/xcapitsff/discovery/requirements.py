"""Generador de requerimientos a partir de sesiones de descubrimiento."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from .session import (
    DiscoveryAnswer,
    DiscoveryPhase,
    DiscoverySession,
    QUESTION_INDEX,
    SessionStatus,
    _get_answer_text,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RequirementType(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"


class Priority(str, Enum):
    """Priorización MoSCoW."""

    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"


class EffortSize(str, Enum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Requirement:
    """Requerimiento del proyecto."""

    req_id: str
    title: str
    description: str
    type: RequirementType = RequirementType.FUNCTIONAL
    priority: Priority = Priority.SHOULD
    module: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    estimated_effort: EffortSize = EffortSize.M


@dataclass
class UserStory:
    """Historia de usuario."""

    story_id: str
    as_a: str  # rol
    i_want: str  # acción
    so_that: str  # beneficio
    acceptance_criteria: list[str] = field(default_factory=list)
    priority: Priority = Priority.SHOULD
    estimated_points: int = 3


@dataclass
class RequirementsDocument:
    """Documento de requerimientos completo."""

    doc_id: str
    client_name: str
    session_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    requirements: list[Requirement] = field(default_factory=list)
    user_stories: list[UserStory] = field(default_factory=list)
    non_functional: list[Requirement] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Mapeo de esfuerzo a horas
# ---------------------------------------------------------------------------

EFFORT_HOURS: dict[EffortSize, int] = {
    EffortSize.XS: 4,
    EffortSize.S: 16,
    EffortSize.M: 40,
    EffortSize.L: 80,
    EffortSize.XL: 160,
}

# ---------------------------------------------------------------------------
# Módulos disponibles del sistema XcapitSFF
# ---------------------------------------------------------------------------

AVAILABLE_MODULES: list[str] = [
    "crm",
    "leads",
    "tickets",
    "analytics",
    "automation",
    "outreach",
    "billing",
    "knowledge_base",
    "dashboard",
    "notifications",
    "campaigns",
    "enrichment",
    "predictions",
    "sequences",
    "ab_testing",
    "search",
    "reports",
    "webhooks",
    "agents",
]


# ---------------------------------------------------------------------------
# Generador de requerimientos
# ---------------------------------------------------------------------------


def _get_answers_for_phase(
    session: DiscoverySession, phase: DiscoveryPhase
) -> list[DiscoveryAnswer]:
    """Devuelve todas las respuestas de una fase."""
    return [a for a in session.answers if a.phase == phase]


class RequirementsGenerator:
    """Genera documentos de requerimientos desde sesiones de descubrimiento."""

    def generate_from_discovery(self, session: DiscoverySession) -> RequirementsDocument:
        """Genera un documento de requerimientos completo a partir del descubrimiento."""
        doc_id = uuid.uuid4().hex[:16]

        functional_reqs = self._generate_functional_requirements(session)
        nf_reqs = self._generate_non_functional_requirements(session)
        stories = self.generate_user_stories(session)
        constraints = self._generate_constraints(session)
        assumptions = self._generate_assumptions(session)
        out_of_scope = self._generate_out_of_scope(session)

        return RequirementsDocument(
            doc_id=doc_id,
            client_name=session.client_name,
            session_id=session.session_id,
            requirements=functional_reqs,
            user_stories=stories,
            non_functional=nf_reqs,
            constraints=constraints,
            assumptions=assumptions,
            out_of_scope=out_of_scope,
        )

    # -- Requerimientos funcionales --

    def _generate_functional_requirements(
        self, session: DiscoverySession
    ) -> list[Requirement]:
        """Genera requerimientos funcionales del problema, workflow y pain points."""
        reqs: list[Requirement] = []
        req_counter = 1

        # Desde el problema principal
        problem = _get_answer_text(session, "prob_01")
        if problem:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Resolución del problema principal",
                    description=f"El sistema debe resolver: {problem}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.MUST,
                    module="core",
                    acceptance_criteria=[
                        "El problema principal del cliente queda resuelto",
                        "El usuario puede completar el flujo sin intervención manual",
                    ],
                    estimated_effort=EffortSize.L,
                )
            )
            req_counter += 1

        # Desde la solución actual
        current_solution = _get_answer_text(session, "prob_02")
        if current_solution:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Migración desde solución actual",
                    description=f"Reemplazar la solución actual: {current_solution}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.MUST,
                    module="core",
                    acceptance_criteria=[
                        "Funcionalidad equivalente o superior a la solución actual",
                        "Plan de migración de datos documentado",
                    ],
                    estimated_effort=EffortSize.M,
                )
            )
            req_counter += 1

        # Desde automatización
        automation = _get_answer_text(session, "flow_03")
        if automation:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Automatización de procesos manuales",
                    description=f"Automatizar: {automation}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.MUST,
                    module="automation",
                    acceptance_criteria=[
                        "Los procesos manuales identificados se automatizan",
                        "Reducción medible del tiempo dedicado a tareas manuales",
                    ],
                    estimated_effort=EffortSize.L,
                )
            )
            req_counter += 1

        # Desde integraciones
        integrations = _get_answer_text(session, "flow_04")
        if integrations:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Integraciones con sistemas externos",
                    description=f"Integrar con: {integrations}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.SHOULD,
                    module="webhooks",
                    acceptance_criteria=[
                        "Integración bidireccional funcionando",
                        "Datos sincronizados en tiempo real o near-real-time",
                    ],
                    estimated_effort=EffortSize.L,
                )
            )
            req_counter += 1

        # Desde pain points
        pain_points = _get_answer_text(session, "pain_01")
        if pain_points:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Eliminación de puntos de dolor principales",
                    description=f"Resolver los siguientes dolores: {pain_points}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.MUST,
                    module="core",
                    acceptance_criteria=[
                        "Cada punto de dolor tiene una solución implementada",
                        "Los usuarios confirman que el dolor se resolvió",
                    ],
                    estimated_effort=EffortSize.L,
                )
            )
            req_counter += 1

        # Desde errores y pérdida de datos
        data_errors = _get_answer_text(session, "pain_03")
        if data_errors:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Prevención de errores y pérdida de datos",
                    description=f"Eliminar errores en: {data_errors}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.MUST,
                    module="data_quality",
                    acceptance_criteria=[
                        "Validaciones implementadas para prevenir errores",
                        "Trazabilidad de datos completa",
                        "Tasa de error reducida a menos del 1%",
                    ],
                    estimated_effort=EffortSize.M,
                )
            )
            req_counter += 1

        # Desde herramientas actuales
        tools = _get_answer_text(session, "flow_02")
        if tools:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Consolidación de herramientas",
                    description=f"Unificar funcionalidades de: {tools}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.SHOULD,
                    module="dashboard",
                    acceptance_criteria=[
                        "Una interfaz unificada reemplaza múltiples herramientas",
                        "No hay pérdida de funcionalidad",
                    ],
                    estimated_effort=EffortSize.L,
                )
            )
            req_counter += 1

        # Desde workflow
        workflow = _get_answer_text(session, "flow_01")
        if workflow:
            reqs.append(
                Requirement(
                    req_id=f"REQ-F-{req_counter:03d}",
                    title="Digitalización del flujo de trabajo",
                    description=f"Digitalizar el proceso: {workflow}",
                    type=RequirementType.FUNCTIONAL,
                    priority=Priority.MUST,
                    module="automation",
                    acceptance_criteria=[
                        "Todo el flujo de trabajo es digital",
                        "Seguimiento en tiempo real del estado de cada paso",
                    ],
                    estimated_effort=EffortSize.XL,
                )
            )
            req_counter += 1

        return reqs

    # -- Requerimientos no funcionales --

    def _generate_non_functional_requirements(
        self, session: DiscoverySession
    ) -> list[Requirement]:
        """Genera requerimientos no funcionales del contexto técnico y criterios."""
        nf_reqs: list[Requirement] = []
        nf_counter = 1

        # Plataforma (mobile/web)
        platform = _get_answer_text(session, "tech_03")
        if platform:
            platform_lower = platform.lower()
            if "mobile" in platform_lower or "ambos" in platform_lower:
                nf_reqs.append(
                    Requirement(
                        req_id=f"REQ-NF-{nf_counter:03d}",
                        title="Compatibilidad mobile",
                        description="El sistema debe ser accesible desde dispositivos móviles",
                        type=RequirementType.NON_FUNCTIONAL,
                        priority=Priority.MUST,
                        module="frontend",
                        acceptance_criteria=[
                            "Interfaz responsive que funciona en móviles",
                            "Compatible con iOS y Android",
                        ],
                        estimated_effort=EffortSize.L,
                    )
                )
                nf_counter += 1

            if "web" in platform_lower or "ambos" in platform_lower:
                nf_reqs.append(
                    Requirement(
                        req_id=f"REQ-NF-{nf_counter:03d}",
                        title="Aplicación web",
                        description="El sistema debe funcionar como aplicación web",
                        type=RequirementType.NON_FUNCTIONAL,
                        priority=Priority.MUST,
                        module="frontend",
                        acceptance_criteria=[
                            "Compatible con Chrome, Firefox, Safari, Edge",
                            "Tiempo de carga menor a 3 segundos",
                        ],
                        estimated_effort=EffortSize.M,
                    )
                )
                nf_counter += 1

        # Seguridad
        security = _get_answer_text(session, "tech_04")
        if security:
            nf_reqs.append(
                Requirement(
                    req_id=f"REQ-NF-{nf_counter:03d}",
                    title="Requisitos de seguridad y compliance",
                    description=f"Cumplir con: {security}",
                    type=RequirementType.NON_FUNCTIONAL,
                    priority=Priority.MUST,
                    module="security",
                    acceptance_criteria=[
                        "Auditoría de seguridad aprobada",
                        "Documentación de compliance actualizada",
                    ],
                    estimated_effort=EffortSize.L,
                )
            )
            nf_counter += 1

        # KPIs como requerimientos de rendimiento
        kpis = _get_answer_text(session, "success_02")
        if kpis:
            nf_reqs.append(
                Requirement(
                    req_id=f"REQ-NF-{nf_counter:03d}",
                    title="Métricas y reportes de KPIs",
                    description=f"El sistema debe medir y reportar: {kpis}",
                    type=RequirementType.NON_FUNCTIONAL,
                    priority=Priority.SHOULD,
                    module="analytics",
                    acceptance_criteria=[
                        "Dashboard con KPIs en tiempo real",
                        "Reportes exportables",
                    ],
                    estimated_effort=EffortSize.M,
                )
            )
            nf_counter += 1

        # Número de usuarios (escalabilidad)
        user_count = _get_answer_text(session, "user_02")
        if user_count:
            nf_reqs.append(
                Requirement(
                    req_id=f"REQ-NF-{nf_counter:03d}",
                    title="Escalabilidad de usuarios",
                    description=f"Soportar la cantidad de usuarios: {user_count}",
                    type=RequirementType.NON_FUNCTIONAL,
                    priority=Priority.MUST,
                    module="infrastructure",
                    acceptance_criteria=[
                        "El sistema soporta la carga de usuarios simultáneos",
                        "Tiempo de respuesta menor a 2 segundos bajo carga",
                    ],
                    estimated_effort=EffortSize.M,
                )
            )
            nf_counter += 1

        # Nivel técnico de usuarios (usabilidad)
        tech_level = _get_answer_text(session, "user_03")
        if tech_level:
            level_lower = tech_level.lower()
            if "básico" in level_lower or "basico" in level_lower:
                nf_reqs.append(
                    Requirement(
                        req_id=f"REQ-NF-{nf_counter:03d}",
                        title="Usabilidad para usuarios no técnicos",
                        description="Interfaz intuitiva para usuarios con nivel técnico básico",
                        type=RequirementType.NON_FUNCTIONAL,
                        priority=Priority.MUST,
                        module="frontend",
                        acceptance_criteria=[
                            "Onboarding guiado para nuevos usuarios",
                            "Ayuda contextual en toda la aplicación",
                            "Test de usabilidad aprobado con usuarios reales",
                        ],
                        estimated_effort=EffortSize.M,
                    )
                )
                nf_counter += 1

        return nf_reqs

    # -- Historias de usuario --

    def generate_user_stories(self, session: DiscoverySession) -> list[UserStory]:
        """Genera historias de usuario desde personas y workflow."""
        stories: list[UserStory] = []
        story_counter = 1

        # Tipos de usuario
        user_types = _get_answer_text(session, "user_01")
        roles = ["usuario"]
        if user_types:
            # Intentar parsear la lista de roles
            roles = [r.strip() for r in user_types.replace(",", "\n").split("\n") if r.strip()]
            if not roles:
                roles = ["usuario"]

        primary_role = roles[0]

        # Historia base: resolver problema principal
        problem = _get_answer_text(session, "prob_01")
        if problem:
            stories.append(
                UserStory(
                    story_id=f"US-{story_counter:03d}",
                    as_a=primary_role,
                    i_want=f"resolver {problem}",
                    so_that="pueda trabajar de forma más eficiente",
                    acceptance_criteria=[
                        "El problema principal queda resuelto",
                        "El flujo es intuitivo y rápido",
                    ],
                    priority=Priority.MUST,
                    estimated_points=8,
                )
            )
            story_counter += 1

        # Historia: automatización
        automation = _get_answer_text(session, "flow_03")
        if automation:
            stories.append(
                UserStory(
                    story_id=f"US-{story_counter:03d}",
                    as_a=primary_role,
                    i_want=f"automatizar {automation}",
                    so_that="no tenga que hacerlo manualmente y ahorre tiempo",
                    acceptance_criteria=[
                        "El proceso se ejecuta automáticamente",
                        "Se pueden configurar reglas de automatización",
                    ],
                    priority=Priority.MUST,
                    estimated_points=5,
                )
            )
            story_counter += 1

        # Historia: visualización de datos
        kpis = _get_answer_text(session, "success_02")
        if kpis:
            stories.append(
                UserStory(
                    story_id=f"US-{story_counter:03d}",
                    as_a=primary_role,
                    i_want=f"ver un dashboard con los KPIs: {kpis}",
                    so_that="pueda tomar decisiones basadas en datos",
                    acceptance_criteria=[
                        "Dashboard con métricas en tiempo real",
                        "Filtros por período y segmento",
                    ],
                    priority=Priority.SHOULD,
                    estimated_points=5,
                )
            )
            story_counter += 1

        # Historias por cada rol adicional
        for role in roles[1:]:
            stories.append(
                UserStory(
                    story_id=f"US-{story_counter:03d}",
                    as_a=role,
                    i_want="acceder al sistema con permisos adecuados a mi rol",
                    so_that="pueda realizar mis tareas sin acceder a funciones que no me corresponden",
                    acceptance_criteria=[
                        f"El rol '{role}' tiene permisos específicos",
                        "El acceso se controla por roles",
                    ],
                    priority=Priority.MUST,
                    estimated_points=3,
                )
            )
            story_counter += 1

        # Historia: workflow digital
        workflow = _get_answer_text(session, "flow_01")
        if workflow:
            stories.append(
                UserStory(
                    story_id=f"US-{story_counter:03d}",
                    as_a=primary_role,
                    i_want="seguir el proceso de trabajo paso a paso en el sistema",
                    so_that="tenga visibilidad del estado de cada tarea",
                    acceptance_criteria=[
                        "Cada paso del proceso tiene un estado visible",
                        "Se pueden asignar responsables a cada paso",
                    ],
                    priority=Priority.MUST,
                    estimated_points=8,
                )
            )
            story_counter += 1

        # Historia: integraciones
        integrations = _get_answer_text(session, "flow_04")
        if integrations:
            stories.append(
                UserStory(
                    story_id=f"US-{story_counter:03d}",
                    as_a=primary_role,
                    i_want=f"que el sistema se integre con {integrations}",
                    so_that="no tenga que duplicar trabajo entre sistemas",
                    acceptance_criteria=[
                        "Los datos se sincronizan automáticamente",
                        "Se notifica cuando hay errores de sincronización",
                    ],
                    priority=Priority.SHOULD,
                    estimated_points=5,
                )
            )
            story_counter += 1

        # Historia: prevención de errores
        data_errors = _get_answer_text(session, "pain_03")
        if data_errors:
            stories.append(
                UserStory(
                    story_id=f"US-{story_counter:03d}",
                    as_a=primary_role,
                    i_want="que el sistema valide los datos y prevenga errores",
                    so_that="no se pierda información ni se cometan errores",
                    acceptance_criteria=[
                        "Validaciones en todos los formularios",
                        "Mensajes de error claros y accionables",
                    ],
                    priority=Priority.MUST,
                    estimated_points=3,
                )
            )
            story_counter += 1

        return stories

    # -- Constraints --

    def _generate_constraints(self, session: DiscoverySession) -> list[str]:
        """Genera restricciones del proyecto."""
        constraints: list[str] = []

        budget = _get_answer_text(session, "budget_01")
        if budget:
            constraints.append(f"Presupuesto: {budget}")

        deadline = _get_answer_text(session, "budget_03")
        if deadline:
            constraints.append(f"Fecha límite: {deadline}")

        tech_restrictions = _get_answer_text(session, "tech_02")
        if tech_restrictions:
            constraints.append(f"Restricciones tecnológicas: {tech_restrictions}")

        security = _get_answer_text(session, "tech_04")
        if security:
            constraints.append(f"Compliance/Seguridad: {security}")

        dev_approach = _get_answer_text(session, "budget_04")
        if dev_approach:
            constraints.append(f"Enfoque de desarrollo: {dev_approach}")

        return constraints

    # -- Assumptions --

    def _generate_assumptions(self, session: DiscoverySession) -> list[str]:
        """Genera supuestos del proyecto."""
        assumptions: list[str] = [
            "El cliente proporcionará acceso oportuno a stakeholders para validaciones",
            "Los datos existentes están disponibles para migración en formato estándar",
            "El cliente asignará un Product Owner dedicado al proyecto",
        ]

        has_team = _get_answer_text(session, "tech_01")
        if has_team and ("sí" in has_team.lower() or "si" in has_team.lower()):
            assumptions.append(
                "El equipo técnico interno del cliente colaborará en la integración"
            )

        market = _get_answer_text(session, "biz_03")
        if market:
            assumptions.append(
                f"El sistema se desplegará inicialmente para el mercado: {market}"
            )

        return assumptions

    # -- Out of scope --

    def _generate_out_of_scope(self, session: DiscoverySession) -> list[str]:
        """Genera elementos fuera del alcance."""
        out_of_scope: list[str] = [
            "Migración de datos históricos anteriores a 2 años",
            "Capacitación presencial (se incluye documentación y videos)",
            "Desarrollo de apps nativas (salvo que se incluya en el alcance)",
            "Mantenimiento de infraestructura del cliente",
        ]

        dev_approach = _get_answer_text(session, "budget_04")
        if dev_approach and "mvp" in dev_approach.lower():
            out_of_scope.append(
                "Funcionalidades que no formen parte del MVP inicial"
            )

        return out_of_scope

    # -- Estimaciones --

    def estimate_effort(self, requirements: list[Requirement]) -> dict:
        """Estima el esfuerzo total del proyecto."""
        total_hours = 0
        by_size: dict[str, int] = {}
        by_module: dict[str, int] = {}

        for req in requirements:
            hours = EFFORT_HOURS[req.estimated_effort]
            total_hours += hours

            size_key = req.estimated_effort.value
            by_size[size_key] = by_size.get(size_key, 0) + 1

            if req.module:
                by_module[req.module] = by_module.get(req.module, 0) + hours

        total_weeks = round(total_hours / 40, 1)

        return {
            "total_hours": total_hours,
            "total_weeks": total_weeks,
            "total_months": round(total_weeks / 4, 1),
            "requirements_count": len(requirements),
            "by_size": by_size,
            "by_module": by_module,
        }

    # -- Sugerencia de módulos --

    def suggest_modules(self, requirements: list[Requirement]) -> list[str]:
        """Sugiere qué módulos de XcapitSFF activar basado en los requerimientos."""
        suggested: set[str] = set()

        for req in requirements:
            if req.module and req.module in AVAILABLE_MODULES:
                suggested.add(req.module)

        # Módulos base siempre recomendados
        base_modules = {"dashboard", "notifications", "analytics"}
        suggested.update(base_modules)

        # Ordenar alfabéticamente
        return sorted(suggested)
