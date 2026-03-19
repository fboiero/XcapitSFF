"""Role-based Dashboards — each user role sees different data.

Sales rep sees leads + outreach. Support agent sees tickets + SLA.
Manager sees everything. Admin sees system health.
"""

from dataclasses import dataclass, field


@dataclass
class DashboardConfig:
    role: str
    title: str
    kpis: list[str]
    sections: list[str]
    quick_actions: list[dict]
    refresh_interval_seconds: int = 30


ROLE_DASHBOARDS: dict[str, DashboardConfig] = {
    "sales_rep": DashboardConfig(
        role="sales_rep",
        title="Mi Pipeline de Ventas",
        kpis=["my_leads_count", "hot_leads", "outreach_pending", "meetings_today"],
        sections=["kanban", "hot_leads_table", "outreach_drafts", "upcoming_meetings"],
        quick_actions=[
            {"label": "Crear lead", "command": "Crear lead", "icon": "➕"},
            {"label": "Componer outreach", "command": "Componer outreach", "icon": "✉️"},
            {"label": "Ver leads hot", "command": "Ver leads hot", "icon": "🔥"},
            {"label": "Agendar reunión", "command": "Agendar reunión", "icon": "📅"},
        ],
    ),
    "support_agent": DashboardConfig(
        role="support_agent",
        title="Mi Cola de Soporte",
        kpis=["my_open_tickets", "urgent_tickets", "sla_at_risk", "resolved_today"],
        sections=["ticket_queue", "sla_warnings", "kb_suggestions", "csat_recent"],
        quick_actions=[
            {"label": "Ver tickets urgentes", "command": "Ver tickets urgentes", "icon": "🚨"},
            {"label": "Buscar en KB", "command": "Buscar en KB", "icon": "📚"},
            {"label": "Responder ticket", "command": "Responder ticket", "icon": "💬"},
            {"label": "Crear artículo KB", "command": "Crear artículo KB", "icon": "📝"},
        ],
    ),
    "manager": DashboardConfig(
        role="manager",
        title="Vista de Manager",
        kpis=["total_leads", "conversion_rate", "open_tickets", "sla_compliance"],
        sections=["pipeline_funnel", "team_performance", "analytics_summary", "inbox"],
        quick_actions=[
            {"label": "Dashboard ejecutivo", "command": "Ver dashboard", "icon": "📊"},
            {"label": "Predicciones", "command": "Ver predicciones", "icon": "🔮"},
            {"label": "Health score", "command": "Ver health score", "icon": "💪"},
            {"label": "Reportes", "command": "Generar reporte", "icon": "📋"},
        ],
    ),
    "admin": DashboardConfig(
        role="admin",
        title="Administración del Sistema",
        kpis=["active_users", "api_calls_today", "system_health", "agent_tasks"],
        sections=["system_status", "usage_metrics", "audit_log", "scheduler_status"],
        quick_actions=[
            {"label": "Estado del sistema", "command": "Ver estado del sistema", "icon": "⚙️"},
            {"label": "Calidad de datos", "command": "Ver calidad de datos", "icon": "🔍"},
            {"label": "Métricas", "command": "Ver métricas", "icon": "📈"},
            {"label": "Configuración", "command": "Configurar settings", "icon": "🔧"},
        ],
    ),
}


def get_dashboard_for_role(role: str) -> DashboardConfig:
    """Get the dashboard configuration for a user role."""
    return ROLE_DASHBOARDS.get(role, ROLE_DASHBOARDS["manager"])


def get_available_roles() -> list[dict]:
    """List available dashboard roles."""
    return [
        {"role": config.role, "title": config.title, "kpis": len(config.kpis)}
        for config in ROLE_DASHBOARDS.values()
    ]


def get_quick_actions_for_role(role: str) -> list[dict]:
    """Get quick actions for a role."""
    config = get_dashboard_for_role(role)
    return config.quick_actions
