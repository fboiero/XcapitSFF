"""Quickstart — instant value for new users in under 5 minutes.

Provides guided "quick wins" that demonstrate product value immediately
after signup, without requiring full configuration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class QuickAction:
    action_id: str
    title: str
    description: str
    category: str  # sales, support, agents, analytics
    estimated_seconds: int
    api_endpoint: str
    api_method: str  # GET or POST
    api_body: dict | None = None
    result_description: str = ""


# Actions that give instant value
QUICK_ACTIONS: list[QuickAction] = [
    QuickAction(
        "try_scoring", "Probá el scoring ICP",
        "Creá un lead de ejemplo y mirá cómo el sistema lo califica automáticamente.",
        "sales", 10,
        "/api/v1/leads/", "POST",
        {"company_name": "Mi Empresa Test", "contact_name": "Juan Pérez",
         "contact_email": "juan@test.com", "region": "LATAM", "c_level": True,
         "afinidad": "HIGH"},
        "Vas a ver el score ICP calculado automáticamente y la clasificación del lead."
    ),
    QuickAction(
        "try_routing", "Probá el routing de tickets",
        "Creá un ticket de ejemplo y mirá cómo el sistema lo clasifica y rutea.",
        "support", 10,
        "/api/v1/webhooks/tickets", "POST",
        {"customer_email": "test@demo.com",
         "subject": "No puedo acceder a mi cuenta",
         "description": "Olvidé mi contraseña y el link de reset no funciona"},
        "El sistema clasifica el ticket como 'account', asigna prioridad y agente automáticamente."
    ),
    QuickAction(
        "try_agent", "Probá un agente AI",
        "Pedile al agente de ventas que califique un lead.",
        "agents", 15,
        "/api/v1/playground/start", "POST",
        {"agent_role": "sales_qualifier"},
        "Podés chatear con el agente y ver cómo analiza leads."
    ),
    QuickAction(
        "see_dashboard", "Mirá el dashboard",
        "Abrí el dashboard ejecutivo para ver la vista general.",
        "analytics", 5,
        "/api/v1/dashboard/", "GET",
        None,
        "El dashboard muestra KPIs de ventas, soporte y agentes en tiempo real."
    ),
    QuickAction(
        "try_outreach", "Generá un outreach",
        "Pedí al sistema que componga un mensaje de venta personalizado.",
        "sales", 10,
        "/api/v1/outreach/compose/1", "POST",
        None,  # needs a lead_id, created in try_scoring
        "El sistema genera un email personalizado con variante A/B."
    ),
    QuickAction(
        "see_kanban", "Mirá el pipeline visual",
        "Abrí el kanban para ver tus leads organizados por etapa.",
        "sales", 5,
        "/api/v1/kanban/board", "GET",
        None,
        "Vista drag-and-drop de todo tu pipeline de ventas."
    ),
    QuickAction(
        "try_kb_search", "Buscá en la Knowledge Base",
        "Probá la búsqueda semántica de artículos de soporte.",
        "support", 10,
        "/api/v1/knowledge/search?q=como+resetear+contraseña", "GET",
        None,
        "El sistema encuentra artículos relevantes rankeados por relevancia."
    ),
    QuickAction(
        "check_health", "Revisá tu health score",
        "Mirá qué tan bien configurado está tu workspace.",
        "analytics", 5,
        "/api/v1/health-score", "GET",
        None,
        "Te muestra un score de 0-100 con recomendaciones para mejorar."
    ),
]


@dataclass
class QuickstartProgress:
    tenant_id: str
    actions_completed: list[str] = field(default_factory=list)
    actions_skipped: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    time_to_first_value_seconds: float | None = None

    @property
    def completion_rate(self) -> float:
        total = len(QUICK_ACTIONS)
        done = len(self.actions_completed)
        return round(done / total * 100, 1) if total > 0 else 0


class QuickstartManager:
    """Manages the quickstart experience for new users."""

    def __init__(self):
        self._progress: dict[str, QuickstartProgress] = {}

    def start(self, tenant_id: str) -> QuickstartProgress:
        if tenant_id not in self._progress:
            self._progress[tenant_id] = QuickstartProgress(tenant_id=tenant_id)
        return self._progress[tenant_id]

    def get_actions(self, category: str | None = None) -> list[QuickAction]:
        actions = QUICK_ACTIONS
        if category:
            actions = [a for a in actions if a.category == category]
        return actions

    def complete_action(self, tenant_id: str, action_id: str) -> QuickstartProgress:
        progress = self.start(tenant_id)
        if action_id not in progress.actions_completed:
            progress.actions_completed.append(action_id)
            if len(progress.actions_completed) == 1:
                progress.time_to_first_value_seconds = (
                    datetime.now() - progress.started_at
                ).total_seconds()
        return progress

    def skip_action(self, tenant_id: str, action_id: str) -> QuickstartProgress:
        progress = self.start(tenant_id)
        if action_id not in progress.actions_skipped:
            progress.actions_skipped.append(action_id)
        return progress

    def get_progress(self, tenant_id: str) -> QuickstartProgress:
        return self.start(tenant_id)

    def get_next_action(self, tenant_id: str) -> QuickAction | None:
        progress = self.start(tenant_id)
        done = set(progress.actions_completed) | set(progress.actions_skipped)
        for action in QUICK_ACTIONS:
            if action.action_id not in done:
                return action
        return None

    def get_summary(self, tenant_id: str) -> dict:
        progress = self.start(tenant_id)
        return {
            "tenant_id": tenant_id,
            "completion_rate": progress.completion_rate,
            "actions_completed": len(progress.actions_completed),
            "actions_total": len(QUICK_ACTIONS),
            "time_to_first_value": progress.time_to_first_value_seconds,
            "next_action": (
                self.get_next_action(tenant_id).action_id
                if self.get_next_action(tenant_id)
                else None
            ),
        }


# Singleton
quickstart_manager = QuickstartManager()
