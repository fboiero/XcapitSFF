"""Dashboard Widgets — customizable widget system for user dashboards.

Provides a flexible widget-based dashboard where each user/tenant can
configure their own layout with different widget types, sizes, and positions.
All data is stored in-memory.
"""

from __future__ import annotations

import copy
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WidgetType(str, Enum):
    KPI = "kpi"
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    FUNNEL = "funnel"
    HEATMAP = "heatmap"
    LEADERBOARD = "leaderboard"
    ACTIVITY_FEED = "activity_feed"
    CALENDAR = "calendar"
    TODO_LIST = "todo_list"
    QUICK_ACTIONS = "quick_actions"


class WidgetSize(str, Enum):
    SMALL = "1x1"
    MEDIUM = "2x1"
    LARGE = "2x2"
    WIDE = "3x1"
    FULL = "3x2"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Widget:
    id: str
    type: WidgetType
    title: str
    description: str = ""
    config: dict = field(default_factory=dict)
    size: WidgetSize = WidgetSize.MEDIUM
    position: dict = field(default_factory=lambda: {"row": 0, "col": 0})
    visible: bool = True


@dataclass
class DashboardLayout:
    id: str
    tenant_id: str
    user_id: str
    name: str
    widgets: list[Widget] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_default: bool = False


@dataclass
class WidgetData:
    widget_id: str
    data: dict = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    cached_until: datetime | None = None


# ---------------------------------------------------------------------------
# Default widgets shipped with every new layout
# ---------------------------------------------------------------------------

DEFAULT_WIDGETS: list[dict] = [
    {
        "type": WidgetType.KPI,
        "title": "Leads Totales",
        "description": "Total de leads en el pipeline",
        "config": {"data_source": "leads", "filters": {}, "refresh_interval_seconds": 60},
        "size": WidgetSize.SMALL,
        "position": {"row": 0, "col": 0},
    },
    {
        "type": WidgetType.KPI,
        "title": "Tickets Abiertos",
        "description": "Tickets de soporte abiertos",
        "config": {"data_source": "tickets", "filters": {"status": "open"}, "refresh_interval_seconds": 60},
        "size": WidgetSize.SMALL,
        "position": {"row": 0, "col": 1},
    },
    {
        "type": WidgetType.LINE_CHART,
        "title": "Leads por Semana",
        "description": "Tendencia semanal de nuevos leads",
        "config": {"data_source": "leads_weekly", "filters": {}, "refresh_interval_seconds": 300},
        "size": WidgetSize.MEDIUM,
        "position": {"row": 0, "col": 2},
    },
    {
        "type": WidgetType.FUNNEL,
        "title": "Pipeline de Ventas",
        "description": "Embudo de conversión del pipeline",
        "config": {"data_source": "pipeline_funnel", "filters": {}, "refresh_interval_seconds": 300},
        "size": WidgetSize.LARGE,
        "position": {"row": 1, "col": 0},
    },
    {
        "type": WidgetType.PIE_CHART,
        "title": "Leads por Región",
        "description": "Distribución geográfica de leads",
        "config": {"data_source": "leads_by_region", "filters": {}, "refresh_interval_seconds": 300},
        "size": WidgetSize.MEDIUM,
        "position": {"row": 1, "col": 2},
    },
    {
        "type": WidgetType.TABLE,
        "title": "Hot Leads",
        "description": "Leads con mayor puntuación ICP",
        "config": {"data_source": "hot_leads", "filters": {"limit": 10}, "refresh_interval_seconds": 120},
        "size": WidgetSize.WIDE,
        "position": {"row": 2, "col": 0},
    },
    {
        "type": WidgetType.ACTIVITY_FEED,
        "title": "Actividad Reciente",
        "description": "Últimas acciones del equipo",
        "config": {"data_source": "activity_feed", "filters": {"limit": 20}, "refresh_interval_seconds": 30},
        "size": WidgetSize.MEDIUM,
        "position": {"row": 3, "col": 0},
    },
    {
        "type": WidgetType.LEADERBOARD,
        "title": "Top Vendedores",
        "description": "Ranking de vendedores por conversiones",
        "config": {"data_source": "sales_leaderboard", "filters": {}, "refresh_interval_seconds": 300},
        "size": WidgetSize.MEDIUM,
        "position": {"row": 3, "col": 2},
    },
]


# ---------------------------------------------------------------------------
# Widget catalog — describes each type for the UI
# ---------------------------------------------------------------------------

WIDGET_CATALOG: list[dict] = [
    {
        "type": WidgetType.KPI.value,
        "name": "KPI",
        "description": "Indicador numérico clave con variación porcentual",
        "default_config": {"data_source": "leads", "filters": {}, "refresh_interval_seconds": 60},
        "available_sizes": [WidgetSize.SMALL.value, WidgetSize.MEDIUM.value],
    },
    {
        "type": WidgetType.LINE_CHART.value,
        "name": "Gráfico de Líneas",
        "description": "Tendencia temporal con múltiples series",
        "default_config": {"data_source": "leads_weekly", "filters": {}, "refresh_interval_seconds": 300},
        "available_sizes": [WidgetSize.MEDIUM.value, WidgetSize.LARGE.value, WidgetSize.WIDE.value],
    },
    {
        "type": WidgetType.BAR_CHART.value,
        "name": "Gráfico de Barras",
        "description": "Comparación de valores entre categorías",
        "default_config": {"data_source": "leads_by_stage", "filters": {}, "refresh_interval_seconds": 300},
        "available_sizes": [WidgetSize.MEDIUM.value, WidgetSize.LARGE.value, WidgetSize.WIDE.value],
    },
    {
        "type": WidgetType.PIE_CHART.value,
        "name": "Gráfico de Torta",
        "description": "Distribución proporcional de categorías",
        "default_config": {"data_source": "leads_by_region", "filters": {}, "refresh_interval_seconds": 300},
        "available_sizes": [WidgetSize.SMALL.value, WidgetSize.MEDIUM.value, WidgetSize.LARGE.value],
    },
    {
        "type": WidgetType.TABLE.value,
        "name": "Tabla",
        "description": "Vista tabular con columnas configurables",
        "default_config": {"data_source": "hot_leads", "filters": {"limit": 10}, "refresh_interval_seconds": 120},
        "available_sizes": [WidgetSize.MEDIUM.value, WidgetSize.LARGE.value, WidgetSize.WIDE.value, WidgetSize.FULL.value],
    },
    {
        "type": WidgetType.FUNNEL.value,
        "name": "Embudo",
        "description": "Visualización de embudo de conversión",
        "default_config": {"data_source": "pipeline_funnel", "filters": {}, "refresh_interval_seconds": 300},
        "available_sizes": [WidgetSize.MEDIUM.value, WidgetSize.LARGE.value],
    },
    {
        "type": WidgetType.HEATMAP.value,
        "name": "Mapa de Calor",
        "description": "Visualización de densidad por hora y día",
        "default_config": {"data_source": "activity_heatmap", "filters": {}, "refresh_interval_seconds": 600},
        "available_sizes": [WidgetSize.LARGE.value, WidgetSize.WIDE.value, WidgetSize.FULL.value],
    },
    {
        "type": WidgetType.LEADERBOARD.value,
        "name": "Leaderboard",
        "description": "Ranking de desempeño del equipo",
        "default_config": {"data_source": "sales_leaderboard", "filters": {}, "refresh_interval_seconds": 300},
        "available_sizes": [WidgetSize.MEDIUM.value, WidgetSize.LARGE.value],
    },
    {
        "type": WidgetType.ACTIVITY_FEED.value,
        "name": "Actividad",
        "description": "Feed cronológico de eventos recientes",
        "default_config": {"data_source": "activity_feed", "filters": {"limit": 20}, "refresh_interval_seconds": 30},
        "available_sizes": [WidgetSize.MEDIUM.value, WidgetSize.LARGE.value],
    },
    {
        "type": WidgetType.CALENDAR.value,
        "name": "Calendario",
        "description": "Próximas reuniones y seguimientos",
        "default_config": {"data_source": "calendar_events", "filters": {}, "refresh_interval_seconds": 120},
        "available_sizes": [WidgetSize.MEDIUM.value, WidgetSize.LARGE.value, WidgetSize.FULL.value],
    },
    {
        "type": WidgetType.TODO_LIST.value,
        "name": "Lista de Tareas",
        "description": "Tareas pendientes y seguimiento de progreso",
        "default_config": {"data_source": "todo_list", "filters": {}, "refresh_interval_seconds": 60},
        "available_sizes": [WidgetSize.SMALL.value, WidgetSize.MEDIUM.value, WidgetSize.LARGE.value],
    },
    {
        "type": WidgetType.QUICK_ACTIONS.value,
        "name": "Acciones Rápidas",
        "description": "Atajos a las acciones más frecuentes",
        "default_config": {"data_source": "quick_actions", "filters": {}, "refresh_interval_seconds": 0},
        "available_sizes": [WidgetSize.SMALL.value, WidgetSize.MEDIUM.value],
    },
]


# ---------------------------------------------------------------------------
# Sample data generators (one per widget type)
# ---------------------------------------------------------------------------


def _sample_kpi(widget: Widget, tenant_id: str) -> dict:
    value = random.randint(50, 500)
    return {
        "value": value,
        "previous_value": value - random.randint(-20, 40),
        "change_pct": round(random.uniform(-15, 25), 1),
        "unit": widget.config.get("unit", ""),
        "label": widget.title,
    }


def _sample_line_chart(widget: Widget, tenant_id: str) -> dict:
    today = datetime.now().date()
    labels = [(today - timedelta(days=7 * i)).isoformat() for i in range(8)]
    labels.reverse()
    return {
        "labels": labels,
        "series": [
            {"name": "Nuevos", "values": [random.randint(5, 50) for _ in labels]},
            {"name": "Convertidos", "values": [random.randint(1, 20) for _ in labels]},
        ],
    }


def _sample_bar_chart(widget: Widget, tenant_id: str) -> dict:
    categories = ["Prospecto", "Contactado", "Calificado", "Propuesta", "Cerrado"]
    return {
        "categories": categories,
        "values": [random.randint(10, 100) for _ in categories],
    }


def _sample_pie_chart(widget: Widget, tenant_id: str) -> dict:
    slices = ["LATAM", "NA", "EMEA", "APAC"]
    values = [random.randint(10, 60) for _ in slices]
    total = sum(values)
    return {
        "slices": [
            {"label": label, "value": v, "pct": round(v / total * 100, 1)}
            for label, v in zip(slices, values)
        ],
    }


def _sample_table(widget: Widget, tenant_id: str) -> dict:
    rows = []
    for i in range(min(widget.config.get("filters", {}).get("limit", 10), 10)):
        rows.append({
            "id": str(uuid.uuid4())[:8],
            "company": f"Empresa {i + 1}",
            "score": random.randint(50, 100),
            "stage": random.choice(["prospecto", "contactado", "calificado"]),
            "updated": (datetime.now() - timedelta(hours=random.randint(1, 72))).isoformat(),
        })
    return {
        "columns": ["id", "company", "score", "stage", "updated"],
        "rows": rows,
    }


def _sample_funnel(widget: Widget, tenant_id: str) -> dict:
    stages = [
        ("Prospecto", random.randint(80, 150)),
        ("Contactado", random.randint(50, 80)),
        ("Calificado", random.randint(20, 50)),
        ("Propuesta", random.randint(10, 20)),
        ("Cerrado", random.randint(2, 10)),
    ]
    return {
        "stages": [{"name": name, "count": count} for name, count in stages],
    }


def _sample_heatmap(widget: Widget, tenant_id: str) -> dict:
    days = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    hours = list(range(8, 20))
    cells = []
    for day in days:
        for hour in hours:
            cells.append({"day": day, "hour": hour, "value": random.randint(0, 30)})
    return {"days": days, "hours": hours, "cells": cells}


def _sample_leaderboard(widget: Widget, tenant_id: str) -> dict:
    agents = ["Ana García", "Carlos López", "María Torres", "Diego Ruiz", "Lucía Fernández"]
    entries = []
    for i, name in enumerate(agents):
        entries.append({
            "rank": i + 1,
            "name": name,
            "conversions": random.randint(5, 30),
            "revenue": random.randint(5000, 50000),
        })
    entries.sort(key=lambda x: x["conversions"], reverse=True)
    for i, e in enumerate(entries):
        e["rank"] = i + 1
    return {"entries": entries}


def _sample_activity_feed(widget: Widget, tenant_id: str) -> dict:
    actions = [
        "creó un nuevo lead",
        "cerró un ticket",
        "envió un email de seguimiento",
        "calificó un prospecto",
        "actualizó un contacto",
    ]
    items = []
    for i in range(min(widget.config.get("filters", {}).get("limit", 10), 10)):
        items.append({
            "id": str(uuid.uuid4())[:8],
            "user": random.choice(["Ana", "Carlos", "María"]),
            "action": random.choice(actions),
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(1, 180))).isoformat(),
        })
    return {"items": items}


def _sample_calendar(widget: Widget, tenant_id: str) -> dict:
    events = []
    today = datetime.now()
    for i in range(5):
        start = today + timedelta(days=random.randint(0, 7), hours=random.randint(9, 17))
        events.append({
            "id": str(uuid.uuid4())[:8],
            "title": random.choice(["Reunión con cliente", "Demo producto", "Seguimiento", "Call de cierre"]),
            "start": start.isoformat(),
            "duration_minutes": random.choice([30, 45, 60]),
        })
    return {"events": events}


def _sample_todo_list(widget: Widget, tenant_id: str) -> dict:
    todos = [
        "Enviar propuesta a Empresa X",
        "Revisar tickets pendientes",
        "Actualizar pipeline semanal",
        "Preparar reporte mensual",
        "Seguimiento con prospecto calificado",
    ]
    items = []
    for i, title in enumerate(todos):
        items.append({
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "done": random.choice([True, False]),
            "due_date": (datetime.now() + timedelta(days=random.randint(0, 5))).date().isoformat(),
        })
    return {"items": items}


def _sample_quick_actions(widget: Widget, tenant_id: str) -> dict:
    return {
        "actions": [
            {"id": "new_lead", "label": "Nuevo Lead", "icon": "plus", "endpoint": "/api/v1/leads"},
            {"id": "new_ticket", "label": "Nuevo Ticket", "icon": "ticket", "endpoint": "/api/v1/tickets"},
            {"id": "send_email", "label": "Enviar Email", "icon": "mail", "endpoint": "/api/v1/outreach"},
            {"id": "view_reports", "label": "Ver Reportes", "icon": "chart", "endpoint": "/api/v1/reports"},
        ],
    }


_DATA_GENERATORS: dict = {
    WidgetType.KPI: _sample_kpi,
    WidgetType.LINE_CHART: _sample_line_chart,
    WidgetType.BAR_CHART: _sample_bar_chart,
    WidgetType.PIE_CHART: _sample_pie_chart,
    WidgetType.TABLE: _sample_table,
    WidgetType.FUNNEL: _sample_funnel,
    WidgetType.HEATMAP: _sample_heatmap,
    WidgetType.LEADERBOARD: _sample_leaderboard,
    WidgetType.ACTIVITY_FEED: _sample_activity_feed,
    WidgetType.CALENDAR: _sample_calendar,
    WidgetType.TODO_LIST: _sample_todo_list,
    WidgetType.QUICK_ACTIONS: _sample_quick_actions,
}


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class DashboardWidgetManager:
    """In-memory dashboard widget manager supporting multi-tenant layouts."""

    def __init__(self) -> None:
        # key: layout_id -> DashboardLayout
        self._layouts: dict[str, DashboardLayout] = {}
        # secondary index: (tenant_id, user_id) -> layout_id
        self._user_index: dict[tuple[str, str], str] = {}

    # -- Layout CRUD --------------------------------------------------------

    def create_layout(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
    ) -> DashboardLayout:
        """Create a new layout with default widgets."""
        layout_id = str(uuid.uuid4())
        widgets = self._build_default_widgets()
        now = datetime.now()
        layout = DashboardLayout(
            id=layout_id,
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            widgets=widgets,
            created_at=now,
            updated_at=now,
            is_default=True,
        )
        self._layouts[layout_id] = layout
        self._user_index[(tenant_id, user_id)] = layout_id
        return layout

    def get_layout(self, tenant_id: str, user_id: str) -> DashboardLayout:
        """Return the user's layout, creating a default one if none exists."""
        key = (tenant_id, user_id)
        if key not in self._user_index:
            return self.create_layout(tenant_id, user_id, "Mi Dashboard")
        return self._layouts[self._user_index[key]]

    def _get_layout_by_id(self, layout_id: str) -> DashboardLayout | None:
        return self._layouts.get(layout_id)

    # -- Widget operations --------------------------------------------------

    def add_widget(
        self,
        layout_id: str,
        widget_type: WidgetType,
        title: str,
        config: dict | None = None,
        size: WidgetSize = WidgetSize.MEDIUM,
        position: dict | None = None,
    ) -> Widget:
        """Add a widget to an existing layout."""
        layout = self._get_layout_by_id(layout_id)
        if layout is None:
            raise ValueError(f"Layout {layout_id} not found")

        widget_id = str(uuid.uuid4())
        if position is None:
            position = self._next_position(layout)
        widget = Widget(
            id=widget_id,
            type=widget_type,
            title=title,
            config=config or {},
            size=size,
            position=position,
        )
        layout.widgets.append(widget)
        layout.updated_at = datetime.now()
        return widget

    def remove_widget(self, layout_id: str, widget_id: str) -> bool:
        """Remove a widget from a layout. Returns True if found and removed."""
        layout = self._get_layout_by_id(layout_id)
        if layout is None:
            return False
        before = len(layout.widgets)
        layout.widgets = [w for w in layout.widgets if w.id != widget_id]
        removed = len(layout.widgets) < before
        if removed:
            layout.updated_at = datetime.now()
        return removed

    def update_widget(self, layout_id: str, widget_id: str, **kwargs) -> Widget:
        """Update one or more fields on a widget."""
        layout = self._get_layout_by_id(layout_id)
        if layout is None:
            raise ValueError(f"Layout {layout_id} not found")
        widget = self._find_widget(layout, widget_id)
        if widget is None:
            raise ValueError(f"Widget {widget_id} not found")

        allowed = {"title", "description", "config", "size", "position", "visible", "type"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(widget, key, value)
        layout.updated_at = datetime.now()
        return widget

    def reorder_widgets(self, layout_id: str, widget_order: list[str]) -> DashboardLayout:
        """Re-arrange widgets according to the given id order."""
        layout = self._get_layout_by_id(layout_id)
        if layout is None:
            raise ValueError(f"Layout {layout_id} not found")

        by_id = {w.id: w for w in layout.widgets}
        ordered: list[Widget] = []
        for wid in widget_order:
            if wid in by_id:
                ordered.append(by_id.pop(wid))
        # Append any widgets not in the order list at the end
        ordered.extend(by_id.values())

        # Recalculate positions based on new order
        for idx, widget in enumerate(ordered):
            widget.position = {"row": idx // 3, "col": idx % 3}

        layout.widgets = ordered
        layout.updated_at = datetime.now()
        return layout

    # -- Data generation ----------------------------------------------------

    def get_widget_data(self, widget: Widget, tenant_id: str) -> WidgetData:
        """Generate sample data for a widget based on its type."""
        generator = _DATA_GENERATORS.get(widget.type, _sample_kpi)
        now = datetime.now()
        refresh = widget.config.get("refresh_interval_seconds", 60)
        return WidgetData(
            widget_id=widget.id,
            data=generator(widget, tenant_id),
            generated_at=now,
            cached_until=now + timedelta(seconds=refresh) if refresh > 0 else None,
        )

    def get_full_dashboard(self, tenant_id: str, user_id: str) -> dict:
        """Return the complete dashboard: layout + data for every visible widget."""
        layout = self.get_layout(tenant_id, user_id)
        widget_data_list = []
        for widget in layout.widgets:
            if widget.visible:
                wd = self.get_widget_data(widget, tenant_id)
                widget_data_list.append({
                    "widget_id": wd.widget_id,
                    "data": wd.data,
                    "generated_at": wd.generated_at.isoformat(),
                    "cached_until": wd.cached_until.isoformat() if wd.cached_until else None,
                })
        return {
            "layout": {
                "id": layout.id,
                "tenant_id": layout.tenant_id,
                "user_id": layout.user_id,
                "name": layout.name,
                "is_default": layout.is_default,
                "created_at": layout.created_at.isoformat(),
                "updated_at": layout.updated_at.isoformat(),
                "widgets": [
                    {
                        "id": w.id,
                        "type": w.type.value,
                        "title": w.title,
                        "description": w.description,
                        "config": w.config,
                        "size": w.size.value,
                        "position": w.position,
                        "visible": w.visible,
                    }
                    for w in layout.widgets
                ],
            },
            "widget_data": widget_data_list,
        }

    # -- Layout management --------------------------------------------------

    def reset_to_default(self, layout_id: str) -> DashboardLayout:
        """Replace all widgets with the default set."""
        layout = self._get_layout_by_id(layout_id)
        if layout is None:
            raise ValueError(f"Layout {layout_id} not found")
        layout.widgets = self._build_default_widgets()
        layout.is_default = True
        layout.updated_at = datetime.now()
        return layout

    def clone_layout(self, layout_id: str, new_name: str) -> DashboardLayout:
        """Deep-copy an existing layout under a new name and id."""
        source = self._get_layout_by_id(layout_id)
        if source is None:
            raise ValueError(f"Layout {layout_id} not found")

        new_id = str(uuid.uuid4())
        now = datetime.now()
        cloned_widgets = []
        for w in source.widgets:
            cloned_widgets.append(Widget(
                id=str(uuid.uuid4()),
                type=w.type,
                title=w.title,
                description=w.description,
                config=copy.deepcopy(w.config),
                size=w.size,
                position=dict(w.position),
                visible=w.visible,
            ))

        cloned = DashboardLayout(
            id=new_id,
            tenant_id=source.tenant_id,
            user_id=source.user_id,
            name=new_name,
            widgets=cloned_widgets,
            created_at=now,
            updated_at=now,
            is_default=False,
        )
        self._layouts[new_id] = cloned
        return cloned

    def get_widget_catalog(self) -> list[dict]:
        """Return the full widget catalog for the UI."""
        return copy.deepcopy(WIDGET_CATALOG)

    # -- Helpers ------------------------------------------------------------

    @staticmethod
    def _build_default_widgets() -> list[Widget]:
        widgets = []
        for spec in DEFAULT_WIDGETS:
            widgets.append(Widget(
                id=str(uuid.uuid4()),
                type=spec["type"],
                title=spec["title"],
                description=spec.get("description", ""),
                config=copy.deepcopy(spec.get("config", {})),
                size=spec["size"],
                position=dict(spec["position"]),
            ))
        return widgets

    @staticmethod
    def _find_widget(layout: DashboardLayout, widget_id: str) -> Widget | None:
        for w in layout.widgets:
            if w.id == widget_id:
                return w
        return None

    @staticmethod
    def _next_position(layout: DashboardLayout) -> dict:
        if not layout.widgets:
            return {"row": 0, "col": 0}
        max_row = max(w.position.get("row", 0) for w in layout.widgets)
        max_col = max(
            w.position.get("col", 0)
            for w in layout.widgets
            if w.position.get("row", 0) == max_row
        )
        next_col = max_col + 1
        if next_col >= 3:
            return {"row": max_row + 1, "col": 0}
        return {"row": max_row, "col": next_col}


# Module-level singleton
widget_manager = DashboardWidgetManager()
