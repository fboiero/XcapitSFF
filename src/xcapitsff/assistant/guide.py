"""Contextual Guide — knows where the user is and proactively suggests next steps.

The guide tracks user behavior and context to provide relevant, timely
suggestions. It's the "proactive" part of the assistant — it doesn't
wait for the user to ask, it suggests based on what they should do next.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Suggestion:
    text: str
    action: str  # what to say to the assistant to trigger this
    priority: int  # 1-5, 1 is highest
    category: str  # sales, support, setup, learning
    reason: str  # why we're suggesting this


@dataclass
class UserContext:
    tenant_id: str
    user_id: str
    current_section: str = "dashboard"  # dashboard, leads, tickets, outreach, etc.
    last_actions: list[str] = field(default_factory=list)
    leads_count: int = 0
    tickets_count: int = 0
    has_imported_data: bool = False
    has_sent_outreach: bool = False
    has_configured_agents: bool = False
    wizard_completed: bool = False
    days_since_signup: int = 0
    health_score: float = 0


class ContextualGuide:
    """Generates contextual suggestions based on user behavior and state."""

    def get_suggestions(self, ctx: UserContext) -> list[Suggestion]:
        suggestions = []

        # === Day 1 — Setup ===
        if not ctx.wizard_completed:
            suggestions.append(Suggestion(
                "Completá el wizard de configuración para aprovechar todo el potencial",
                "Completar wizard",
                1, "setup",
                "No completaste el setup inicial"
            ))

        if ctx.leads_count == 0:
            suggestions.append(Suggestion(
                "Importá tus leads para empezar a usar el pipeline",
                "Importar leads",
                1, "sales",
                "No tenés leads cargados"
            ))

        if ctx.leads_count > 0 and not ctx.has_sent_outreach:
            suggestions.append(Suggestion(
                "Tus leads están listos. ¿Querés que compose un outreach para los mejores?",
                "Componer outreach para leads hot",
                2, "sales",
                "Tenés leads pero no enviaste outreach"
            ))

        # === Sales suggestions ===
        if ctx.current_section == "leads" or ctx.current_section == "dashboard":
            if ctx.leads_count > 10:
                suggestions.append(Suggestion(
                    "Revisá los leads hot que necesitan acción",
                    "Mostrar leads hot",
                    2, "sales",
                    "Hay leads de alto potencial"
                ))
                suggestions.append(Suggestion(
                    "Mirá las predicciones del pipeline",
                    "Ver predicciones",
                    3, "sales",
                    "Tené visibilidad del forecast"
                ))

        if ctx.current_section == "leads":
            suggestions.append(Suggestion(
                "¿Querés ver el pipeline como kanban?",
                "Ver kanban",
                3, "sales",
                "Visualización alternativa del pipeline"
            ))
            suggestions.append(Suggestion(
                "Ejecutá la automatización para calificar leads pendientes",
                "Ejecutar automatización",
                3, "sales",
                "Hay leads sin calificar"
            ))

        # === Support suggestions ===
        if ctx.current_section == "tickets" or ctx.current_section == "dashboard":
            if ctx.tickets_count > 0:
                suggestions.append(Suggestion(
                    "Revisá los tickets que están cerca del SLA",
                    "Ver tickets por vencer",
                    2, "support",
                    "Prevenir incumplimientos de SLA"
                ))

        if ctx.current_section == "tickets":
            suggestions.append(Suggestion(
                "¿Querés que el agente AI responda los tickets pendientes?",
                "Responder tickets con AI",
                3, "support",
                "Acelerar tiempo de respuesta"
            ))
            suggestions.append(Suggestion(
                "Buscá artículos de KB para responder más rápido",
                "Buscar en knowledge base",
                4, "support",
                "Usa la base de conocimiento"
            ))

        # === Agent suggestions ===
        if not ctx.has_configured_agents and ctx.days_since_signup >= 2:
            suggestions.append(Suggestion(
                "Activá los agentes AI para automatizar calificación y respuestas",
                "Configurar agentes",
                2, "setup",
                "Los agentes pueden ahorrar horas por semana"
            ))

        # === Health suggestions ===
        if ctx.health_score < 60:
            suggestions.append(Suggestion(
                "Tu workspace tiene áreas de mejora. Revisá el health score.",
                "Ver health score",
                2, "setup",
                f"Health score: {ctx.health_score}/100"
            ))

        # === Learning suggestions ===
        if ctx.days_since_signup <= 7:
            suggestions.append(Suggestion(
                "¿Querés un tutorial rápido de las funcionalidades principales?",
                "Ver tutoriales",
                4, "learning",
                "Estás en tu primera semana"
            ))

        # Sort by priority
        suggestions.sort(key=lambda s: s.priority)
        return suggestions[:5]  # max 5 suggestions

    def get_section_help(self, section: str) -> dict:
        """Get contextual help for each section."""
        help_map = {
            "dashboard": {
                "title": "Dashboard",
                "description": "Vista general de tu negocio. Acá ves los KPIs más importantes.",
                "tips": [
                    "Los números se actualizan en tiempo real",
                    "Hacé click en cualquier KPI para ver detalle",
                    "El inbox muestra las acciones pendientes más urgentes",
                ],
            },
            "leads": {
                "title": "Leads",
                "description": "Gestioná tu pipeline de ventas. Cada lead tiene un score ICP automático.",
                "tips": [
                    "Los leads se califican automáticamente al crearlos",
                    "Podés arrastrar leads entre etapas en el kanban",
                    "Los leads 'hot' (score ≥70) necesitan contacto inmediato",
                ],
            },
            "tickets": {
                "title": "Tickets",
                "description": "Gestioná soporte al cliente. Los tickets se clasifican y rutean automáticamente.",
                "tips": [
                    "Los tickets urgentes aparecen primero",
                    "El SLA se calcula según la prioridad",
                    "El agente AI puede sugerir respuestas",
                ],
            },
            "outreach": {
                "title": "Outreach",
                "description": "Enviá mensajes personalizados a tus leads. El sistema genera borradores automáticos.",
                "tips": [
                    "Cada mensaje tiene variante A/B para testing",
                    "Las secuencias envían follow-ups automáticos",
                    "Personalizá el tono por región (LATAM vs Iberia)",
                ],
            },
            "analytics": {
                "title": "Analytics",
                "description": "Métricas y reportes de ventas y soporte.",
                "tips": [
                    "El forecast predice conversiones del pipeline",
                    "El reporte de churn identifica clientes en riesgo",
                    "Los reportes se exportan en CSV, JSON o Markdown",
                ],
            },
        }
        return help_map.get(section, {
            "title": section.capitalize(),
            "description": "Sección del sistema",
            "tips": [],
        })

    def get_empty_state_message(self, section: str) -> dict:
        """Message to show when a section has no data."""
        messages = {
            "leads": {
                "title": "No tenés leads todavía",
                "description": "Importá tus leads desde un CSV o creá uno manualmente para empezar.",
                "actions": [
                    {"label": "Importar CSV", "command": "Importar leads"},
                    {"label": "Crear lead manual", "command": "Crear lead"},
                    {"label": "Cargar datos de demo", "command": "Cargar demo"},
                ],
            },
            "tickets": {
                "title": "No hay tickets aún",
                "description": "Los tickets se crean cuando tus clientes necesitan ayuda.",
                "actions": [
                    {"label": "Crear ticket de prueba", "command": "Crear ticket"},
                    {"label": "Configurar webhook", "command": "Configurar webhooks"},
                ],
            },
            "outreach": {
                "title": "No enviaste outreach todavía",
                "description": "Primero necesitás leads calificados. El sistema genera mensajes automáticamente.",
                "actions": [
                    {"label": "Ver leads hot", "command": "Ver leads hot"},
                    {"label": "Crear secuencia", "command": "Crear secuencia de outreach"},
                ],
            },
        }
        return messages.get(section, {
            "title": f"No hay datos en {section}",
            "description": "Empezá usando la sección para ver datos acá.",
            "actions": [],
        })


# Singleton
contextual_guide = ContextualGuide()
