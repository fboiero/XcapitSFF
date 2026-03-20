"""Command Palette — Ctrl+K to search and execute any action.

Like Spotlight/Alfred but for the product. User types, sees matching
commands/entities, selects one, and it executes.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CommandItem:
    item_id: str
    title: str
    subtitle: str
    category: str  # navigation, action, entity, recent
    icon: str
    action: str  # what to execute
    keywords: list[str] = field(default_factory=list)


# Static commands always available
STATIC_COMMANDS: list[CommandItem] = [
    # Navigation
    CommandItem("nav_dashboard", "Dashboard", "Ver el panel principal", "navigation", "📊", "navigate('dashboard')", ["dashboard", "panel", "inicio", "home"]),
    CommandItem("nav_leads", "Leads", "Ver pipeline de leads", "navigation", "👥", "navigate('leads')", ["leads", "prospectos", "pipeline", "ventas"]),
    CommandItem("nav_tickets", "Tickets", "Ver tickets de soporte", "navigation", "🎫", "navigate('tickets')", ["tickets", "soporte", "casos"]),
    CommandItem("nav_outreach", "Outreach", "Ver mensajes enviados", "navigation", "✉️", "navigate('outreach')", ["outreach", "mensajes", "contacto"]),
    CommandItem("nav_analytics", "Analytics", "Ver métricas y reportes", "navigation", "📈", "navigate('analytics')", ["analytics", "métricas", "reportes", "estadísticas"]),
    CommandItem("nav_kanban", "Kanban", "Ver pipeline visual", "navigation", "📋", "navigate('kanban')", ["kanban", "tablero", "visual"]),
    CommandItem("nav_inbox", "Inbox", "Ver acciones pendientes", "navigation", "📥", "navigate('inbox')", ["inbox", "bandeja", "pendientes"]),

    # Actions
    CommandItem("act_create_lead", "Crear Lead", "Nuevo prospecto", "action", "➕", "openForm('create_lead')", ["crear", "nuevo", "lead", "prospecto"]),
    CommandItem("act_create_ticket", "Crear Ticket", "Nuevo caso de soporte", "action", "➕", "openForm('create_ticket')", ["crear", "nuevo", "ticket", "caso"]),
    CommandItem("act_outreach", "Componer Outreach", "Redactar mensaje", "action", "✍️", "openForm('compose_outreach')", ["componer", "redactar", "outreach", "mensaje"]),
    CommandItem("act_import", "Importar Datos", "Subir CSV", "action", "📤", "openForm('import')", ["importar", "subir", "csv", "cargar"]),
    CommandItem("act_export", "Exportar Datos", "Descargar CSV/JSON", "action", "📥", "openForm('export')", ["exportar", "descargar", "csv", "json"]),
    CommandItem("act_meeting", "Agendar Reunión", "Programar meeting", "action", "📅", "openForm('schedule_meeting')", ["agendar", "reunión", "meeting", "programar"]),
    CommandItem("act_automation", "Ejecutar Automatización", "Correr reglas", "action", "⚡", "runAutomation()", ["automatizar", "reglas", "ejecutar"]),
    CommandItem("act_qualify", "Calificar Leads", "Bulk qualify", "action", "⭐", "bulkQualify()", ["calificar", "scoring", "puntuar"]),

    # Views
    CommandItem("view_health", "Health Score", "Ver salud del workspace", "action", "💪", "navigate('health')", ["health", "salud", "score"]),
    CommandItem("view_predictions", "Predicciones", "Forecast de pipeline", "action", "🔮", "navigate('predictions')", ["predicciones", "forecast", "pronóstico"]),
    CommandItem("view_churn", "Riesgo de Churn", "Clientes en riesgo", "action", "⚠️", "navigate('churn')", ["churn", "riesgo", "retención"]),

    # System
    CommandItem("sys_shortcuts", "Atajos de Teclado", "Ver todos los shortcuts", "system", "⌨️", "showShortcuts()", ["atajos", "shortcuts", "teclado"]),
    CommandItem("sys_help", "Ayuda", "Centro de ayuda", "system", "❓", "showHelp()", ["ayuda", "help", "soporte"]),
    CommandItem("sys_settings", "Configuración", "Ajustes del workspace", "system", "⚙️", "navigate('settings')", ["configuración", "settings", "ajustes"]),
]


class CommandPalette:
    """Search and execute commands via Ctrl+K palette."""

    def __init__(self):
        self._recent: list[str] = []  # recent command IDs

    def search(self, query: str, limit: int = 10) -> list[CommandItem]:
        """Search commands by query text."""
        if not query:
            return self._get_recent() + STATIC_COMMANDS[:5]

        query_lower = query.lower().strip()
        scored: list[tuple[CommandItem, float]] = []

        for cmd in STATIC_COMMANDS:
            score = 0.0
            # Title match
            if query_lower in cmd.title.lower():
                score += 10.0
            # Subtitle match
            if query_lower in cmd.subtitle.lower():
                score += 5.0
            # Keyword match
            for kw in cmd.keywords:
                if query_lower in kw or kw in query_lower:
                    score += 3.0

            if score > 0:
                scored.append((cmd, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [cmd for cmd, _ in scored[:limit]]

    def execute(self, command_id: str) -> CommandItem | None:
        """Record execution of a command."""
        for cmd in STATIC_COMMANDS:
            if cmd.item_id == command_id:
                self._record_recent(command_id)
                return cmd
        return None

    def _record_recent(self, command_id: str) -> None:
        if command_id in self._recent:
            self._recent.remove(command_id)
        self._recent.insert(0, command_id)
        self._recent = self._recent[:10]

    def _get_recent(self) -> list[CommandItem]:
        result = []
        for cmd_id in self._recent:
            for cmd in STATIC_COMMANDS:
                if cmd.item_id == cmd_id:
                    result.append(CommandItem(
                        item_id=cmd.item_id, title=cmd.title,
                        subtitle="Reciente", category="recent",
                        icon=cmd.icon, action=cmd.action,
                    ))
                    break
        return result


# Singleton
command_palette = CommandPalette()
