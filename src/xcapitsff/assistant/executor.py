"""Action executor — maps recognised intents to API actions and formats results.

Every action returns an :class:`ActionResult` that contains the data needed
to render a visual component on the frontend (card, table, chart, kanban,
form, or plain text) together with a user-facing message in Spanish and
contextual suggestions for the next step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .intent import Intent, IntentMatch


@dataclass
class ActionResult:
    """Result produced by executing an action for a recognised intent."""

    success: bool
    action_taken: str
    result_data: dict = field(default_factory=dict)
    visual_type: str = "text"  # card | table | chart | text | form | kanban
    message: str = ""
    next_suggestions: list[str] = field(default_factory=list)


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
    return ActionResult(
        success=True,
        action_taken="greeting",
        result_data={
            "welcome": True,
            "features": [
                "Gestionar leads y pipeline de ventas",
                "Crear y resolver tickets de soporte",
                "Ver dashboard y metricas en tiempo real",
                "Componer outreach personalizado",
                "Calificar leads con scoring IA",
                "Ver predicciones y pronosticos",
            ],
        },
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
    )


def _handle_help(intent: IntentMatch, context: dict) -> ActionResult:
    categories = {
        "Ventas": [
            "Crear un lead",
            "Ver el pipeline / kanban",
            "Calificar leads (scoring)",
            "Componer outreach",
            "Iniciar una campana",
            "Ver predicciones",
        ],
        "Soporte": [
            "Crear un ticket",
            "Ver tickets abiertos",
            "Buscar en la base de conocimiento",
            "Crear un articulo KB",
        ],
        "General": [
            "Ver el dashboard",
            "Importar / exportar datos",
            "Agendar una reunion",
            "Configurar automatizaciones",
            "Ver analiticas",
        ],
    }
    return ActionResult(
        success=True,
        action_taken="help",
        result_data={"categories": categories},
        visual_type="card",
        message="Estas son las cosas que puedo hacer por ti, organizadas por categoria:",
        next_suggestions=[
            "Crear un lead",
            "Ver el dashboard",
            "Crear un ticket",
        ],
    )


def _handle_create_lead(intent: IntentMatch, context: dict) -> ActionResult:
    params = intent.extracted_params
    # If we have enough data we could call the real API; otherwise ask for it.
    if params.get("company") or params.get("email"):
        lead_data = {
            "id": 1001,
            "company_name": params.get("company", "Sin nombre"),
            "contact_email": params.get("email", ""),
            "stage": "new",
            "score_icp": 0,
        }
        return ActionResult(
            success=True,
            action_taken="create_lead",
            result_data={"lead": lead_data},
            visual_type="card",
            message=f"Lead creado exitosamente para {lead_data['company_name']}.",
            next_suggestions=[
                "Calificar este lead",
                "Ver el pipeline",
                "Componer outreach",
            ],
        )

    # Not enough data — show form
    return ActionResult(
        success=True,
        action_taken="create_lead_form",
        result_data={
            "form_fields": [
                {"name": "company_name", "label": "Nombre de la empresa", "type": "text", "required": True},
                {"name": "contact_name", "label": "Nombre del contacto", "type": "text", "required": True},
                {"name": "contact_email", "label": "Email de contacto", "type": "email", "required": True},
                {"name": "phone", "label": "Telefono", "type": "text", "required": False},
                {"name": "region", "label": "Region", "type": "select", "options": ["LATAM", "NA", "EU", "APAC"], "required": False},
            ],
        },
        visual_type="form",
        message="Para crear un nuevo lead, necesito los siguientes datos:",
        next_suggestions=[
            "Importar leads desde CSV",
            "Ver el pipeline",
        ],
    )


def _handle_list_leads(intent: IntentMatch, context: dict) -> ActionResult:
    sample_leads = [
        {"id": 1, "company": "TechCorp", "contact": "Ana Garcia", "score": 87, "stage": "qualified"},
        {"id": 2, "company": "FinanceHub", "contact": "Carlos Lopez", "score": 72, "stage": "contacted"},
        {"id": 3, "company": "DataPro", "contact": "Maria Rodriguez", "score": 93, "stage": "proposal"},
        {"id": 4, "company": "CloudNet", "contact": "Juan Martinez", "score": 61, "stage": "new"},
        {"id": 5, "company": "SalesForce Latam", "contact": "Laura Perez", "score": 45, "stage": "new"},
    ]
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
        )

    score_card = {
        "lead_id": lead_id,
        "score_icp": 85,
        "grade": "A",
        "factors": {
            "Tamano de empresa": 9,
            "Industria target": 8,
            "Nivel de contacto": 9,
            "Engagement": 7,
            "Presupuesto estimado": 8,
        },
        "recommendation": "Lead altamente calificado. Se recomienda agendar reunion.",
    }
    return ActionResult(
        success=True,
        action_taken="qualify_lead",
        result_data={"score_card": score_card},
        visual_type="card",
        message=f"El lead #{lead_id} obtuvo un score de 85/100 (Grado A).",
        next_suggestions=[
            "Componer outreach para este lead",
            "Agendar una reunion",
            "Ver el pipeline",
        ],
    )


def _handle_view_kanban(intent: IntentMatch, context: dict) -> ActionResult:
    columns = [
        {"stage": "new", "label": "Nuevos", "count": 12, "color": "#3b82f6"},
        {"stage": "contacted", "label": "Contactados", "count": 8, "color": "#f59e0b"},
        {"stage": "qualified", "label": "Calificados", "count": 5, "color": "#10b981"},
        {"stage": "proposal", "label": "Propuesta", "count": 3, "color": "#8b5cf6"},
        {"stage": "negotiation", "label": "Negociacion", "count": 2, "color": "#ef4444"},
        {"stage": "won", "label": "Ganados", "count": 7, "color": "#22c55e"},
    ]
    return ActionResult(
        success=True,
        action_taken="view_kanban",
        result_data={"columns": columns, "total_leads": 37},
        visual_type="kanban",
        message="Aqui tienes tu tablero Kanban con 37 leads distribuidos en 6 etapas.",
        next_suggestions=[
            "Crear un nuevo lead",
            "Ver leads calificados",
            "Ver dashboard completo",
        ],
    )


def _handle_view_pipeline(intent: IntentMatch, context: dict) -> ActionResult:
    funnel = [
        {"stage": "new", "count": 12, "pct": 100},
        {"stage": "contacted", "count": 8, "pct": 67},
        {"stage": "qualified", "count": 5, "pct": 42},
        {"stage": "proposal", "count": 3, "pct": 25},
        {"stage": "won", "count": 2, "pct": 17},
    ]
    return ActionResult(
        success=True,
        action_taken="view_pipeline",
        result_data={"funnel": funnel, "conversion_rate": 17},
        visual_type="chart",
        message="Tu embudo de ventas muestra una tasa de conversion del 17%.",
        next_suggestions=[
            "Ver el kanban",
            "Ver leads hot",
            "Ver predicciones",
        ],
    )


def _handle_view_dashboard(intent: IntentMatch, context: dict) -> ActionResult:
    dashboard_data = {
        "sales": {"total_leads": 37, "avg_score": 72, "conversion_rate": 17},
        "support": {"open_tickets": 14, "avg_resolution_hours": 4.2, "satisfaction": 4.5},
        "activity": {"events_today": 128, "active_campaigns": 3},
    }
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
    )


def _handle_create_ticket(intent: IntentMatch, context: dict) -> ActionResult:
    params = intent.extracted_params
    if params.get("search_query"):
        ticket = {
            "id": 501,
            "subject": params["search_query"],
            "status": "open",
            "priority": "medium",
        }
        return ActionResult(
            success=True,
            action_taken="create_ticket",
            result_data={"ticket": ticket},
            visual_type="card",
            message=f"Ticket #{ticket['id']} creado: \"{ticket['subject']}\".",
            next_suggestions=[
                "Ver el ticket",
                "Buscar en KB",
                "Responder al ticket",
            ],
        )

    return ActionResult(
        success=True,
        action_taken="create_ticket_form",
        result_data={
            "form_fields": [
                {"name": "subject", "label": "Asunto", "type": "text", "required": True},
                {"name": "description", "label": "Descripcion", "type": "textarea", "required": True},
                {"name": "priority", "label": "Prioridad", "type": "select", "options": ["low", "medium", "high", "critical"], "required": True},
                {"name": "category", "label": "Categoria", "type": "select", "options": ["bug", "feature", "question", "billing"], "required": False},
            ],
        },
        visual_type="form",
        message="Para crear un ticket, necesito los siguientes datos:",
        next_suggestions=[
            "Ver tickets abiertos",
            "Buscar en KB",
        ],
    )


def _handle_list_tickets(intent: IntentMatch, context: dict) -> ActionResult:
    sample_tickets = [
        {"id": 100, "subject": "Error en login", "status": "open", "priority": "high"},
        {"id": 101, "subject": "Consulta sobre facturacion", "status": "open", "priority": "medium"},
        {"id": 102, "subject": "Solicitud de nueva feature", "status": "in_progress", "priority": "low"},
        {"id": 103, "subject": "Integracion con Slack falla", "status": "open", "priority": "high"},
    ]
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
    )


def _handle_compose_outreach(intent: IntentMatch, context: dict) -> ActionResult:
    lead_id = None
    ids = intent.extracted_params.get("ids", [])
    if ids:
        lead_id = ids[0]
    elif context.get("current_lead_id"):
        lead_id = context["current_lead_id"]

    draft = {
        "lead_id": lead_id,
        "subject": "Oportunidad de colaboracion — XcapitSFF",
        "body": (
            "Hola [Nombre],\n\n"
            "Espero que estes muy bien. Me comunico porque creo que "
            "nuestra solucion puede aportar valor a [Empresa].\n\n"
            "Me encantaria agendar una breve reunion para mostrarte "
            "como podemos ayudarte.\n\n"
            "Saludos cordiales."
        ),
        "tone": "profesional",
        "channel": "email",
    }
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
    )


def _handle_import_data(intent: IntentMatch, context: dict) -> ActionResult:
    return ActionResult(
        success=True,
        action_taken="import_data_form",
        result_data={
            "supported_formats": ["CSV", "Excel (.xlsx)", "JSON"],
            "form_fields": [
                {"name": "file", "label": "Archivo", "type": "file", "required": True},
                {"name": "entity_type", "label": "Tipo de entidad", "type": "select", "options": ["leads", "contacts", "tickets", "customers"], "required": True},
                {"name": "duplicate_handling", "label": "Manejo de duplicados", "type": "select", "options": ["skip", "update", "create_new"], "required": False},
            ],
        },
        visual_type="form",
        message="Para importar datos, selecciona el archivo y el tipo de entidad:",
        next_suggestions=[
            "Ver formato de CSV esperado",
            "Ver leads importados",
        ],
    )


def _handle_export_data(intent: IntentMatch, context: dict) -> ActionResult:
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
        ],
    }
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
    )


def _handle_configure_settings(intent: IntentMatch, context: dict) -> ActionResult:
    settings_sections = [
        {"section": "general", "label": "General", "description": "Nombre, idioma, zona horaria"},
        {"section": "sales", "label": "Ventas", "description": "Pipeline, scoring, outreach"},
        {"section": "support", "label": "Soporte", "description": "SLA, categorias, asignacion"},
        {"section": "integrations", "label": "Integraciones", "description": "Email, Slack, CRM"},
        {"section": "team", "label": "Equipo", "description": "Usuarios, roles, permisos"},
    ]
    return ActionResult(
        success=True,
        action_taken="configure_settings",
        result_data={"sections": settings_sections},
        visual_type="card",
        message="Que seccion quieres configurar?",
        next_suggestions=[
            "Configurar ventas",
            "Configurar soporte",
            "Configurar integraciones",
        ],
    )


def _handle_start_campaign(intent: IntentMatch, context: dict) -> ActionResult:
    return ActionResult(
        success=True,
        action_taken="start_campaign_form",
        result_data={
            "form_fields": [
                {"name": "name", "label": "Nombre de la campana", "type": "text", "required": True},
                {"name": "type", "label": "Tipo", "type": "select", "options": ["email_sequence", "outbound", "nurturing"], "required": True},
                {"name": "target_segment", "label": "Segmento objetivo", "type": "text", "required": True},
                {"name": "start_date", "label": "Fecha de inicio", "type": "date", "required": False},
            ],
        },
        visual_type="form",
        message="Vamos a crear una nueva campana. Completa los datos:",
        next_suggestions=[
            "Ver campanas activas",
            "Ver leads para segmentar",
        ],
    )


def _handle_view_campaigns(intent: IntentMatch, context: dict) -> ActionResult:
    campaigns = [
        {"id": 1, "name": "Q1 Outbound LATAM", "status": "active", "sent": 120, "opened": 67, "replied": 23},
        {"id": 2, "name": "Nurturing Fintech", "status": "active", "sent": 85, "opened": 42, "replied": 11},
        {"id": 3, "name": "Reactivacion Q4", "status": "paused", "sent": 200, "opened": 90, "replied": 30},
    ]
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
    )


def _handle_schedule_meeting(intent: IntentMatch, context: dict) -> ActionResult:
    return ActionResult(
        success=True,
        action_taken="schedule_meeting_form",
        result_data={
            "form_fields": [
                {"name": "title", "label": "Titulo de la reunion", "type": "text", "required": True},
                {"name": "date", "label": "Fecha", "type": "date", "required": True},
                {"name": "time", "label": "Hora", "type": "time", "required": True},
                {"name": "duration", "label": "Duracion (minutos)", "type": "number", "required": True},
                {"name": "attendees", "label": "Participantes (emails)", "type": "text", "required": True},
            ],
        },
        visual_type="form",
        message="Vamos a agendar una reunion. Completa los datos:",
        next_suggestions=[
            "Ver mis reuniones",
            "Ver calendario",
        ],
    )


def _handle_search_kb(intent: IntentMatch, context: dict) -> ActionResult:
    query = intent.extracted_params.get("search_query", "")
    articles = [
        {"id": 1, "title": "Como restablecer contrasena", "relevance": 0.95},
        {"id": 2, "title": "Guia de inicio rapido", "relevance": 0.82},
        {"id": 3, "title": "Preguntas frecuentes sobre facturacion", "relevance": 0.76},
    ]
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
    )


def _handle_create_kb_article(intent: IntentMatch, context: dict) -> ActionResult:
    return ActionResult(
        success=True,
        action_taken="create_kb_article_form",
        result_data={
            "form_fields": [
                {"name": "title", "label": "Titulo del articulo", "type": "text", "required": True},
                {"name": "category", "label": "Categoria", "type": "select", "options": ["guia", "faq", "troubleshooting", "referencia"], "required": True},
                {"name": "content", "label": "Contenido", "type": "textarea", "required": True},
                {"name": "tags", "label": "Etiquetas", "type": "text", "required": False},
            ],
        },
        visual_type="form",
        message="Vamos a crear un articulo para la base de conocimiento:",
        next_suggestions=[
            "Ver articulos existentes",
            "Buscar en KB",
        ],
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
    )


def _handle_run_automation(intent: IntentMatch, context: dict) -> ActionResult:
    automations = [
        {"id": 1, "name": "Seguimiento automatico a leads nuevos", "status": "active", "executions_today": 12},
        {"id": 2, "name": "Escalar tickets sin respuesta > 24h", "status": "active", "executions_today": 3},
        {"id": 3, "name": "Notificar equipo sobre leads hot", "status": "active", "executions_today": 5},
    ]
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
    )


def _handle_search(intent: IntentMatch, context: dict) -> ActionResult:
    query = intent.extracted_params.get("search_query", intent.original_text)
    results = [
        {"type": "lead", "id": 1, "title": "TechCorp", "subtitle": "Lead — Score 87"},
        {"type": "ticket", "id": 100, "title": "Error en login", "subtitle": "Ticket — Alta prioridad"},
        {"type": "customer", "id": 10, "title": "TechCorp S.A.", "subtitle": "Cliente — Enterprise"},
    ]
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
    )


def _handle_unknown(intent: IntentMatch, context: dict) -> ActionResult:
    return ActionResult(
        success=False,
        action_taken="unknown",
        result_data={},
        visual_type="text",
        message=(
            "No estoy seguro de lo que necesitas. "
            "Puedes intentar de otra forma o escribir \"ayuda\" para ver lo que puedo hacer."
        ),
        next_suggestions=[
            "Ayuda",
            "Ver el dashboard",
            "Crear un lead",
        ],
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
