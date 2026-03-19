"""Action executor — maps recognised intents to API actions and returns rich visuals.

Every action returns an :class:`ActionResult` that contains a list of
:class:`VisualComponent` objects the frontend renders (cards, tables, charts,
kanban boards, forms, etc.) together with a user-facing message in Spanish and
contextual suggestions for the next step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .intent import Intent, IntentMatch
from .visual import (
    VisualComponent,
    action_card,
    bar_chart,
    build_lead_card,
    chat_card,
    form,
    funnel_chart,
    kanban,
    kpi_card,
    list_component,
    progress_bar,
    score_card,
    table,
)


@dataclass
class ActionResult:
    """Result produced by executing an action for a recognised intent."""

    success: bool
    action_taken: str
    result_data: dict = field(default_factory=dict)
    visual_type: str = "text"  # card | table | chart | text | form | kanban
    message: str = ""
    next_suggestions: list[str] = field(default_factory=list)
    visual_components: list[VisualComponent] = field(default_factory=list)


class ActionExecutor:
    """Execute the action associated with a recognised intent.

    In a production deployment each handler would call the real internal
    services (database, pipelines, scoring engine, etc.).  Here we provide
    representative responses so the conversation flow is fully functional
    without external dependencies.
    """

    def execute(self, intent_match: IntentMatch, context: dict | None = None) -> ActionResult:
        """Dispatch *intent_match* to the appropriate handler."""
        context = context or {}
        handler = _HANDLERS.get(intent_match.intent, _handle_unknown)
        return handler(intent_match, context)


# ---------------------------------------------------------------------------
# Individual intent handlers
# ---------------------------------------------------------------------------


def _handle_greeting(intent: IntentMatch, context: dict) -> ActionResult:
    # Welcome card (as a chat_card)
    welcome = chat_card(
        "XcapitSFF Assistant",
        (
            "Hola! Soy tu asistente de XcapitSFF. "
            "Estoy aqui para ayudarte a gestionar tus ventas, soporte y mucho mas."
        ),
    )

    # KPI summary
    kpis = [
        kpi_card("Leads Activos", 37, icon="people", trend="+5 esta semana", color="#3b82f6"),
        kpi_card("Tickets Abiertos", 14, icon="ticket", color="#f59e0b"),
        kpi_card("Tasa de Conversion", "17%", icon="trend_up", color="#22c55e"),
        kpi_card("Satisfaccion", "4.5/5", icon="star", color="#8b5cf6"),
    ]

    # Quickstart action cards
    quickstart = [
        action_card(
            "Ver Dashboard",
            "Revisa tus metricas y KPIs en tiempo real",
            "Abrir", "/api/v1/dashboard", icon="chart",
        ),
        action_card(
            "Crear un Lead",
            "Registra un nuevo prospecto en el pipeline",
            "Crear", "/api/v1/leads", icon="add_person",
        ),
        action_card(
            "Ver Tickets",
            "Consulta los tickets de soporte abiertos",
            "Ver", "/api/v1/tickets", icon="support",
        ),
        action_card(
            "Buscar",
            "Busca leads, tickets o clientes rapidamente",
            "Buscar", "/api/v1/search", icon="search",
        ),
    ]

    components = [welcome] + kpis + quickstart

    return ActionResult(
        success=True,
        action_taken="greeting",
        result_data={"welcome": True},
        visual_type="card",
        message=(
            "Hola! Soy tu asistente de XcapitSFF. "
            "Estoy aqui para ayudarte a gestionar tus ventas, soporte y mucho mas. "
            "Que te gustaria hacer?"
        ),
        next_suggestions=[
            "Ver el dashboard",
            "Crear un nuevo lead",
            "Ver mis tickets",
            "Buscar un cliente",
        ],
        visual_components=components,
    )


def _handle_help(intent: IntentMatch, context: dict) -> ActionResult:
    # Sales category
    sales_cards = [
        action_card("Crear un Lead", "Registra un nuevo prospecto", "Crear", "/api/v1/leads", icon="add_person"),
        action_card("Ver Pipeline / Kanban", "Visualiza tu embudo de ventas", "Ver", "/api/v1/kanban", icon="kanban"),
        action_card("Calificar Leads", "Scoring IA de tus prospectos", "Calificar", "/api/v1/leads/qualify", icon="score"),
        action_card("Componer Outreach", "Redacta mensajes personalizados", "Redactar", "/api/v1/outreach", icon="email"),
        action_card("Iniciar Campana", "Lanza una secuencia de contacto", "Iniciar", "/api/v1/campaigns", icon="campaign"),
        action_card("Ver Predicciones", "Pronosticos de ingresos y conversiones", "Ver", "/api/v1/predictions", icon="forecast"),
    ]

    # Soporte category
    soporte_cards = [
        action_card("Crear un Ticket", "Abre un nuevo caso de soporte", "Crear", "/api/v1/tickets", icon="ticket"),
        action_card("Ver Tickets Abiertos", "Consulta los tickets pendientes", "Ver", "/api/v1/tickets?status=open", icon="list"),
        action_card("Buscar en KB", "Encuentra articulos en la base de conocimiento", "Buscar", "/api/v1/kb/search", icon="search"),
        action_card("Crear Articulo KB", "Agrega conocimiento al sistema", "Crear", "/api/v1/kb/articles", icon="article"),
    ]

    # Analytics category
    analytics_cards = [
        action_card("Ver Dashboard", "Metricas y KPIs en tiempo real", "Ver", "/api/v1/dashboard", icon="chart"),
        action_card("Ver Analiticas", "Estadisticas detalladas y reportes", "Ver", "/api/v1/analytics", icon="analytics"),
        action_card("Health Score", "Puntuacion de salud del sistema", "Ver", "/api/v1/health", icon="health"),
    ]

    # Configuracion category
    config_cards = [
        action_card("Importar Datos", "Carga datos desde CSV o Excel", "Importar", "/api/v1/import", icon="upload"),
        action_card("Exportar Datos", "Descarga tus datos en varios formatos", "Exportar", "/api/v1/export", icon="download"),
        action_card("Configuracion", "Ajustes del sistema y preferencias", "Configurar", "/api/v1/settings", icon="settings"),
        action_card("Automatizaciones", "Reglas y flujos de trabajo", "Ver", "/api/v1/automations", icon="automation"),
    ]

    components = sales_cards + soporte_cards + analytics_cards + config_cards

    return ActionResult(
        success=True,
        action_taken="help",
        result_data={
            "categories": {
                "Ventas": [c.to_dict() for c in sales_cards],
                "Soporte": [c.to_dict() for c in soporte_cards],
                "Analytics": [c.to_dict() for c in analytics_cards],
                "Configuracion": [c.to_dict() for c in config_cards],
            },
        },
        visual_type="card",
        message="Estas son las cosas que puedo hacer por ti, organizadas por categoria:",
        next_suggestions=[
            "Crear un lead",
            "Ver el dashboard",
            "Crear un ticket",
        ],
        visual_components=components,
    )


def _handle_create_lead(intent: IntentMatch, context: dict) -> ActionResult:
    params = intent.extracted_params

    # If we have enough data, create the lead and return a score_card
    if params.get("company") or params.get("email"):
        lead_data = {
            "id": 1001,
            "company_name": params.get("company", "Sin nombre"),
            "contact_name": params.get("search_query", "Contacto"),
            "contact_email": params.get("email", ""),
            "region": "LATAM",
            "c_level": False,
            "afinidad": "media",
            "stage": "new",
            "score_icp": 62,
        }

        # Use build_lead_card for a rich score_card with ICP classification
        lead_card = build_lead_card(lead_data)

        return ActionResult(
            success=True,
            action_taken="create_lead",
            result_data={"lead": lead_data},
            visual_type="card",
            message=(
                f"Lead creado exitosamente para {lead_data['company_name']}. "
                f"Score ICP: {lead_data['score_icp']}/100 — clasificacion: "
                f"{lead_card.data['classification']}."
            ),
            next_suggestions=[
                "Calificar este lead",
                "Ver el pipeline",
                "Componer outreach",
            ],
            visual_components=[lead_card],
        )

    # Not enough data — show a form with all lead fields
    form_fields = [
        {"name": "company_name", "label": "Nombre de la empresa", "type": "text", "required": True},
        {"name": "contact_name", "label": "Nombre del contacto", "type": "text", "required": True},
        {"name": "contact_email", "label": "Email de contacto", "type": "email", "required": True},
        {"name": "region", "label": "Region", "type": "select",
         "options": ["LATAM", "NA", "EU", "APAC"], "required": True},
        {"name": "c_level", "label": "Es C-Level?", "type": "select",
         "options": ["Si", "No"], "required": True},
        {"name": "afinidad", "label": "Afinidad", "type": "select",
         "options": ["alta", "media", "baja"], "required": True},
    ]

    lead_form = form(
        "Nuevo Lead",
        fields=form_fields,
        submit_endpoint="/api/v1/leads",
        submit_label="Crear Lead",
    )

    return ActionResult(
        success=True,
        action_taken="create_lead_form",
        result_data={"form_fields": form_fields},
        visual_type="form",
        message="Para crear un nuevo lead, completa los siguientes datos:",
        next_suggestions=[
            "Importar leads desde CSV",
            "Ver el pipeline",
        ],
        visual_components=[lead_form],
    )


def _handle_list_leads(intent: IntentMatch, context: dict) -> ActionResult:
    sample_leads = [
        {"id": 1, "company": "TechCorp", "contact": "Ana Garcia", "score": 87, "stage": "qualified", "region": "LATAM"},
        {"id": 2, "company": "FinanceHub", "contact": "Carlos Lopez", "score": 72, "stage": "contacted", "region": "NA"},
        {"id": 3, "company": "DataPro", "contact": "Maria Rodriguez", "score": 93, "stage": "proposal", "region": "EU"},
        {"id": 4, "company": "CloudNet", "contact": "Juan Martinez", "score": 61, "stage": "new", "region": "LATAM"},
        {"id": 5, "company": "SalesForce Latam", "contact": "Laura Perez", "score": 45, "stage": "new", "region": "LATAM"},
    ]

    leads_table = table(
        "Leads en Pipeline",
        headers=["Empresa", "Contacto", "Score", "Stage", "Region"],
        rows=[
            [ld["company"], ld["contact"], ld["score"], ld["stage"], ld["region"]]
            for ld in sample_leads
        ],
        actions=["Ver detalle", "Calificar", "Outreach"],
    )

    return ActionResult(
        success=True,
        action_taken="list_leads",
        result_data={"leads": sample_leads, "total": len(sample_leads)},
        visual_type="table",
        message=f"Encontre {len(sample_leads)} leads en tu pipeline.",
        next_suggestions=[
            "Calificar un lead",
            "Ver el kanban",
            "Crear un nuevo lead",
            "Exportar leads",
        ],
        visual_components=[leads_table],
    )


def _handle_qualify_lead(intent: IntentMatch, context: dict) -> ActionResult:
    lead_id = None
    ids = intent.extracted_params.get("ids", [])
    if ids:
        lead_id = ids[0]
    elif context.get("current_lead_id"):
        lead_id = context["current_lead_id"]

    if lead_id is None:
        return ActionResult(
            success=True,
            action_taken="qualify_lead_ask",
            result_data={},
            visual_type="text",
            message="Cual lead quieres calificar? Dame el ID o nombre de la empresa.",
            next_suggestions=["Ver leads", "Buscar un lead"],
            visual_components=[],
        )

    factors = {
        "Tamano de empresa": 9,
        "Industria target": 8,
        "Nivel de contacto": 9,
        "Engagement": 7,
        "Presupuesto estimado": 8,
    }
    total_score = 85

    # Score card with overall grade
    main_card = score_card(
        f"Lead #{lead_id} — ICP Score",
        score=total_score,
        max_score=100,
        classification="A",
        color="#22c55e",
        details=[
            {"label": k, "value": f"{v}/10"} for k, v in factors.items()
        ],
    )

    return ActionResult(
        success=True,
        action_taken="qualify_lead",
        result_data={
            "score_card": {
                "lead_id": lead_id,
                "score_icp": total_score,
                "grade": "A",
                "factors": factors,
                "recommendation": "Lead altamente calificado. Se recomienda agendar reunion.",
            },
        },
        visual_type="card",
        message=(
            f"El lead #{lead_id} obtuvo un score de {total_score}/100 (Grado A). "
            "Lead altamente calificado. Se recomienda agendar reunion."
        ),
        next_suggestions=[
            "Componer outreach para este lead",
            "Agendar una reunion",
            "Ver el pipeline",
        ],
        visual_components=[main_card],
    )


def _handle_view_kanban(intent: IntentMatch, context: dict) -> ActionResult:
    columns_data = [
        {"id": "new", "label": "Nuevos", "count": 12, "color": "#3b82f6"},
        {"id": "contacted", "label": "Contactados", "count": 8, "color": "#f59e0b"},
        {"id": "qualified", "label": "Calificados", "count": 5, "color": "#10b981"},
        {"id": "proposal", "label": "Propuesta", "count": 3, "color": "#8b5cf6"},
        {"id": "negotiation", "label": "Negociacion", "count": 2, "color": "#ef4444"},
        {"id": "won", "label": "Ganados", "count": 7, "color": "#22c55e"},
    ]

    sample_cards = [
        {"id": "1", "column": "new", "title": "CloudNet", "subtitle": "Juan Martinez — Score 61"},
        {"id": "5", "column": "new", "title": "SalesForce Latam", "subtitle": "Laura Perez — Score 45"},
        {"id": "2", "column": "contacted", "title": "FinanceHub", "subtitle": "Carlos Lopez — Score 72"},
        {"id": "1b", "column": "qualified", "title": "TechCorp", "subtitle": "Ana Garcia — Score 87"},
        {"id": "3", "column": "proposal", "title": "DataPro", "subtitle": "Maria Rodriguez — Score 93"},
    ]

    kanban_board = kanban(
        "Pipeline de Ventas",
        columns=columns_data,
        cards=sample_cards,
    )

    return ActionResult(
        success=True,
        action_taken="view_kanban",
        result_data={"columns": columns_data, "total_leads": 37},
        visual_type="kanban",
        message="Aqui tienes tu tablero Kanban con 37 leads distribuidos en 6 etapas.",
        next_suggestions=[
            "Crear un nuevo lead",
            "Ver leads calificados",
            "Ver dashboard completo",
        ],
        visual_components=[kanban_board],
    )


def _handle_view_pipeline(intent: IntentMatch, context: dict) -> ActionResult:
    stages = [
        {"label": "Nuevos", "count": 12, "color": "#3b82f6"},
        {"label": "Contactados", "count": 8, "color": "#f59e0b"},
        {"label": "Calificados", "count": 5, "color": "#10b981"},
        {"label": "Propuesta", "count": 3, "color": "#8b5cf6"},
        {"label": "Ganados", "count": 2, "color": "#22c55e"},
    ]

    funnel = funnel_chart("Embudo de Ventas", stages)
    conversion_kpi = kpi_card("Tasa de Conversion", "17%", icon="trend_up", color="#22c55e")

    return ActionResult(
        success=True,
        action_taken="view_pipeline",
        result_data={"funnel": stages, "conversion_rate": 17},
        visual_type="chart",
        message="Tu embudo de ventas muestra una tasa de conversion del 17%.",
        next_suggestions=[
            "Ver el kanban",
            "Ver leads hot",
            "Ver predicciones",
        ],
        visual_components=[conversion_kpi, funnel],
    )


def _handle_view_dashboard(intent: IntentMatch, context: dict) -> ActionResult:
    dashboard_data = {
        "sales": {"total_leads": 37, "avg_score": 72, "conversion_rate": 17},
        "support": {"open_tickets": 14, "avg_resolution_hours": 4.2, "satisfaction": 4.5},
        "activity": {"events_today": 128, "active_campaigns": 3},
    }

    # KPI cards
    kpis = [
        kpi_card("Total Leads", 37, icon="people", trend="+5 esta semana", color="#3b82f6"),
        kpi_card("Tickets Abiertos", 14, icon="ticket", color="#f59e0b"),
        kpi_card("Tasa de Conversion", "17%", icon="trend_up", color="#22c55e"),
        kpi_card("Score Promedio", 72, icon="star", color="#8b5cf6"),
        kpi_card("Satisfaccion", "4.5/5", icon="heart", color="#ec4899"),
        kpi_card("Campanas Activas", 3, icon="campaign", color="#6366f1"),
    ]

    # Funnel chart
    funnel = funnel_chart("Pipeline de Ventas", [
        {"label": "Nuevos", "count": 12, "color": "#3b82f6"},
        {"label": "Contactados", "count": 8, "color": "#f59e0b"},
        {"label": "Calificados", "count": 5, "color": "#10b981"},
        {"label": "Propuesta", "count": 3, "color": "#8b5cf6"},
        {"label": "Ganados", "count": 2, "color": "#22c55e"},
    ])

    components = kpis + [funnel]

    return ActionResult(
        success=True,
        action_taken="view_dashboard",
        result_data=dashboard_data,
        visual_type="card",
        message=(
            "Dashboard actualizado: 37 leads activos, 14 tickets abiertos, "
            "tasa de conversion 17%, satisfaccion 4.5/5."
        ),
        next_suggestions=[
            "Ver leads hot",
            "Ver tickets urgentes",
            "Ver predicciones",
        ],
        visual_components=components,
    )


def _handle_create_ticket(intent: IntentMatch, context: dict) -> ActionResult:
    params = intent.extracted_params

    if params.get("search_query"):
        # Ticket created — return an action_card with routing info
        ticket = {
            "id": 501,
            "subject": params["search_query"],
            "status": "open",
            "priority": "medium",
            "category": "general",
            "assigned_to": "Soporte Nivel 1",
        }

        ticket_card = action_card(
            f"Ticket #{ticket['id']}: {ticket['subject']}",
            (
                f"Categoria: {ticket['category']} | "
                f"Prioridad: {ticket['priority']} | "
                f"Agente: {ticket['assigned_to']}"
            ),
            "Ver ticket",
            f"/api/v1/tickets/{ticket['id']}",
            icon="ticket",
        )

        return ActionResult(
            success=True,
            action_taken="create_ticket",
            result_data={"ticket": ticket},
            visual_type="card",
            message=(
                f"Ticket #{ticket['id']} creado: \"{ticket['subject']}\". "
                f"Asignado a {ticket['assigned_to']} con prioridad {ticket['priority']}."
            ),
            next_suggestions=[
                "Ver el ticket",
                "Buscar en KB",
                "Responder al ticket",
            ],
            visual_components=[ticket_card],
        )

    # No params — show a form for ticket creation
    ticket_form = form(
        "Nuevo Ticket de Soporte",
        fields=[
            {"name": "subject", "label": "Asunto", "type": "text", "required": True},
            {"name": "description", "label": "Descripcion", "type": "textarea", "required": True},
            {"name": "priority", "label": "Prioridad", "type": "select",
             "options": ["low", "medium", "high", "critical"], "required": True},
            {"name": "category", "label": "Categoria", "type": "select",
             "options": ["bug", "feature", "question", "billing"], "required": False},
        ],
        submit_endpoint="/api/v1/tickets",
        submit_label="Crear Ticket",
    )

    return ActionResult(
        success=True,
        action_taken="create_ticket_form",
        result_data={},
        visual_type="form",
        message="Para crear un ticket de soporte, completa los siguientes datos:",
        next_suggestions=[
            "Ver tickets abiertos",
            "Buscar en KB",
        ],
        visual_components=[ticket_form],
    )


def _handle_list_tickets(intent: IntentMatch, context: dict) -> ActionResult:
    sample_tickets = [
        {"id": 100, "subject": "Error en login", "status": "open", "priority": "high"},
        {"id": 101, "subject": "Consulta sobre facturacion", "status": "open", "priority": "medium"},
        {"id": 102, "subject": "Solicitud de nueva feature", "status": "in_progress", "priority": "low"},
        {"id": 103, "subject": "Integracion con Slack falla", "status": "open", "priority": "high"},
    ]

    tickets_table = table(
        "Tickets Activos",
        headers=["ID", "Asunto", "Estado", "Prioridad"],
        rows=[
            [t["id"], t["subject"], t["status"], t["priority"]]
            for t in sample_tickets
        ],
        actions=["Ver detalle", "Responder", "Escalar"],
    )

    return ActionResult(
        success=True,
        action_taken="list_tickets",
        result_data={"tickets": sample_tickets, "total": len(sample_tickets)},
        visual_type="table",
        message=f"Hay {len(sample_tickets)} tickets activos.",
        next_suggestions=[
            "Ver un ticket especifico",
            "Crear un nuevo ticket",
            "Ver tickets urgentes",
        ],
        visual_components=[tickets_table],
    )


def _handle_view_ticket(intent: IntentMatch, context: dict) -> ActionResult:
    ids = intent.extracted_params.get("ids", [])
    ticket_id = ids[0] if ids else context.get("current_ticket_id", 100)
    ticket = {
        "id": ticket_id,
        "subject": "Error en login",
        "description": "El usuario no puede iniciar sesion desde la app movil.",
        "status": "open",
        "priority": "high",
        "created_at": "2026-03-18T10:30:00Z",
        "assigned_to": "Soporte Nivel 2",
    }

    ticket_card = action_card(
        f"Ticket #{ticket_id}: {ticket['subject']}",
        (
            f"Estado: {ticket['status']} | Prioridad: {ticket['priority']} | "
            f"Agente: {ticket['assigned_to']}\n{ticket['description']}"
        ),
        "Responder",
        f"/api/v1/tickets/{ticket_id}/reply",
        icon="ticket",
    )

    return ActionResult(
        success=True,
        action_taken="view_ticket",
        result_data={"ticket": ticket},
        visual_type="card",
        message=f"Ticket #{ticket_id}: \"{ticket['subject']}\" — Estado: abierto, Prioridad: alta.",
        next_suggestions=[
            "Responder al ticket",
            "Escalar el ticket",
            "Buscar en KB",
        ],
        visual_components=[ticket_card],
    )


def _handle_compose_outreach(intent: IntentMatch, context: dict) -> ActionResult:
    lead_id = None
    ids = intent.extracted_params.get("ids", [])
    if ids:
        lead_id = ids[0]
    elif context.get("current_lead_id"):
        lead_id = context["current_lead_id"]

    draft_body = (
        "Hola [Nombre],\n\n"
        "Espero que estes muy bien. Me comunico porque creo que "
        "nuestra solucion puede aportar valor a [Empresa].\n\n"
        "Me encantaria agendar una breve reunion para mostrarte "
        "como podemos ayudarte.\n\n"
        "Saludos cordiales."
    )

    draft = {
        "lead_id": lead_id,
        "subject": "Oportunidad de colaboracion — XcapitSFF",
        "body": draft_body,
        "tone": "profesional",
        "channel": "email",
    }

    outreach_card = chat_card(
        "Borrador de Outreach",
        f"Asunto: {draft['subject']}\n\n{draft_body}",
        confidence=0.92,
    )

    return ActionResult(
        success=True,
        action_taken="compose_outreach",
        result_data={"draft": draft},
        visual_type="card",
        message="He preparado un borrador de outreach. Revisalo y ajustalo antes de enviar.",
        next_suggestions=[
            "Enviar el mensaje",
            "Cambiar el tono",
            "Agendar una reunion",
        ],
        visual_components=[outreach_card],
    )


def _handle_import_data(intent: IntentMatch, context: dict) -> ActionResult:
    import_form = form(
        "Importar Datos",
        fields=[
            {"name": "file", "label": "Archivo", "type": "file", "required": True},
            {"name": "entity_type", "label": "Tipo de entidad", "type": "select",
             "options": ["leads", "contacts", "tickets", "customers"], "required": True},
            {"name": "duplicate_handling", "label": "Manejo de duplicados", "type": "select",
             "options": ["skip", "update", "create_new"], "required": False},
        ],
        submit_endpoint="/api/v1/import",
        submit_label="Importar",
    )

    return ActionResult(
        success=True,
        action_taken="import_data_form",
        result_data={"supported_formats": ["CSV", "Excel (.xlsx)", "JSON"]},
        visual_type="form",
        message="Para importar datos, selecciona el archivo y el tipo de entidad. Formatos soportados: CSV, Excel, JSON.",
        next_suggestions=[
            "Ver formato de CSV esperado",
            "Ver leads importados",
        ],
        visual_components=[import_form],
    )


def _handle_export_data(intent: IntentMatch, context: dict) -> ActionResult:
    export_cards = [
        action_card("Exportar Leads", "37 leads disponibles — CSV, Excel, JSON", "Exportar", "/api/v1/export/leads", icon="download"),
        action_card("Exportar Tickets", "14 tickets disponibles — CSV, Excel", "Exportar", "/api/v1/export/tickets", icon="download"),
        action_card("Exportar Clientes", "52 clientes disponibles — CSV, Excel, JSON", "Exportar", "/api/v1/export/customers", icon="download"),
    ]

    return ActionResult(
        success=True,
        action_taken="export_data_form",
        result_data={
            "available_exports": [
                {"entity": "leads", "count": 37, "formats": ["CSV", "Excel", "JSON"]},
                {"entity": "tickets", "count": 14, "formats": ["CSV", "Excel"]},
                {"entity": "customers", "count": 52, "formats": ["CSV", "Excel", "JSON"]},
            ],
        },
        visual_type="card",
        message="Que datos quieres exportar? Estos son los disponibles:",
        next_suggestions=[
            "Exportar leads",
            "Exportar tickets",
            "Exportar clientes",
        ],
        visual_components=export_cards,
    )


def _handle_view_analytics(intent: IntentMatch, context: dict) -> ActionResult:
    analytics = {
        "leads_this_month": 23,
        "leads_last_month": 18,
        "conversion_rate": 17,
        "avg_deal_cycle_days": 14,
        "top_sources": [
            {"source": "Organico", "count": 10},
            {"source": "Referido", "count": 7},
            {"source": "Outbound", "count": 6},
        ],
    }

    # Bar chart for lead sources
    sources_chart = bar_chart(
        "Leads por Fuente",
        labels=["Organico", "Referido", "Outbound"],
        values=[10, 7, 6],
        colors=["#3b82f6", "#22c55e", "#f59e0b"],
    )

    # KPI cards
    kpis = [
        kpi_card("Leads Este Mes", 23, icon="trend_up", trend="+28% vs mes anterior", color="#22c55e"),
        kpi_card("Leads Mes Anterior", 18, icon="people", color="#6b7280"),
        kpi_card("Tasa de Conversion", "17%", icon="funnel", color="#3b82f6"),
        kpi_card("Ciclo Promedio", "14 dias", icon="clock", color="#8b5cf6"),
    ]

    components = kpis + [sources_chart]

    return ActionResult(
        success=True,
        action_taken="view_analytics",
        result_data={"analytics": analytics},
        visual_type="chart",
        message="Analiticas del mes: 23 leads nuevos (+28% vs mes anterior), conversion 17%.",
        next_suggestions=[
            "Ver predicciones",
            "Ver dashboard",
            "Exportar reporte",
        ],
        visual_components=components,
    )


def _handle_view_health_score(intent: IntentMatch, context: dict) -> ActionResult:
    health = {
        "overall_grade": "B+",
        "overall_score": 82,
        "dimensions": {
            "Calidad de datos": {"score": 90, "grade": "A"},
            "Actividad de ventas": {"score": 78, "grade": "B"},
            "Soporte al cliente": {"score": 85, "grade": "A-"},
            "Engagement": {"score": 72, "grade": "B-"},
            "Automatizaciones": {"score": 65, "grade": "C+"},
        },
        "recommendations": [
            "Mejorar automatizaciones de seguimiento",
            "Incrementar actividad de outreach",
            "Implementar workflows de nurturing para leads frios",
        ],
    }

    # Main score card
    main_score = score_card(
        "Health Score General",
        score=82,
        max_score=100,
        classification="B+",
        color="#22c55e",
        details=[
            {"label": "Calidad de datos", "value": "90/100 (A)"},
            {"label": "Actividad de ventas", "value": "78/100 (B)"},
            {"label": "Soporte al cliente", "value": "85/100 (A-)"},
            {"label": "Engagement", "value": "72/100 (B-)"},
            {"label": "Automatizaciones", "value": "65/100 (C+)"},
        ],
    )

    # Progress bars per category
    progress_bars = [
        progress_bar("Calidad de datos", 90, 100, label="A"),
        progress_bar("Actividad de ventas", 78, 100, label="B"),
        progress_bar("Soporte al cliente", 85, 100, label="A-"),
        progress_bar("Engagement", 72, 100, label="B-"),
        progress_bar("Automatizaciones", 65, 100, label="C+"),
    ]

    # Recommendations list
    recommendations = list_component(
        "Recomendaciones",
        items=health["recommendations"],
    )

    components = [main_score] + progress_bars + [recommendations]

    return ActionResult(
        success=True,
        action_taken="view_health_score",
        result_data={"health": health},
        visual_type="card",
        message="Tu puntaje de salud general es B+ (82/100). Areas de mejora: automatizaciones y engagement.",
        next_suggestions=[
            "Ver recomendaciones detalladas",
            "Configurar automatizaciones",
            "Ver dashboard",
        ],
        visual_components=components,
    )


def _handle_configure_settings(intent: IntentMatch, context: dict) -> ActionResult:
    settings_cards = [
        action_card("General", "Nombre, idioma, zona horaria", "Configurar", "/api/v1/settings/general", icon="settings"),
        action_card("Ventas", "Pipeline, scoring, outreach", "Configurar", "/api/v1/settings/sales", icon="sales"),
        action_card("Soporte", "SLA, categorias, asignacion", "Configurar", "/api/v1/settings/support", icon="support"),
        action_card("Integraciones", "Email, Slack, CRM", "Configurar", "/api/v1/settings/integrations", icon="integration"),
        action_card("Equipo", "Usuarios, roles, permisos", "Configurar", "/api/v1/settings/team", icon="team"),
    ]

    return ActionResult(
        success=True,
        action_taken="configure_settings",
        result_data={
            "sections": [
                {"section": "general", "label": "General", "description": "Nombre, idioma, zona horaria"},
                {"section": "sales", "label": "Ventas", "description": "Pipeline, scoring, outreach"},
                {"section": "support", "label": "Soporte", "description": "SLA, categorias, asignacion"},
                {"section": "integrations", "label": "Integraciones", "description": "Email, Slack, CRM"},
                {"section": "team", "label": "Equipo", "description": "Usuarios, roles, permisos"},
            ],
        },
        visual_type="card",
        message="Que seccion quieres configurar?",
        next_suggestions=[
            "Configurar ventas",
            "Configurar soporte",
            "Configurar integraciones",
        ],
        visual_components=settings_cards,
    )


def _handle_start_campaign(intent: IntentMatch, context: dict) -> ActionResult:
    campaign_form = form(
        "Nueva Campana",
        fields=[
            {"name": "name", "label": "Nombre de la campana", "type": "text", "required": True},
            {"name": "type", "label": "Tipo", "type": "select",
             "options": ["email_sequence", "outbound", "nurturing"], "required": True},
            {"name": "target_segment", "label": "Segmento objetivo", "type": "text", "required": True},
            {"name": "start_date", "label": "Fecha de inicio", "type": "date", "required": False},
        ],
        submit_endpoint="/api/v1/campaigns",
        submit_label="Crear Campana",
    )

    return ActionResult(
        success=True,
        action_taken="start_campaign_form",
        result_data={},
        visual_type="form",
        message="Vamos a crear una nueva campana. Completa los datos:",
        next_suggestions=[
            "Ver campanas activas",
            "Ver leads para segmentar",
        ],
        visual_components=[campaign_form],
    )


def _handle_view_campaigns(intent: IntentMatch, context: dict) -> ActionResult:
    campaigns = [
        {"id": 1, "name": "Q1 Outbound LATAM", "status": "active", "sent": 120, "opened": 67, "replied": 23},
        {"id": 2, "name": "Nurturing Fintech", "status": "active", "sent": 85, "opened": 42, "replied": 11},
        {"id": 3, "name": "Reactivacion Q4", "status": "paused", "sent": 200, "opened": 90, "replied": 30},
    ]

    campaigns_table = table(
        "Campanas",
        headers=["ID", "Nombre", "Estado", "Enviados", "Abiertos", "Respondidos"],
        rows=[
            [c["id"], c["name"], c["status"], c["sent"], c["opened"], c["replied"]]
            for c in campaigns
        ],
        actions=["Ver detalle", "Pausar", "Reanudar"],
    )

    return ActionResult(
        success=True,
        action_taken="view_campaigns",
        result_data={"campaigns": campaigns},
        visual_type="table",
        message=f"Tienes {len(campaigns)} campanas. 2 activas, 1 pausada.",
        next_suggestions=[
            "Iniciar nueva campana",
            "Ver detalles de una campana",
            "Pausar una campana",
        ],
        visual_components=[campaigns_table],
    )


def _handle_schedule_meeting(intent: IntentMatch, context: dict) -> ActionResult:
    meeting_form = form(
        "Agendar Reunion",
        fields=[
            {"name": "title", "label": "Titulo de la reunion", "type": "text", "required": True},
            {"name": "date", "label": "Fecha", "type": "date", "required": True},
            {"name": "time", "label": "Hora", "type": "time", "required": True},
            {"name": "duration", "label": "Duracion (minutos)", "type": "number", "required": True},
            {"name": "attendees", "label": "Participantes (emails)", "type": "text", "required": True},
        ],
        submit_endpoint="/api/v1/meetings",
        submit_label="Agendar",
    )

    return ActionResult(
        success=True,
        action_taken="schedule_meeting_form",
        result_data={},
        visual_type="form",
        message="Vamos a agendar una reunion. Completa los datos:",
        next_suggestions=[
            "Ver mis reuniones",
            "Ver calendario",
        ],
        visual_components=[meeting_form],
    )


def _handle_search_kb(intent: IntentMatch, context: dict) -> ActionResult:
    query = intent.extracted_params.get("search_query", "")
    articles = [
        {"id": 1, "title": "Como restablecer contrasena", "relevance": 0.95},
        {"id": 2, "title": "Guia de inicio rapido", "relevance": 0.82},
        {"id": 3, "title": "Preguntas frecuentes sobre facturacion", "relevance": 0.76},
    ]

    kb_table = table(
        "Resultados de la Base de Conocimiento",
        headers=["ID", "Titulo", "Relevancia"],
        rows=[
            [a["id"], a["title"], f"{int(a['relevance'] * 100)}%"]
            for a in articles
        ],
        actions=["Ver articulo", "Copiar enlace"],
    )

    return ActionResult(
        success=True,
        action_taken="search_kb",
        result_data={"articles": articles, "query": query},
        visual_type="table",
        message=f"Encontre {len(articles)} articulos relevantes en la base de conocimiento.",
        next_suggestions=[
            "Ver un articulo",
            "Crear un nuevo articulo",
            "Crear un ticket",
        ],
        visual_components=[kb_table],
    )


def _handle_create_kb_article(intent: IntentMatch, context: dict) -> ActionResult:
    kb_form = form(
        "Nuevo Articulo KB",
        fields=[
            {"name": "title", "label": "Titulo del articulo", "type": "text", "required": True},
            {"name": "category", "label": "Categoria", "type": "select",
             "options": ["guia", "faq", "troubleshooting", "referencia"], "required": True},
            {"name": "content", "label": "Contenido", "type": "textarea", "required": True},
            {"name": "tags", "label": "Etiquetas", "type": "text", "required": False},
        ],
        submit_endpoint="/api/v1/kb/articles",
        submit_label="Publicar Articulo",
    )

    return ActionResult(
        success=True,
        action_taken="create_kb_article_form",
        result_data={},
        visual_type="form",
        message="Vamos a crear un articulo para la base de conocimiento:",
        next_suggestions=[
            "Ver articulos existentes",
            "Buscar en KB",
        ],
        visual_components=[kb_form],
    )


def _handle_view_customer(intent: IntentMatch, context: dict) -> ActionResult:
    ids = intent.extracted_params.get("ids", [])
    customer_id = ids[0] if ids else context.get("current_customer_id", 1)
    customer = {
        "id": customer_id,
        "name": "TechCorp S.A.",
        "contact": "Ana Garcia",
        "email": "ana@techcorp.com",
        "health_score": 85,
        "lifetime_value": 24500,
        "open_tickets": 2,
        "last_interaction": "2026-03-18",
        "tags": ["enterprise", "fintech", "LATAM"],
    }

    customer_score = score_card(
        customer["name"],
        score=customer["health_score"],
        max_score=100,
        classification="A",
        color="#22c55e",
        details=[
            {"label": "Contacto", "value": customer["contact"]},
            {"label": "Email", "value": customer["email"]},
            {"label": "Valor de vida", "value": f"${customer['lifetime_value']:,}"},
            {"label": "Tickets abiertos", "value": str(customer["open_tickets"])},
            {"label": "Ultima interaccion", "value": customer["last_interaction"]},
            {"label": "Tags", "value": ", ".join(customer["tags"])},
        ],
    )

    return ActionResult(
        success=True,
        action_taken="view_customer",
        result_data={"customer": customer},
        visual_type="card",
        message=f"Perfil 360 de {customer['name']}: salud 85/100, 2 tickets abiertos.",
        next_suggestions=[
            "Ver historial de interacciones",
            "Componer outreach",
            "Ver tickets del cliente",
        ],
        visual_components=[customer_score],
    )


def _handle_view_predictions(intent: IntentMatch, context: dict) -> ActionResult:
    predictions = {
        "revenue_forecast": {
            "current_month": 45000,
            "next_month": 52000,
            "trend": "up",
            "confidence": 0.78,
        },
        "lead_conversion_forecast": {
            "expected_conversions": 6,
            "pipeline_value": 180000,
        },
        "churn_risk": {
            "at_risk_customers": 3,
            "top_risk": "CloudNet (72% probabilidad de churn)",
        },
    }

    # KPI cards for key predictions
    kpis = [
        kpi_card("Ingresos Este Mes", "$45,000", icon="money", color="#3b82f6"),
        kpi_card("Pronostico Prox. Mes", "$52,000", icon="trend_up", trend="+15%", color="#22c55e"),
        kpi_card("Conversiones Esperadas", 6, icon="funnel", color="#8b5cf6"),
        kpi_card("Valor del Pipeline", "$180,000", icon="pipeline", color="#6366f1"),
        kpi_card("Clientes en Riesgo", 3, icon="warning", color="#ef4444"),
    ]

    # Bar chart for pipeline forecast by month
    pipeline_chart = bar_chart(
        "Pronostico de Ingresos",
        labels=["Ene", "Feb", "Mar", "Abr (est)", "May (est)", "Jun (est)"],
        values=[38000, 41000, 45000, 49000, 52000, 55000],
        colors=["#3b82f6", "#3b82f6", "#3b82f6", "#93c5fd", "#93c5fd", "#93c5fd"],
    )

    components = kpis + [pipeline_chart]

    return ActionResult(
        success=True,
        action_taken="view_predictions",
        result_data={"predictions": predictions},
        visual_type="chart",
        message=(
            "Pronostico: ingresos estimados $52,000 proximo mes (+15%). "
            "6 conversiones esperadas. 3 clientes en riesgo de churn."
        ),
        next_suggestions=[
            "Ver clientes en riesgo",
            "Ver pipeline",
            "Ver analiticas detalladas",
        ],
        visual_components=components,
    )


def _handle_run_automation(intent: IntentMatch, context: dict) -> ActionResult:
    automations = [
        {"id": 1, "name": "Seguimiento automatico a leads nuevos", "status": "active", "executions_today": 12},
        {"id": 2, "name": "Escalar tickets sin respuesta > 24h", "status": "active", "executions_today": 3},
        {"id": 3, "name": "Notificar equipo sobre leads hot", "status": "active", "executions_today": 5},
    ]

    automations_table = table(
        "Automatizaciones Activas",
        headers=["ID", "Nombre", "Estado", "Ejecuciones Hoy"],
        rows=[
            [a["id"], a["name"], a["status"], a["executions_today"]]
            for a in automations
        ],
        actions=["Ver detalle", "Pausar", "Editar"],
    )

    return ActionResult(
        success=True,
        action_taken="view_automations",
        result_data={"automations": automations},
        visual_type="table",
        message=f"Tienes {len(automations)} automatizaciones activas con 20 ejecuciones hoy.",
        next_suggestions=[
            "Crear nueva automatizacion",
            "Ver detalle de automatizacion",
            "Pausar una automatizacion",
        ],
        visual_components=[automations_table],
    )


def _handle_search(intent: IntentMatch, context: dict) -> ActionResult:
    query = intent.extracted_params.get("search_query", intent.original_text)
    results = [
        {"type": "lead", "id": 1, "title": "TechCorp", "subtitle": "Lead — Score 87"},
        {"type": "ticket", "id": 100, "title": "Error en login", "subtitle": "Ticket — Alta prioridad"},
        {"type": "customer", "id": 10, "title": "TechCorp S.A.", "subtitle": "Cliente — Enterprise"},
    ]

    results_table = table(
        "Resultados de Busqueda",
        headers=["Tipo", "ID", "Titulo", "Detalle"],
        rows=[
            [r["type"].capitalize(), r["id"], r["title"], r["subtitle"]]
            for r in results
        ],
        actions=["Ver detalle"],
    )

    return ActionResult(
        success=True,
        action_taken="search",
        result_data={"results": results, "query": query, "total": len(results)},
        visual_type="table",
        message=f"Encontre {len(results)} resultados para tu busqueda.",
        next_suggestions=[
            "Ver un resultado",
            "Refinar busqueda",
            "Buscar en KB",
        ],
        visual_components=[results_table],
    )


def _handle_unknown(intent: IntentMatch, context: dict) -> ActionResult:
    suggestion_cards = [
        action_card(
            "Ver Dashboard",
            "Revisa las metricas y KPIs de tu negocio",
            "Abrir", "/api/v1/dashboard", icon="chart",
        ),
        action_card(
            "Crear un Lead",
            "Registra un nuevo prospecto en el pipeline",
            "Crear", "/api/v1/leads", icon="add_person",
        ),
        action_card(
            "Crear un Ticket",
            "Abre un caso de soporte nuevo",
            "Crear", "/api/v1/tickets", icon="ticket",
        ),
        action_card(
            "Ayuda",
            "Mira todas las acciones disponibles",
            "Ver", "/api/v1/help", icon="help",
        ),
    ]

    return ActionResult(
        success=False,
        action_taken="unknown",
        result_data={},
        visual_type="text",
        message=(
            "No estoy seguro de lo que necesitas. "
            "Aqui tienes algunas acciones comunes que puedes probar, "
            "o escribe \"ayuda\" para ver todo lo que puedo hacer."
        ),
        next_suggestions=[
            "Ayuda",
            "Ver el dashboard",
            "Crear un lead",
        ],
        visual_components=suggestion_cards,
    )


# ---------------------------------------------------------------------------
# Handler dispatch table
# ---------------------------------------------------------------------------

_HANDLERS: dict = {
    Intent.GREETING: _handle_greeting,
    Intent.HELP: _handle_help,
    Intent.CREATE_LEAD: _handle_create_lead,
    Intent.LIST_LEADS: _handle_list_leads,
    Intent.QUALIFY_LEAD: _handle_qualify_lead,
    Intent.VIEW_KANBAN: _handle_view_kanban,
    Intent.VIEW_PIPELINE: _handle_view_pipeline,
    Intent.VIEW_DASHBOARD: _handle_view_dashboard,
    Intent.CREATE_TICKET: _handle_create_ticket,
    Intent.LIST_TICKETS: _handle_list_tickets,
    Intent.VIEW_TICKET: _handle_view_ticket,
    Intent.COMPOSE_OUTREACH: _handle_compose_outreach,
    Intent.IMPORT_DATA: _handle_import_data,
    Intent.EXPORT_DATA: _handle_export_data,
    Intent.VIEW_ANALYTICS: _handle_view_analytics,
    Intent.VIEW_HEALTH_SCORE: _handle_view_health_score,
    Intent.CONFIGURE_SETTINGS: _handle_configure_settings,
    Intent.START_CAMPAIGN: _handle_start_campaign,
    Intent.VIEW_CAMPAIGNS: _handle_view_campaigns,
    Intent.SCHEDULE_MEETING: _handle_schedule_meeting,
    Intent.SEARCH_KB: _handle_search_kb,
    Intent.CREATE_KB_ARTICLE: _handle_create_kb_article,
    Intent.VIEW_CUSTOMER: _handle_view_customer,
    Intent.VIEW_PREDICTIONS: _handle_view_predictions,
    Intent.RUN_AUTOMATION: _handle_run_automation,
    Intent.SEARCH: _handle_search,
    Intent.UNKNOWN: _handle_unknown,
}
