"""Public API — endpoints for the landing page, pricing, and public info.

These don't require authentication. They power the marketing site.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/pricing")
async def pricing():
    """Public pricing page data."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_monthly": 0,
                "price_annual": 0,
                "description": "Para empezar a explorar",
                "features": [
                    "Hasta 100 leads",
                    "Hasta 50 tickets",
                    "2 usuarios",
                    "Scoring ICP básico",
                    "Knowledge Base",
                    "Routing inteligente",
                    "Templates de respuesta",
                    "Export CSV",
                    "Soporte por email",
                ],
                "cta": "Empezar gratis",
                "popular": False,
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_monthly": 99,
                "price_annual": 79,
                "description": "Para equipos en crecimiento",
                "features": [
                    "Hasta 5,000 leads",
                    "Hasta 500 tickets",
                    "10 usuarios",
                    "Scoring avanzado multi-factor",
                    "Outreach sequences automáticos",
                    "A/B testing",
                    "Lead enrichment",
                    "Pipeline automation",
                    "SLA monitoring",
                    "CSAT/NPS",
                    "CRM integration (Salesforce, HubSpot)",
                    "Agentes AI",
                    "Webhooks",
                    "Soporte prioritario",
                ],
                "cta": "Iniciar prueba gratis",
                "popular": True,
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price_monthly": 499,
                "price_annual": 399,
                "description": "Para organizaciones que necesitan todo",
                "features": [
                    "Leads ilimitados",
                    "Tickets ilimitados",
                    "Usuarios ilimitados",
                    "Todo lo de Pro +",
                    "Territory management",
                    "Predictive analytics",
                    "Agent orchestration avanzado",
                    "Compliance reports (GDPR, ISO)",
                    "White-label / marca propia",
                    "Agentes AI personalizados",
                    "Garantía SLA 99.9%",
                    "Soporte dedicado 24/7",
                    "Onboarding personalizado",
                ],
                "cta": "Contactar ventas",
                "popular": False,
            },
        ],
        "faq": [
            {
                "q": "¿Puedo cambiar de plan en cualquier momento?",
                "a": "Sí, podés upgradear o downgradear en cualquier momento. Los cambios se prorratean automáticamente.",
            },
            {
                "q": "¿Hay compromiso de permanencia?",
                "a": "No, todos los planes son mes a mes. El plan anual ofrece un descuento pero podés cancelar en cualquier momento.",
            },
            {
                "q": "¿Cómo funciona la prueba gratuita?",
                "a": "El plan Pro incluye 14 días de prueba gratis con todas las funcionalidades. No se requiere tarjeta de crédito.",
            },
            {
                "q": "¿Qué pasa con mis datos si cancelo?",
                "a": "Tus datos se mantienen por 30 días después de la cancelación. Podés exportar todo en CSV o JSON antes.",
            },
            {
                "q": "¿Los agentes AI tienen costo adicional?",
                "a": "No, el uso de agentes AI está incluido en los planes Pro y Enterprise sin costo extra.",
            },
        ],
        "currency": "USD",
        "trial_days": 14,
    }


@router.get("/features")
async def features():
    """Public features overview for marketing site."""
    return {
        "hero": {
            "title": "Software Factory con Agentes AI",
            "subtitle": "Automatizá ventas, soporte y desarrollo con agentes inteligentes",
            "cta": "Empezar gratis",
        },
        "modules": [
            {
                "name": "Ventas AI",
                "icon": "chart-line",
                "features": [
                    "Scoring ICP multi-factor automático",
                    "Pipeline con auto-avance por señales",
                    "Outreach sequences personalizados",
                    "A/B testing de mensajes",
                    "Lead enrichment automático",
                    "Territory management",
                    "CRM sync (Salesforce, HubSpot)",
                    "Predictive analytics y forecast",
                ],
            },
            {
                "name": "Soporte AI",
                "icon": "headset",
                "features": [
                    "Routing inteligente multi-señal",
                    "Respuestas automáticas con AI",
                    "SLA monitoring con auto-escalation",
                    "Knowledge Base con búsqueda semántica",
                    "Escalation workflow L1→L4",
                    "CSAT/NPS tracking",
                    "Templates de respuesta en español",
                    "Customer 360 view",
                ],
            },
            {
                "name": "Agentes AI",
                "icon": "robot",
                "features": [
                    "Sales Qualifier: califica leads automáticamente",
                    "Outreach Composer: redacta mensajes personalizados",
                    "Support Responder: genera respuestas empáticas",
                    "Ticket Router: clasifica y asigna tickets",
                    "Analytics Reporter: genera reportes ejecutivos",
                    "Integración con Argentor (Rust) para production",
                ],
            },
            {
                "name": "Plataforma",
                "icon": "cog",
                "features": [
                    "API REST completa (144+ endpoints)",
                    "Event bus para automatizaciones",
                    "Webhooks in/out",
                    "Dashboard ejecutivo",
                    "Export CSV/JSON",
                    "Audit trail completo",
                    "Multi-tenant con aislamiento de datos",
                    "Docker + CI/CD ready",
                ],
            },
        ],
        "integrations": [
            {"name": "Salesforce", "status": "available"},
            {"name": "HubSpot", "status": "available"},
            {"name": "Slack", "status": "available"},
            {"name": "WhatsApp", "status": "coming_soon"},
            {"name": "Zapier", "status": "coming_soon"},
            {"name": "Intercom", "status": "planned"},
        ],
        "stats": {
            "endpoints": "144+",
            "tests": "850+",
            "uptime_sla": "99.9%",
            "setup_time": "5 minutos",
        },
    }


@router.get("/demo")
async def demo_info():
    """Public demo information."""
    return {
        "demo_url": "/api/v1/onboarding/start",
        "demo_features": [
            "14 días de prueba gratis del plan Pro",
            "Data de demo pre-cargada",
            "Sin tarjeta de crédito",
            "Setup en 5 minutos",
        ],
        "demo_includes": {
            "sample_leads": 50,
            "sample_tickets": 20,
            "sample_kb_articles": 22,
            "sample_customers": 10,
        },
    }
