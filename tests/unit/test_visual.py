"""Tests for visual components and contextual guide."""

from xcapitsff.assistant.visual import (
    VisualType, kpi_card, table, score_card, funnel_chart, bar_chart,
    form, progress_bar, alert, success, error, empty_state,
    build_lead_card, build_ticket_card, build_dashboard_visuals,
)
from xcapitsff.assistant.guide import ContextualGuide, UserContext, Suggestion


# === Visual Components ===

def test_kpi_card():
    c = kpi_card("Total Leads", 150, "📊")
    assert c.type == VisualType.KPI_CARD
    assert c.data["value"] == 150


def test_table():
    t = table("Leads", ["Nombre", "Score"], [["Acme", 75], ["Corp", 50]])
    assert t.type == VisualType.TABLE
    assert len(t.data["rows"]) == 2


def test_score_card():
    sc = score_card("Lead Score", 75, 100, "HOT", "#22c55e")
    assert sc.data["percentage"] == 75.0
    assert sc.data["classification"] == "HOT"


def test_funnel_chart():
    fc = funnel_chart("Pipeline", [
        {"label": "Nuevos", "count": 50},
        {"label": "Calificados", "count": 30},
    ])
    assert fc.type == VisualType.CHART_FUNNEL
    assert len(fc.data["stages"]) == 2


def test_form():
    f = form("Crear Lead", [
        {"name": "company", "label": "Empresa", "type": "text", "required": True},
    ], "/api/v1/leads/")
    assert f.type == VisualType.FORM
    assert f.data["submit_endpoint"] == "/api/v1/leads/"


def test_progress_bar():
    pb = progress_bar("Onboarding", 3, 8)
    assert pb.data["percentage"] == 37.5


def test_alert():
    a = alert("SLA por vencer", "warning")
    assert a.data["level"] == "warning"


def test_success():
    s = success("Lead creado exitosamente")
    assert s.type == VisualType.SUCCESS


def test_error():
    e = error("No se pudo crear el lead", "Campo email inválido")
    assert e.type == VisualType.ERROR


def test_empty_state():
    es = empty_state("No hay leads", "Importá datos para empezar", "Importar", "/api/v1/leads/import")
    assert es.type == VisualType.EMPTY_STATE


def test_build_lead_card_hot():
    card = build_lead_card({"id": 1, "company_name": "Acme", "score_icp": 80, "c_level": True, "region": "LATAM", "afinidad": "HIGH"})
    assert card.data["classification"] == "HOT"
    assert card.data["color"] == "#22c55e"


def test_build_lead_card_cold():
    card = build_lead_card({"id": 2, "score_icp": 15})
    assert card.data["classification"] == "COLD"


def test_build_ticket_card():
    card = build_ticket_card({"id": 1, "subject": "Error", "priority": "urgent", "category": "technical"})
    assert card.data["priority"] == "urgent"
    assert card.data["color"] == "#ef4444"


def test_build_dashboard_visuals():
    dashboard = {"sales": {"total_leads": 50, "conversion_rate": 12.5, "avg_score": 55, "funnel": [{"stage": "raw", "count": 20}]}, "support": {"open_tickets": 5}}
    visuals = build_dashboard_visuals(dashboard)
    assert len(visuals) >= 4  # at least 4 KPI cards
    assert any(v.type == VisualType.KPI_CARD for v in visuals)


# === Contextual Guide ===

def test_new_user_suggestions():
    guide = ContextualGuide()
    ctx = UserContext(tenant_id="t1", user_id="u1", wizard_completed=False, leads_count=0)
    suggestions = guide.get_suggestions(ctx)
    assert len(suggestions) >= 1
    assert any("wizard" in s.text.lower() or "configuración" in s.text.lower() for s in suggestions)


def test_user_with_leads_no_outreach():
    guide = ContextualGuide()
    ctx = UserContext(tenant_id="t1", user_id="u1", wizard_completed=True, leads_count=20, has_sent_outreach=False)
    suggestions = guide.get_suggestions(ctx)
    assert any("outreach" in s.text.lower() for s in suggestions)


def test_low_health_score():
    guide = ContextualGuide()
    ctx = UserContext(tenant_id="t1", user_id="u1", wizard_completed=True, leads_count=10, health_score=40)
    suggestions = guide.get_suggestions(ctx)
    assert any("health" in s.text.lower() for s in suggestions)


def test_max_5_suggestions():
    guide = ContextualGuide()
    ctx = UserContext(tenant_id="t1", user_id="u1", wizard_completed=False, leads_count=0, health_score=30, days_since_signup=3)
    suggestions = guide.get_suggestions(ctx)
    assert len(suggestions) <= 5


def test_section_help():
    guide = ContextualGuide()
    help_data = guide.get_section_help("leads")
    assert help_data["title"] == "Leads"
    assert len(help_data["tips"]) >= 2


def test_empty_state_leads():
    guide = ContextualGuide()
    msg = guide.get_empty_state_message("leads")
    assert "lead" in msg["title"].lower()
    assert len(msg["actions"]) >= 2


def test_empty_state_unknown():
    guide = ContextualGuide()
    msg = guide.get_empty_state_message("unknown_section")
    assert "datos" in msg["title"].lower() or "unknown" in msg["title"].lower()


def test_suggestions_sorted_by_priority():
    guide = ContextualGuide()
    ctx = UserContext(tenant_id="t1", user_id="u1", wizard_completed=True, leads_count=20, health_score=40, current_section="leads")
    suggestions = guide.get_suggestions(ctx)
    priorities = [s.priority for s in suggestions]
    assert priorities == sorted(priorities)
