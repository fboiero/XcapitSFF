"""Visual Components — data structures for rendering UI elements.

Each visual component maps to a frontend component that the web dashboard
renders. The assistant returns these as part of its responses so the
user sees visual feedback for every action.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class VisualType(str, Enum):
    KPI_CARD = "kpi_card"
    TABLE = "table"
    KANBAN = "kanban"
    CHART_BAR = "chart_bar"
    CHART_FUNNEL = "chart_funnel"
    SCORE_CARD = "score_card"
    FORM = "form"
    TIMELINE = "timeline"
    CHAT_CARD = "chat_card"
    ACTION_CARD = "action_card"
    PROGRESS_BAR = "progress_bar"
    ALERT = "alert"
    LIST = "list"
    EMPTY_STATE = "empty_state"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class VisualComponent:
    type: VisualType
    title: str = ""
    data: dict = field(default_factory=dict)


def kpi_card(label: str, value, icon: str = "", trend: str = "", color: str = "#3b82f6") -> VisualComponent:
    return VisualComponent(VisualType.KPI_CARD, label, {
        "value": value, "icon": icon, "trend": trend, "color": color,
    })


def table(title: str, headers: list[str], rows: list[list], actions: list[str] | None = None) -> VisualComponent:
    return VisualComponent(VisualType.TABLE, title, {
        "headers": headers, "rows": rows, "actions": actions or [],
    })


def score_card(label: str, score: float, max_score: float = 100, classification: str = "", color: str = "#3b82f6", details: list[dict] | None = None) -> VisualComponent:
    return VisualComponent(VisualType.SCORE_CARD, label, {
        "score": score, "max_score": max_score, "classification": classification,
        "color": color, "percentage": round(score / max_score * 100, 1),
        "details": details or [],
    })


def funnel_chart(title: str, stages: list[dict]) -> VisualComponent:
    """stages: [{"label": "Nuevos", "count": 50, "color": "#3b82f6"}, ...]"""
    return VisualComponent(VisualType.CHART_FUNNEL, title, {"stages": stages})


def bar_chart(title: str, labels: list[str], values: list[float], colors: list[str] | None = None) -> VisualComponent:
    return VisualComponent(VisualType.CHART_BAR, title, {
        "labels": labels, "values": values, "colors": colors,
    })


def timeline(title: str, events: list[dict]) -> VisualComponent:
    """events: [{"time": "...", "title": "...", "description": "...", "icon": "..."}, ...]"""
    return VisualComponent(VisualType.TIMELINE, title, {"events": events})


def action_card(title: str, description: str, action_label: str, action_endpoint: str, icon: str = "") -> VisualComponent:
    return VisualComponent(VisualType.ACTION_CARD, title, {
        "description": description, "action_label": action_label,
        "action_endpoint": action_endpoint, "icon": icon,
    })


def form(title: str, fields: list[dict], submit_endpoint: str, submit_label: str = "Guardar") -> VisualComponent:
    """fields: [{"name": "...", "label": "...", "type": "text|email|select|number", "required": true, "options": [...]}]"""
    return VisualComponent(VisualType.FORM, title, {
        "fields": fields, "submit_endpoint": submit_endpoint,
        "submit_label": submit_label,
    })


def progress_bar(title: str, current: int, total: int, label: str = "") -> VisualComponent:
    pct = round(current / max(total, 1) * 100, 1)
    return VisualComponent(VisualType.PROGRESS_BAR, title, {
        "current": current, "total": total, "percentage": pct, "label": label,
    })


def alert(message: str, level: str = "info", actions: list[dict] | None = None) -> VisualComponent:
    """level: info, warning, error, success"""
    return VisualComponent(VisualType.ALERT, "", {
        "message": message, "level": level, "actions": actions or [],
    })


def success(message: str, details: dict | None = None) -> VisualComponent:
    return VisualComponent(VisualType.SUCCESS, message, details or {})


def error(message: str, details: str = "") -> VisualComponent:
    return VisualComponent(VisualType.ERROR, message, {"details": details})


def empty_state(title: str, description: str, action_label: str = "", action_endpoint: str = "") -> VisualComponent:
    return VisualComponent(VisualType.EMPTY_STATE, title, {
        "description": description, "action_label": action_label,
        "action_endpoint": action_endpoint,
    })


def chat_card(agent_name: str, message: str, confidence: float = 1.0) -> VisualComponent:
    return VisualComponent(VisualType.CHAT_CARD, agent_name, {
        "message": message, "confidence": confidence,
    })


# === Composite builders ===

def build_lead_card(lead_data: dict) -> VisualComponent:
    """Build a visual card for a lead."""
    score = lead_data.get("score_icp", 0) or 0
    if score >= 70:
        color = "#22c55e"
        classification = "HOT"
    elif score >= 45:
        color = "#f59e0b"
        classification = "WARM"
    elif score >= 25:
        color = "#3b82f6"
        classification = "COOL"
    else:
        color = "#6b7280"
        classification = "COLD"

    return score_card(
        lead_data.get("company_name", f"Lead #{lead_data.get('id', '?')}"),
        score, 100, classification, color,
        details=[
            {"label": "Región", "value": lead_data.get("region", "?")},
            {"label": "C-Level", "value": "Sí" if lead_data.get("c_level") else "No"},
            {"label": "Afinidad", "value": lead_data.get("afinidad", "?")},
            {"label": "Stage", "value": lead_data.get("stage", "raw")},
        ],
    )


def build_ticket_card(ticket_data: dict) -> VisualComponent:
    priority = ticket_data.get("priority", "medium")
    color_map = {"urgent": "#ef4444", "high": "#f97316", "medium": "#f59e0b", "low": "#22c55e"}

    return VisualComponent(VisualType.ACTION_CARD, ticket_data.get("subject", "Ticket"), {
        "description": ticket_data.get("description", "")[:150],
        "priority": priority,
        "category": ticket_data.get("category", "general"),
        "status": ticket_data.get("status", "open"),
        "color": color_map.get(priority, "#6b7280"),
        "action_label": "Ver ticket",
        "action_endpoint": f"/api/v1/tickets/{ticket_data.get('id')}",
    })


def build_dashboard_visuals(dashboard_data: dict) -> list[VisualComponent]:
    """Build all visual components for the main dashboard."""
    components = []

    sales = dashboard_data.get("sales", {})
    support = dashboard_data.get("support", {})

    # KPI cards
    components.append(kpi_card("Total Leads", sales.get("total_leads", 0), "📊"))
    components.append(kpi_card("Tickets Abiertos", support.get("open_tickets", 0), "🎫",
                               color="#f59e0b" if support.get("open_tickets", 0) > 10 else "#22c55e"))
    components.append(kpi_card("Tasa de Conversión",
                               f"{sales.get('conversion_rate', 0) or 0}%", "📈"))
    components.append(kpi_card("Score Promedio", sales.get("avg_score", "N/A"), "⭐"))

    # Funnel
    funnel_data = sales.get("funnel", [])
    if funnel_data:
        stages = [{"label": s.get("stage", ""), "count": s.get("count", 0)} for s in funnel_data]
        components.append(funnel_chart("Pipeline de Ventas", stages))

    return components
