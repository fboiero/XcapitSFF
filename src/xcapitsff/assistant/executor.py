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

import asyncio
import logging
from xcapitsff.core.database import async_session
from xcapitsff.sales.pipeline import (
    get_leads,
    get_lead,
    create_lead,
    get_pipeline_stats,
    get_hot_leads,
)
from xcapitsff.core.schemas import LeadCreate, LeadFilter, LeadResponse
from xcapitsff.core.deals import deal_manager
from xcapitsff.discovery.project import project_manager
from xcapitsff.sales.scoring import calculate_icp_score
from xcapitsff.core.models import Ticket

logger = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# Async Data Provider Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=5)
        return loop.run_until_complete(coro)
    except Exception as e:
        logger.debug(f"Async operation failed: {e}")
        return None


async def _get_leads_from_db(limit: int = 50) -> list[dict]:
    """Fetch leads from database."""
    try:
        async with async_session() as db:
            leads = await get_leads(db, LeadFilter(), limit, 0)
            return [
                {
                    "id": l.id,
                    "company": l.company_name or "Sin nombre",
                    "contact": l.contact_name or "Sin contacto",
                    "score": l.score_icp or 0,
                    "stage": l.stage.value if hasattr(l.stage, 'value') else str(l.stage),
                    "region": l.region.value if hasattr(l.region, 'value') else str(l.region),
                    "email": l.contact_email or "",
                }
                for l in leads
            ]
    except Exception as e:
        logger.debug(f"Failed to fetch leads: {e}")
        return []


async def _get_pipeline_stats_from_db() -> dict:
    """Fetch pipeline stats from database."""
    try:
        async with async_session() as db:
            stats = await get_pipeline_stats(db)
            return {
                "total": stats.total,
                "by_stage": {s.stage: s.count for s in stats.by_stage} if hasattr(stats, 'by_stage') else {},
                "avg_score": stats.avg_score if hasattr(stats, 'avg_score') else 0,
            }
    except Exception as e:
        logger.debug(f"Failed to fetch pipeline stats: {e}")
        return {"total": 0, "by_stage": {}, "avg_score": 0}


async def _get_hot_leads_from_db(limit: int = 10) -> list[dict]:
    """Fetch hot (high-ICP-score) leads from database."""
    try:
        async with async_session() as db:
            hot_leads = await get_hot_leads(db, limit)
            return [
                {
                    "id": l.id,
                    "company": l.company_name or "Sin nombre",
                    "contact": l.contact_name or "Sin contacto",
                    "score": l.score_icp or 0,
                    "stage": l.stage.value if hasattr(l.stage, 'value') else str(l.stage),
                    "region": l.region.value if hasattr(l.region, 'value') else str(l.region),
                }
                for l in hot_leads
            ]
    except Exception as e:
        logger.debug(f"Failed to fetch hot leads: {e}")
        return []


async def _get_tickets_from_db(limit: int = 20) -> list[dict]:
    """Fetch tickets from database."""
    try:
        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(Ticket).limit(limit))
            tickets = result.scalars().all()
            return [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "status": t.status,
                    "priority": t.priority,
                    "category": t.category,
                    "assigned": t.assigned_agent or "Sin asignar",
                }
                for t in tickets
            ]
    except Exception as e:
        logger.debug(f"Failed to fetch tickets: {e}")
        return []


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

    # Fetch real data
    real_leads = _run_async(_get_leads_from_db(limit=500)) or []
    real_tickets = _run_async(_get_tickets_from_db(limit=500)) or []

    # Calculate real KPIs
    total_leads = len(real_leads) if real_leads else 37
    open_tickets = len([t for t in real_tickets if t.get("status") == "open"]) if real_tickets else 14
    conversion_rate = "17%"  # Would need to calculate from DB
    satisfaction = "4.5/5"   # Would need to calculate from DB
    trend = f"+{len([l for l in real_leads if l.get('stage') == 'qualified'])} calificados"

    # KPI summary with real data
    kpis = [
        kpi_card("Leads Activos", total_leads, icon="people", trend=trend, color="#3b82f6"),
        kpi_card("Tickets Abiertos", open_tickets, icon="ticket", color="#f59e0b"),
        kpi_card("Tasa de Conversion", conversion_rate, icon="trend_up", color="#22c55e"),
        kpi_card("Satisfaccion", satisfaction, icon="star", color="#8b5cf6"),
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

    # If we have enough data, create the lead in DB and return a score_card
    if params.get("company") or params.get("email"):
        # Try to create in database
        lead_created = False
        created_lead = None

        try:
            async def _create_lead_async():
                async with async_session() as db:
                    from xcapitsff.core.schemas import LeadCreate
                    lead_create = LeadCreate(
                        company_name=params.get("company", "Sin nombre"),
                        contact_name=params.get("contact", params.get("search_query", "Contacto")),
                        contact_email=params.get("email", ""),
                        region=params.get("region", "LATAM"),
                        c_level=params.get("c_level", False),
                    )
                    lead = await create_lead(db, lead_create)
                    return {
                        "id": lead.id,
                        "company_name": lead.company_name,
                        "contact_name": lead.contact_name,
                        "contact_email": lead.contact_email,
                        "region": lead.region.value if hasattr(lead.region, 'value') else str(lead.region),
                        "c_level": lead.c_level,
                        "stage": lead.stage.value if hasattr(lead.stage, 'value') else str(lead.stage),
                        "score_icp": lead.score_icp or 62,
                    }

            created_lead = _run_async(_create_lead_async())
            if created_lead:
                lead_created = True
                lead_data = created_lead
            else:
                lead_data = {
                    "id": 1001,
                    "company_name": params.get("company", "Sin nombre"),
                    "contact_name": params.get("contact", params.get("search_query", "Contacto")),
                    "contact_email": params.get("email", ""),
                    "region": "LATAM",
                    "c_level": False,
                    "afinidad": "media",
                    "stage": "new",
                    "score_icp": 62,
                }
        except Exception as e:
            logger.debug(f"Failed to create lead in DB: {e}")
            lead_data = {
                "id": 1001,
                "company_name": params.get("company", "Sin nombre"),
                "contact_name": params.get("contact", params.get("search_query", "Contacto")),
                "contact_email": params.get("email", ""),
                "region": "LATAM",
                "c_level": False,
                "afinidad": "media",
                "stage": "new",
                "score_icp": 62,
            }

        # Use build_lead_card for a rich score_card with ICP classification
        lead_card = build_lead_card(lead_data)

        success_msg = "Lead creado exitosamente" if lead_created else "Lead configurado"

        return ActionResult(
            success=True,
            action_taken="create_lead",
            result_data={"lead": lead_data, "created": lead_created},
            visual_type="card",
            message=(
                f"{success_msg} para {lead_data['company_name']}. "
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
    # Try real data first
    real_leads = _run_async(_get_leads_from_db(limit=20))

    if real_leads:
        leads_data = real_leads
    else:
        # Fallback to sample data
        leads_data = [
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
            for ld in leads_data
        ],
        actions=["Ver detalle", "Calificar", "Outreach"],
    )

    return ActionResult(
        success=True,
        action_taken="list_leads",
        result_data={"leads": leads_data, "total": len(leads_data)},
        visual_type="table",
        message=f"Encontre {len(leads_data)} leads en tu pipeline.",
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

    # Try to fetch and score the lead from DB
    real_lead = None
    try:
        async def _get_and_score_lead():
            async with async_session() as db:
                lead = await get_lead(db, lead_id)
                if lead:
                    score = await calculate_icp_score(db, lead)
                    return {
                        "id": lead.id,
                        "company_name": lead.company_name,
                        "contact_name": lead.contact_name,
                        "score_icp": score or lead.score_icp or 0,
                        "region": lead.region.value if hasattr(lead.region, 'value') else str(lead.region),
                        "c_level": lead.c_level,
                    }
                return None

        real_lead = _run_async(_get_and_score_lead())
    except Exception as e:
        logger.debug(f"Failed to fetch and score lead: {e}")

    if real_lead:
        total_score = int(real_lead.get("score_icp", 85))
    else:
        total_score = 85

    # Classify grade based on score
    if total_score >= 80:
        grade = "A"
        color = "#22c55e"
        recommendation = "Lead altamente calificado. Se recomienda agendar reunion."
    elif total_score >= 60:
        grade = "B"
        color = "#f59e0b"
        recommendation = "Lead calificado. Se recomienda contacto personalizado."
    else:
        grade = "C"
        color = "#ef4444"
        recommendation = "Lead con potencial. Se recomienda nurturing."

    factors = {
        "Tamano de empresa": min(10, max(1, total_score // 20 + 5)),
        "Industria target": min(10, max(1, total_score // 25 + 4)),
        "Nivel de contacto": min(10, max(1, total_score // 15 + 6)),
        "Engagement": min(10, max(1, total_score // 30 + 3)),
        "Presupuesto estimado": min(10, max(1, total_score // 20 + 5)),
    }

    # Score card with overall grade
    main_card = score_card(
        f"Lead #{lead_id} — ICP Score",
        score=total_score,
        max_score=100,
        classification=grade,
        color=color,
        details=[
            {"label": k, "value": f"{int(v)}/10"} for k, v in factors.items()
        ],
    )

    return ActionResult(
        success=True,
        action_taken="qualify_lead",
        result_data={
            "score_card": {
                "lead_id": lead_id,
                "score_icp": total_score,
                "grade": grade,
                "factors": {k: int(v) for k, v in factors.items()},
                "recommendation": recommendation,
            },
        },
        visual_type="card",
        message=(
            f"El lead #{lead_id} obtuvo un score de {total_score}/100 (Grado {grade}). "
            f"{recommendation}"
        ),
        next_suggestions=[
            "Componer outreach para este lead",
            "Agendar una reunion",
            "Ver el pipeline",
        ],
        visual_components=[main_card],
    )


def _handle_view_kanban(intent: IntentMatch, context: dict) -> ActionResult:
    # Fetch real leads
    real_leads = _run_async(_get_leads_from_db(limit=500)) or []

    # Group leads by stage
    stage_groups = {}
    for ld in real_leads:
        stage = ld.get("stage", "new")
        if stage not in stage_groups:
            stage_groups[stage] = []
        stage_groups[stage].append(ld)

    # Define stages with counts from real data
    stage_labels = {
        "new": "Nuevos",
        "qualified": "Calificados",
        "contacted": "Contactados",
        "meeting": "Reunion",
        "proposal": "Propuesta",
        "negotiation": "Negociacion",
        "won": "Ganados",
        "lost": "Perdidos",
    }

    stage_colors = {
        "new": "#3b82f6",
        "contacted": "#f59e0b",
        "qualified": "#10b981",
        "meeting": "#06b6d4",
        "proposal": "#8b5cf6",
        "negotiation": "#ef4444",
        "won": "#22c55e",
        "lost": "#6b7280",
    }

    columns_data = [
        {
            "id": stage,
            "label": stage_labels.get(stage, stage),
            "count": len(stage_groups.get(stage, [])),
            "color": stage_colors.get(stage, "#9ca3af"),
        }
        for stage in stage_labels.keys()
    ]

    # Build kanban cards from real leads (limit to first 20)
    sample_cards = []
    card_id = 0
    for ld in real_leads[:20]:
        sample_cards.append({
            "id": str(ld["id"]),
            "column": ld.get("stage", "new"),
            "title": ld.get("company", "Sin nombre"),
            "subtitle": f"{ld.get('contact', 'Sin contacto')} — Score {ld.get('score', 0)}",
        })
        card_id += 1

    # Fallback if no real data
    if not sample_cards:
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

    total_leads = len(real_leads) if real_leads else 37

    return ActionResult(
        success=True,
        action_taken="view_kanban",
        result_data={"columns": columns_data, "total_leads": total_leads},
        visual_type="kanban",
        message=f"Aqui tienes tu tablero Kanban con {total_leads} leads distribuidos en 6 etapas.",
        next_suggestions=[
            "Crear un nuevo lead",
            "Ver leads calificados",
            "Ver dashboard completo",
        ],
        visual_components=[kanban_board],
    )


def _handle_view_pipeline(intent: IntentMatch, context: dict) -> ActionResult:
    # Fetch real leads
    real_leads = _run_async(_get_leads_from_db(limit=500)) or []

    # Count leads by stage
    stage_counts = {}
    stage_labels_map = {
        "new": "Nuevos",
        "qualified": "Calificados",
        "contacted": "Contactados",
        "meeting": "Reunion",
        "proposal": "Propuesta",
        "negotiation": "Negociacion",
        "won": "Ganados",
        "lost": "Perdidos",
    }

    stage_colors = {
        "nuevos": "#3b82f6",
        "contactados": "#f59e0b",
        "calificados": "#10b981",
        "reunion": "#06b6d4",
        "propuesta": "#8b5cf6",
        "ganados": "#22c55e",
    }

    for ld in real_leads:
        stage = ld.get("stage", "new")
        label = stage_labels_map.get(stage, stage)
        stage_counts[label] = stage_counts.get(label, 0) + 1

    # Build funnel with real data or fallback
    if stage_counts:
        stages = [
            {
                "label": label,
                "count": stage_counts.get(label, 0),
                "color": stage_colors.get(label.lower(), "#9ca3af"),
            }
            for label in ["Nuevos", "Contactados", "Calificados", "Propuesta", "Ganados"]
            if label in stage_counts or label in ["Nuevos", "Contactados", "Calificados", "Propuesta", "Ganados"]
        ]
    else:
        stages = [
            {"label": "Nuevos", "count": 12, "color": "#3b82f6"},
            {"label": "Contactados", "count": 8, "color": "#f59e0b"},
            {"label": "Calificados", "count": 5, "color": "#10b981"},
            {"label": "Propuesta", "count": 3, "color": "#8b5cf6"},
            {"label": "Ganados", "count": 2, "color": "#22c55e"},
        ]

    # Calculate conversion rate
    total = len(real_leads) if real_leads else 30
    won = len([l for l in real_leads if l.get("stage") == "won"]) if real_leads else 2
    conversion_rate = int((won / total * 100)) if total > 0 else 17

    funnel = funnel_chart("Embudo de Ventas", stages)
    conversion_kpi = kpi_card("Tasa de Conversion", f"{conversion_rate}%", icon="trend_up", color="#22c55e")

    return ActionResult(
        success=True,
        action_taken="view_pipeline",
        result_data={"funnel": stages, "conversion_rate": conversion_rate},
        visual_type="chart",
        message=f"Tu embudo de ventas muestra una tasa de conversion del {conversion_rate}%.",
        next_suggestions=[
            "Ver el kanban",
            "Ver leads hot",
            "Ver predicciones",
        ],
        visual_components=[conversion_kpi, funnel],
    )


def _handle_view_dashboard(intent: IntentMatch, context: dict) -> ActionResult:
    # Fetch real data
    real_leads = _run_async(_get_leads_from_db(limit=500)) or []
    real_tickets = _run_async(_get_tickets_from_db(limit=500)) or []

    # Calculate real KPIs
    total_leads = len(real_leads) if real_leads else 37
    avg_score = int(sum([l.get("score", 0) for l in real_leads]) / len(real_leads)) if real_leads else 72
    open_tickets = len([t for t in real_tickets if t.get("status") == "open"]) if real_tickets else 14
    won_leads = len([l for l in real_leads if l.get("stage") == "won"]) if real_leads else 2
    conversion_rate = int((won_leads / total_leads * 100)) if total_leads > 0 else 17

    dashboard_data = {
        "sales": {"total_leads": total_leads, "avg_score": avg_score, "conversion_rate": conversion_rate},
        "support": {"open_tickets": open_tickets, "avg_resolution_hours": 4.2, "satisfaction": 4.5},
        "activity": {"events_today": 128, "active_campaigns": 3},
    }

    # KPI cards with real data
    kpis = [
        kpi_card("Total Leads", total_leads, icon="people", trend=f"+{len([l for l in real_leads if l.get('stage') == 'qualified'])} calificados", color="#3b82f6"),
        kpi_card("Tickets Abiertos", open_tickets, icon="ticket", color="#f59e0b"),
        kpi_card("Tasa de Conversion", f"{conversion_rate}%", icon="trend_up", color="#22c55e"),
        kpi_card("Score Promedio", avg_score, icon="star", color="#8b5cf6"),
        kpi_card("Satisfaccion", "4.5/5", icon="heart", color="#ec4899"),
        kpi_card("Campanas Activas", 3, icon="campaign", color="#6366f1"),
    ]

    # Count leads by stage for funnel
    stage_counts = {}
    stage_labels_map = {
        "new": "Nuevos",
        "qualified": "Calificados",
        "contacted": "Contactados",
        "meeting": "Reunion",
        "proposal": "Propuesta",
        "negotiation": "Negociacion",
        "won": "Ganados",
    }

    stage_colors = {
        "Nuevos": "#3b82f6",
        "Contactados": "#f59e0b",
        "Calificados": "#10b981",
        "Propuesta": "#8b5cf6",
        "Ganados": "#22c55e",
    }

    for ld in real_leads:
        stage = ld.get("stage", "new")
        label = stage_labels_map.get(stage, stage)
        stage_counts[label] = stage_counts.get(label, 0) + 1

    funnel_data = [
        {
            "label": label,
            "count": stage_counts.get(label, 0),
            "color": stage_colors.get(label, "#9ca3af"),
        }
        for label in ["Nuevos", "Contactados", "Calificados", "Propuesta", "Ganados"]
    ]

    if not any(d["count"] > 0 for d in funnel_data):
        funnel_data = [
            {"label": "Nuevos", "count": 12, "color": "#3b82f6"},
            {"label": "Contactados", "count": 8, "color": "#f59e0b"},
            {"label": "Calificados", "count": 5, "color": "#10b981"},
            {"label": "Propuesta", "count": 3, "color": "#8b5cf6"},
            {"label": "Ganados", "count": 2, "color": "#22c55e"},
        ]

    funnel = funnel_chart("Pipeline de Ventas", funnel_data)

    components = kpis + [funnel]

    return ActionResult(
        success=True,
        action_taken="view_dashboard",
        result_data=dashboard_data,
        visual_type="card",
        message=(
            f"Dashboard actualizado: {total_leads} leads activos, {open_tickets} tickets abiertos, "
            f"tasa de conversion {conversion_rate}%, satisfaccion 4.5/5."
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
    # Try real data first
    real_tickets = _run_async(_get_tickets_from_db(limit=20))

    if real_tickets:
        tickets_data = real_tickets
    else:
        # Fallback to sample data
        tickets_data = [
            {"id": 100, "subject": "Error en login", "status": "open", "priority": "high"},
            {"id": 101, "subject": "Consulta sobre facturacion", "status": "open", "priority": "medium"},
            {"id": 102, "subject": "Solicitud de nueva feature", "status": "in_progress", "priority": "low"},
            {"id": 103, "subject": "Integracion con Slack falla", "status": "open", "priority": "high"},
        ]

    tickets_table = table(
        "Tickets Activos",
        headers=["ID", "Asunto", "Estado", "Prioridad"],
        rows=[
            [t["id"], t["subject"], t.get("status", "open"), t.get("priority", "medium")]
            for t in tickets_data
        ],
        actions=["Ver detalle", "Responder", "Escalar"],
    )

    return ActionResult(
        success=True,
        action_taken="list_tickets",
        result_data={"tickets": tickets_data, "total": len(tickets_data)},
        visual_type="table",
        message=f"Hay {len(tickets_data)} tickets activos.",
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
    # Try to fetch forecast from deal_manager
    forecast = None
    try:
        forecast = deal_manager.get_forecast("default")
    except Exception as e:
        logger.debug(f"Failed to fetch forecast from deal_manager: {e}")

    if forecast:
        current_month = forecast.get("current_month_revenue", 45000)
        next_month = forecast.get("next_month_revenue", 52000)
        expected_conversions = forecast.get("expected_conversions", 6)
        pipeline_value = forecast.get("total_pipeline_value", 180000)
        at_risk = forecast.get("at_risk_count", 3)
    else:
        current_month = 45000
        next_month = 52000
        expected_conversions = 6
        pipeline_value = 180000
        at_risk = 3

    trend_pct = int((next_month - current_month) / current_month * 100) if current_month > 0 else 15

    predictions = {
        "revenue_forecast": {
            "current_month": current_month,
            "next_month": next_month,
            "trend": "up" if trend_pct > 0 else "down",
            "confidence": 0.78,
        },
        "lead_conversion_forecast": {
            "expected_conversions": expected_conversions,
            "pipeline_value": pipeline_value,
        },
        "churn_risk": {
            "at_risk_customers": at_risk,
            "top_risk": "CloudNet (72% probabilidad de churn)" if at_risk > 0 else "Ninguno detectado",
        },
    }

    # KPI cards for key predictions
    kpis = [
        kpi_card("Ingresos Este Mes", f"${current_month:,}", icon="money", color="#3b82f6"),
        kpi_card("Pronostico Prox. Mes", f"${next_month:,}", icon="trend_up", trend=f"+{trend_pct}%", color="#22c55e"),
        kpi_card("Conversiones Esperadas", expected_conversions, icon="funnel", color="#8b5cf6"),
        kpi_card("Valor del Pipeline", f"${pipeline_value:,}", icon="pipeline", color="#6366f1"),
        kpi_card("Clientes en Riesgo", at_risk, icon="warning", color="#ef4444"),
    ]

    # Bar chart for pipeline forecast by month
    pipeline_chart = bar_chart(
        "Pronostico de Ingresos",
        labels=["Ene", "Feb", "Mar", "Abr (est)", "May (est)", "Jun (est)"],
        values=[38000, 41000, current_month, 49000, next_month, 55000],
        colors=["#3b82f6", "#3b82f6", "#3b82f6", "#93c5fd", "#93c5fd", "#93c5fd"],
    )

    components = kpis + [pipeline_chart]

    return ActionResult(
        success=True,
        action_taken="view_predictions",
        result_data={"predictions": predictions},
        visual_type="chart",
        message=(
            f"Pronostico: ingresos estimados ${next_month:,} proximo mes (+{trend_pct}%). "
            f"{expected_conversions} conversiones esperadas. {at_risk} clientes en riesgo de churn."
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
