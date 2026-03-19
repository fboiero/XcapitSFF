"""Interactive tutorials for self-service onboarding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TutorialStep:
    """A single step within an interactive tutorial."""

    step_number: int
    title: str
    description: str
    action: str  # API call or instruction
    highlight_element: str = ""  # CSS selector hint for frontend
    completed: bool = False


@dataclass
class Tutorial:
    """An interactive tutorial."""

    tutorial_id: str
    name: str
    description: str
    target_audience: str  # new_user / sales / support / admin
    steps: list[TutorialStep] = field(default_factory=list)
    estimated_minutes: int = 5


# ---------------------------------------------------------------------------
# Pre-built tutorials (all in Spanish)
# ---------------------------------------------------------------------------

def _build_tutorials() -> list[Tutorial]:
    """Return all available tutorials."""

    first_lead = Tutorial(
        tutorial_id="first_lead",
        name="Tu primer lead",
        description="Aprend\u00e9 a crear un lead, ver su scoring y calificarlo.",
        target_audience="new_user",
        estimated_minutes=5,
        steps=[
            TutorialStep(
                step_number=1,
                title="Crear un lead",
                description="Hac\u00e9 clic en 'Nuevo lead' y complet\u00e1 los datos b\u00e1sicos.",
                action="POST /api/v1/leads/",
                highlight_element="#btn-new-lead",
            ),
            TutorialStep(
                step_number=2,
                title="Ver el scoring",
                description="Una vez creado, mir\u00e1 el score ICP que se calcul\u00f3 autom\u00e1ticamente.",
                action="GET /api/v1/leads/{id}",
                highlight_element=".lead-score-badge",
            ),
            TutorialStep(
                step_number=3,
                title="Calificar el lead",
                description="Si el score es bueno, mov\u00e9 el lead a 'Calificado'.",
                action="PATCH /api/v1/leads/{id}",
                highlight_element=".lead-stage-selector",
            ),
        ],
    )

    first_ticket = Tutorial(
        tutorial_id="first_ticket",
        name="Tu primer ticket",
        description="Cre\u00e1 un ticket de soporte, ve\u00e1 el ruteo y respond\u00e9.",
        target_audience="new_user",
        estimated_minutes=5,
        steps=[
            TutorialStep(
                step_number=1,
                title="Crear un ticket",
                description="Hac\u00e9 clic en 'Nuevo ticket' y describí el problema.",
                action="POST /api/v1/tickets/",
                highlight_element="#btn-new-ticket",
            ),
            TutorialStep(
                step_number=2,
                title="Ver el ruteo",
                description="Observ\u00e1 c\u00f3mo el ticket se asigna autom\u00e1ticamente.",
                action="GET /api/v1/tickets/{id}",
                highlight_element=".ticket-assignment",
            ),
            TutorialStep(
                step_number=3,
                title="Responder al ticket",
                description="Escrib\u00ed una respuesta para el cliente.",
                action="POST /api/v1/tickets/{id}/respond",
                highlight_element=".ticket-reply-box",
            ),
        ],
    )

    import_csv = Tutorial(
        tutorial_id="import_csv",
        name="Importar datos",
        description="Sub\u00ed un CSV con tus datos, mape\u00e1 los campos y verific\u00e1.",
        target_audience="admin",
        estimated_minutes=10,
        steps=[
            TutorialStep(
                step_number=1,
                title="Subir archivo CSV",
                description="Seleccion\u00e1 tu archivo CSV con los leads a importar.",
                action="POST /api/v1/leads/import",
                highlight_element="#btn-import-csv",
            ),
            TutorialStep(
                step_number=2,
                title="Mapear campos",
                description="Asign\u00e1 cada columna del CSV al campo correspondiente.",
                action="UI: field mapping screen",
                highlight_element=".field-mapping-table",
            ),
            TutorialStep(
                step_number=3,
                title="Verificar importaci\u00f3n",
                description="Revis\u00e1 el resultado y correg\u00ed errores si los hay.",
                action="GET /api/v1/leads/?limit=10",
                highlight_element=".import-results-summary",
            ),
        ],
    )

    setup_outreach = Tutorial(
        tutorial_id="setup_outreach",
        name="Configurar outreach",
        description="Cre\u00e1 una secuencia de outreach y enrollá leads.",
        target_audience="sales",
        estimated_minutes=8,
        steps=[
            TutorialStep(
                step_number=1,
                title="Crear secuencia",
                description="Defin\u00ed nombre, asunto y cuerpo del primer mensaje.",
                action="POST /api/v1/sequences/",
                highlight_element="#btn-new-sequence",
            ),
            TutorialStep(
                step_number=2,
                title="Agregar pasos",
                description="Sum\u00e1 pasos de seguimiento con delays entre ellos.",
                action="POST /api/v1/sequences/{id}/steps",
                highlight_element=".sequence-step-list",
            ),
            TutorialStep(
                step_number=3,
                title="Enrollar leads",
                description="Seleccion\u00e1 leads y agregalos a la secuencia.",
                action="POST /api/v1/sequences/{id}/enroll",
                highlight_element="#btn-enroll-leads",
            ),
        ],
    )

    use_dashboard = Tutorial(
        tutorial_id="use_dashboard",
        name="Entender el dashboard",
        description="Naveg\u00e1 las m\u00e9tricas clave y KPIs de tu workspace.",
        target_audience="new_user",
        estimated_minutes=5,
        steps=[
            TutorialStep(
                step_number=1,
                title="Abrir dashboard",
                description="Naveg\u00e1 al dashboard principal para ver el resumen.",
                action="GET /api/v1/dashboard/",
                highlight_element="#nav-dashboard",
            ),
            TutorialStep(
                step_number=2,
                title="Revisar m\u00e9tricas de ventas",
                description="Mir\u00e1 la cantidad de leads, conversi\u00f3n y pipeline.",
                action="GET /api/v1/analytics/sales",
                highlight_element=".sales-metrics-card",
            ),
            TutorialStep(
                step_number=3,
                title="Revisar m\u00e9tricas de soporte",
                description="Observ\u00e1 tickets abiertos, tiempo de respuesta y satisfacci\u00f3n.",
                action="GET /api/v1/analytics/support",
                highlight_element=".support-metrics-card",
            ),
        ],
    )

    configure_agents = Tutorial(
        tutorial_id="configure_agents",
        name="Activar agentes AI",
        description="Prob\u00e1 la calificaci\u00f3n autom\u00e1tica y la respuesta de agentes.",
        target_audience="admin",
        estimated_minutes=10,
        steps=[
            TutorialStep(
                step_number=1,
                title="Activar agentes",
                description="Habilit\u00e1 los agentes AI desde la configuraci\u00f3n.",
                action="POST /api/v1/agents/configure",
                highlight_element="#toggle-agents",
            ),
            TutorialStep(
                step_number=2,
                title="Probar calificaci\u00f3n",
                description="Cre\u00e1 un lead de prueba y observ\u00e1 la calificaci\u00f3n autom\u00e1tica.",
                action="POST /api/v1/agents/qualify-test",
                highlight_element=".agent-qualify-demo",
            ),
            TutorialStep(
                step_number=3,
                title="Probar respuesta",
                description="Cre\u00e1 un ticket de prueba y mir\u00e1 c\u00f3mo responde el agente.",
                action="POST /api/v1/agents/respond-test",
                highlight_element=".agent-respond-demo",
            ),
        ],
    )

    return [
        first_lead,
        first_ticket,
        import_csv,
        setup_outreach,
        use_dashboard,
        configure_agents,
    ]


# ---------------------------------------------------------------------------
# Tutorial Manager
# ---------------------------------------------------------------------------


class TutorialManager:
    """Manages interactive tutorials for users."""

    def __init__(self) -> None:
        self._tutorials: dict[str, Tutorial] = {
            t.tutorial_id: t for t in _build_tutorials()
        }
        # tenant_id -> { tutorial_id -> { "status": ..., "completed_steps": [...] } }
        self._progress: dict[str, dict[str, dict[str, Any]]] = {}

    def list_tutorials(self, audience: str | None = None) -> list[Tutorial]:
        """Return tutorials, optionally filtered by target audience."""
        tutorials = list(self._tutorials.values())
        if audience:
            tutorials = [t for t in tutorials if t.target_audience == audience]
        return tutorials

    def start_tutorial(self, tenant_id: str, tutorial_id: str) -> Tutorial:
        """Start a tutorial for a tenant."""
        tutorial = self._tutorials.get(tutorial_id)
        if not tutorial:
            raise ValueError(f"Tutorial '{tutorial_id}' no encontrado.")

        if tenant_id not in self._progress:
            self._progress[tenant_id] = {}

        self._progress[tenant_id][tutorial_id] = {
            "status": "in_progress",
            "completed_steps": [],
        }

        # Return a fresh copy with steps reset
        return Tutorial(
            tutorial_id=tutorial.tutorial_id,
            name=tutorial.name,
            description=tutorial.description,
            target_audience=tutorial.target_audience,
            estimated_minutes=tutorial.estimated_minutes,
            steps=[
                TutorialStep(
                    step_number=s.step_number,
                    title=s.title,
                    description=s.description,
                    action=s.action,
                    highlight_element=s.highlight_element,
                    completed=False,
                )
                for s in tutorial.steps
            ],
        )

    def complete_step(
        self, tenant_id: str, tutorial_id: str, step_number: int
    ) -> Tutorial:
        """Mark a tutorial step as completed."""
        tutorial = self._tutorials.get(tutorial_id)
        if not tutorial:
            raise ValueError(f"Tutorial '{tutorial_id}' no encontrado.")

        tenant_progress = self._progress.get(tenant_id, {})
        tut_progress = tenant_progress.get(tutorial_id)
        if not tut_progress:
            raise ValueError(
                f"El tutorial '{tutorial_id}' no fue iniciado para el tenant '{tenant_id}'."
            )

        # Validate step number
        valid_steps = [s.step_number for s in tutorial.steps]
        if step_number not in valid_steps:
            raise ValueError(
                f"Paso {step_number} inv\u00e1lido. Pasos v\u00e1lidos: {valid_steps}"
            )

        if step_number not in tut_progress["completed_steps"]:
            tut_progress["completed_steps"].append(step_number)

        # Check if all steps are done
        if set(tut_progress["completed_steps"]) == set(valid_steps):
            tut_progress["status"] = "completed"

        # Return tutorial with progress applied
        return Tutorial(
            tutorial_id=tutorial.tutorial_id,
            name=tutorial.name,
            description=tutorial.description,
            target_audience=tutorial.target_audience,
            estimated_minutes=tutorial.estimated_minutes,
            steps=[
                TutorialStep(
                    step_number=s.step_number,
                    title=s.title,
                    description=s.description,
                    action=s.action,
                    highlight_element=s.highlight_element,
                    completed=s.step_number in tut_progress["completed_steps"],
                )
                for s in tutorial.steps
            ],
        )

    def get_progress(self, tenant_id: str) -> dict[str, Any]:
        """Return tutorial progress for a tenant."""
        tenant_progress = self._progress.get(tenant_id, {})

        result: dict[str, Any] = {
            "tenant_id": tenant_id,
            "tutorials": {},
        }

        for tutorial_id, tut_data in tenant_progress.items():
            tutorial = self._tutorials.get(tutorial_id)
            total_steps = len(tutorial.steps) if tutorial else 0
            result["tutorials"][tutorial_id] = {
                "status": tut_data["status"],
                "steps_completed": len(tut_data["completed_steps"]),
                "total_steps": total_steps,
            }

        return result
