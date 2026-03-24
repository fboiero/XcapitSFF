"""Temporary seed endpoint for demo data injection into in-memory stores."""
from datetime import datetime, timedelta
import random

from fastapi import APIRouter

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("/demo")
async def seed_demo_data():
    """Inject Banco Patagonia demo data into all in-memory modules."""
    from xcapitsff.core.activity_log import activity_log
    from xcapitsff.core.audit import audit_log, AuditAction
    from xcapitsff.core.events import event_bus, Event, EventType
    from xcapitsff.core.notification_center import notification_center, NotificationType
    from xcapitsff.core.realtime_analytics import analytics_engine

    TENANT = "default"
    USER = "admin"
    NOW = datetime.now()
    counts = {}

    # ── Activity Log ──
    activities = [
        ("create", "lead", 1, "Lead creado: Banco Patagonia S.A. — ICP Score 85", None),
        ("update", "lead", 1, "Lead calificado: Banco Patagonia → qualified",
         {"stage": {"old": "raw", "new": "qualified"}}),
        ("create", "company", "ab3bf13f", "Company creada: Banco Patagonia S.A. — Financial Services", None),
        ("create", "contact", "7352a72d", "Contacto creado: Martín Rodríguez (CTO)", None),
        ("update", "lead", 1, "Lead avanza a proposal: propuesta enviada al CTO",
         {"stage": {"old": "qualified", "new": "proposal"}}),
        ("create", "deal", "b377bc00", "Deal creado: Core Banking Modernization — USD $2,000,000", None),
        ("create", "quote", "d1329763", "Quote generada: QT-0001 — USD $2,250,000 (5 líneas)", None),
        ("update", "lead", 1, "Lead avanza a negotiation: cliente acepta propuesta",
         {"stage": {"old": "proposal", "new": "negotiation"}}),
        ("update", "lead", 1, "DEAL WON: Banco Patagonia — contrato firmado!",
         {"stage": {"old": "negotiation", "new": "won"}}),
        ("update", "deal", "b377bc00", "Deal actualizado: probabilidad 75% → 100%",
         {"probability": {"old": 75, "new": 100}}),
        ("create", "lead", 2, "Lead creado: Mercado Libre — ICP Score 52.5", None),
        ("create", "lead", 3, "Lead creado: YPF Tecnología — ICP Score 85, C-level", None),
        ("create", "lead", 4, "Lead creado: Globant — ICP Score 40.5", None),
        ("create", "lead", 5, "Lead creado: BBVA Argentina — ICP Score 85, C-level", None),
        ("update", "lead", 2, "Mercado Libre calificado → qualified",
         {"stage": {"old": "raw", "new": "qualified"}}),
        ("update", "lead", 3, "YPF Tecnología avanza → proposal",
         {"stage": {"old": "raw", "new": "proposal"}}),
        ("update", "lead", 5, "BBVA Argentina avanza → negotiation",
         {"stage": {"old": "raw", "new": "negotiation"}}),
        ("score", "lead", 1, "ICP Scoring: Banco Patagonia = 85.0 (HIGH)",
         {"score_icp": {"old": 0, "new": 85.0}, "afinidad": {"old": None, "new": "HIGH"}}),
    ]
    for action, etype, eid, desc, changes in activities:
        activity_log.log(
            tenant_id=TENANT, user_id=USER, action=action,
            entity_type=etype, entity_id=eid, description=desc,
            changes=changes, ip="192.168.1.100", ua="XcapitSFF/Demo",
        )
    counts["activity"] = len(activities)

    # ── Audit Log ──
    audits = [
        (AuditAction.CREATE, "lead", 1, "webhook", None,
         {"source": "referral", "region": "LATAM", "company": "Banco Patagonia S.A."}),
        (AuditAction.SCORE, "lead", 1, "sales_qualifier",
         {"score_icp": {"old": 0, "new": 85.0}},
         {"model": "ICP_v2", "budget": 90, "authority": 95, "need": 85, "timeline": 80}),
        (AuditAction.QUALIFY, "lead", 1, "sales_qualifier",
         {"stage": {"old": "raw", "new": "qualified"}},
         {"reason": "ICP 85, C-level, budget USD 2M"}),
        (AuditAction.STAGE_CHANGE, "lead", 1, "admin",
         {"stage": {"old": "qualified", "new": "proposal"}},
         {"reason": "Propuesta enviada"}),
        (AuditAction.CREATE, "deal", "b377bc00", "admin", None,
         {"amount": 2000000, "currency": "USD"}),
        (AuditAction.CREATE, "quote", "d1329763", "admin", None,
         {"total": 2250000, "line_items": 5}),
        (AuditAction.STAGE_CHANGE, "lead", 1, "admin",
         {"stage": {"old": "proposal", "new": "negotiation"}}, None),
        (AuditAction.STAGE_CHANGE, "lead", 1, "admin",
         {"stage": {"old": "negotiation", "new": "won"}},
         {"reason": "Contrato firmado!"}),
        (AuditAction.CREATE, "lead", 2, "webhook", None, {"company": "Mercado Libre"}),
        (AuditAction.CREATE, "lead", 3, "webhook", None, {"company": "YPF Tecnología"}),
        (AuditAction.CREATE, "lead", 4, "webhook", None, {"company": "Globant"}),
        (AuditAction.CREATE, "lead", 5, "webhook", None, {"company": "BBVA Argentina"}),
        (AuditAction.QUALIFY, "lead", 2, "sales_qualifier",
         {"stage": {"old": "raw", "new": "qualified"}}, None),
        (AuditAction.STAGE_CHANGE, "lead", 3, "admin",
         {"stage": {"old": "qualified", "new": "proposal"}}, None),
        (AuditAction.STAGE_CHANGE, "lead", 5, "admin",
         {"stage": {"old": "proposal", "new": "negotiation"}}, None),
    ]
    for action, etype, eid, actor, changes, meta in audits:
        audit_log.record(action=action, entity_type=etype, entity_id=eid,
                         actor=actor, changes=changes, metadata=meta)
    counts["audit"] = len(audits)

    # ── Event Bus ──
    events = [
        (EventType.LEAD_CREATED, {"lead_id": 1, "company_name": "Banco Patagonia S.A.", "score_icp": 85.0, "region": "LATAM"}, "webhook"),
        (EventType.LEAD_SCORED, {"lead_id": 1, "score": 85.0, "afinidad": "HIGH"}, "sales_qualifier"),
        (EventType.LEAD_QUALIFIED, {"lead_id": 1, "company_name": "Banco Patagonia S.A."}, "sales_qualifier"),
        (EventType.LEAD_STAGE_CHANGED, {"lead_id": 1, "old_stage": "qualified", "new_stage": "proposal"}, "admin"),
        (EventType.LEAD_STAGE_CHANGED, {"lead_id": 1, "old_stage": "proposal", "new_stage": "negotiation"}, "admin"),
        (EventType.LEAD_STAGE_CHANGED, {"lead_id": 1, "old_stage": "negotiation", "new_stage": "won"}, "admin"),
        (EventType.LEAD_CREATED, {"lead_id": 2, "company_name": "Mercado Libre", "score_icp": 52.5}, "webhook"),
        (EventType.LEAD_CREATED, {"lead_id": 3, "company_name": "YPF Tecnología", "score_icp": 85.0}, "webhook"),
        (EventType.LEAD_CREATED, {"lead_id": 4, "company_name": "Globant", "score_icp": 40.5}, "webhook"),
        (EventType.LEAD_CREATED, {"lead_id": 5, "company_name": "BBVA Argentina", "score_icp": 85.0}, "webhook"),
        (EventType.LEAD_QUALIFIED, {"lead_id": 2, "company_name": "Mercado Libre"}, "sales_qualifier"),
        (EventType.LEAD_STAGE_CHANGED, {"lead_id": 3, "old_stage": "qualified", "new_stage": "proposal"}, "admin"),
        (EventType.LEAD_STAGE_CHANGED, {"lead_id": 5, "old_stage": "proposal", "new_stage": "negotiation"}, "admin"),
        (EventType.OUTREACH_SENT, {"lead_id": 1, "template": "enterprise_intro", "channel": "email"}, "outreach_composer"),
        (EventType.AGENT_TASK_COMPLETED, {"agent": "sales_qualifier", "task": "qualify_lead", "lead_id": 1}, "orchestrator"),
        (EventType.AGENT_TASK_COMPLETED, {"agent": "outreach_composer", "task": "compose_email", "lead_id": 1}, "orchestrator"),
        (EventType.CUSTOMER_CREATED, {"company": "Banco Patagonia S.A.", "contact": "Martín Rodríguez"}, "admin"),
    ]
    for etype, data, source in events:
        evt = Event(type=etype, data=data, source=source)
        await event_bus.emit(evt)
    counts["events"] = len(events)

    # ── Notification Center ──
    notifications = [
        (NotificationType.LEAD_HOT, "Lead Hot: Banco Patagonia",
         "ICP score 85 — C-level, budget USD 2M confirmado", "/leads/1", {"score": 85}),
        (NotificationType.SUCCESS, "Lead Calificado",
         "Banco Patagonia calificado por Sales Qualifier Agent", "/leads/1", None),
        (NotificationType.INFO, "Propuesta Generada",
         "Quote QT-0001: USD $2,250,000 — 5 líneas de servicio", "/deals/b377bc00", None),
        (NotificationType.DEAL_WON, "Deal Ganado!",
         "Core Banking Modernization — Banco Patagonia: USD $2,000,000", "/deals/b377bc00", {"amount": 2000000}),
        (NotificationType.ASSIGNMENT, "Lead Asignado",
         "Mercado Libre (score 52.5) asignado para seguimiento", "/leads/2", None),
        (NotificationType.INFO, "Nuevo Lead: YPF Tecnología",
         "Lead desde evento: YPF Tecnología — C-level, ICP 85", "/leads/3", None),
        (NotificationType.WARNING, "Lead Frío: Globant",
         "Globant ICP 40.5 — revisar seguimiento", "/leads/4", None),
        (NotificationType.LEAD_HOT, "Lead Hot: BBVA Argentina",
         "Referido por Banco Patagonia, ICP 85, C-level", "/leads/5", {"score": 85}),
        (NotificationType.INFO, "Agent Completado",
         "Sales Qualifier: 5 leads procesados, 3 calificados", "/history", None),
        (NotificationType.SYSTEM, "Resumen Diario",
         "5 leads nuevos, 1 deal cerrado ($2M), conversión 20%", "/analytics", None),
    ]
    for ntype, title, message, link, meta in notifications:
        notification_center.notify(
            tenant_id=TENANT, user_id=USER, type=ntype,
            title=title, message=message, link=link, metadata=meta,
        )
    counts["notifications"] = len(notifications)

    # ── Realtime Analytics ──
    metrics = [
        ("lead.created", 1.0, {"region": "LATAM", "source": "referral"}),
        ("lead.created", 1.0, {"region": "LATAM", "source": "web"}),
        ("lead.created", 1.0, {"region": "LATAM", "source": "event"}),
        ("lead.created", 1.0, {"region": "LATAM", "source": "cold"}),
        ("lead.created", 1.0, {"region": "LATAM", "source": "referral"}),
        ("lead.qualified", 1.0, {"region": "LATAM"}),
        ("lead.qualified", 1.0, {"region": "LATAM"}),
        ("lead.qualified", 1.0, {"region": "LATAM"}),
        ("lead.converted", 1.0, {"region": "LATAM", "industry": "Banking"}),
        ("revenue.won", 2000000.0, {"region": "LATAM", "industry": "Banking"}),
        ("outreach.sent", 1.0, {"channel": "email"}),
        ("outreach.sent", 1.0, {"channel": "email"}),
        ("outreach.opened", 1.0, {"channel": "email"}),
        ("outreach.replied", 1.0, {"channel": "email"}),
        ("meeting.booked", 1.0, {"type": "discovery"}),
        ("meeting.booked", 1.0, {"type": "proposal_review"}),
    ]
    for metric_name, value, dims in metrics:
        analytics_engine.record_event(
            tenant_id=TENANT, metric_name=metric_name, value=value, dimensions=dims,
        )
    counts["analytics_today"] = len(metrics)

    # Historical data (7 days)
    hist_count = 0
    for days_ago in range(7, 0, -1):
        ts = NOW - timedelta(days=days_ago)
        for _ in range(random.randint(1, 4)):
            analytics_engine.record_event(
                tenant_id=TENANT, metric_name="lead.created", value=1.0,
                dimensions={"region": random.choice(["LATAM", "Iberia"])},
                timestamp=ts,
            )
            hist_count += 1
        if random.random() > 0.3:
            analytics_engine.record_event(
                tenant_id=TENANT, metric_name="lead.qualified", value=1.0,
                dimensions={"region": "LATAM"}, timestamp=ts,
            )
            hist_count += 1
        if random.random() > 0.5:
            analytics_engine.record_event(
                tenant_id=TENANT, metric_name="outreach.sent", value=1.0,
                dimensions={"channel": "email"}, timestamp=ts,
            )
            hist_count += 1
    counts["analytics_historical"] = hist_count

    return {"status": "ok", "counts": counts}
