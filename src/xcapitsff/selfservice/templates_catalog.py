"""Industry templates for self-service onboarding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IndustryTemplate:
    """Pre-configured template for a specific industry."""

    template_id: str
    name: str
    description: str
    industry: str
    recommended_plan: str
    features_enabled: list[str] = field(default_factory=list)
    pipeline_stages: list[str] = field(default_factory=list)
    scoring_weights: dict[str, float] = field(default_factory=dict)
    outreach_sequences: list[str] = field(default_factory=list)
    kb_categories: list[str] = field(default_factory=list)
    sample_data_count: int = 0


# ---------------------------------------------------------------------------
# Pre-built templates (all in Spanish)
# ---------------------------------------------------------------------------

_TEMPLATES: list[IndustryTemplate] = [
    IndustryTemplate(
        template_id="fintech",
        name="Fintech / Crypto",
        description=(
            "Configuraci\u00f3n optimizada para empresas fintech y crypto. "
            "Scoring enfocado en C-level y afinidad, pipeline de 8 etapas, "
            "secuencias de outreach financieras y base de conocimiento "
            "con art\u00edculos de crypto y billing."
        ),
        industry="fintech",
        recommended_plan="professional",
        features_enabled=[
            "sales", "support", "agents", "scoring_advanced",
            "auto_qualify", "sla", "kb", "outreach",
        ],
        pipeline_stages=[
            "raw", "contacted", "qualified", "demo",
            "proposal", "negotiation", "won", "lost",
        ],
        scoring_weights={
            "c_level": 0.35,
            "afinidad": 0.30,
            "company_size": 0.15,
            "engagement": 0.10,
            "region": 0.10,
        },
        outreach_sequences=[
            "bienvenida_fintech",
            "seguimiento_producto",
            "caso_de_exito_crypto",
            "demo_personalizada",
        ],
        kb_categories=[
            "Crypto b\u00e1sico",
            "Billing y pagos",
            "Seguridad y compliance",
            "Integraciones financieras",
            "FAQ general",
        ],
        sample_data_count=50,
    ),
    IndustryTemplate(
        template_id="saas",
        name="SaaS B2B",
        description=(
            "Configuraci\u00f3n para empresas SaaS B2B. Scoring enfocado en "
            "tama\u00f1o de empresa y engagement, pipeline de 6 etapas, "
            "secuencias de outreach de producto y base de conocimiento t\u00e9cnica."
        ),
        industry="tech",
        recommended_plan="professional",
        features_enabled=[
            "sales", "support", "agents", "scoring_advanced",
            "auto_qualify", "kb", "outreach",
        ],
        pipeline_stages=[
            "raw", "contacted", "qualified", "proposal", "won", "lost",
        ],
        scoring_weights={
            "company_size": 0.30,
            "engagement": 0.30,
            "c_level": 0.20,
            "afinidad": 0.10,
            "region": 0.10,
        },
        outreach_sequences=[
            "bienvenida_saas",
            "demo_producto",
            "caso_de_exito_b2b",
            "upgrade_plan",
        ],
        kb_categories=[
            "Primeros pasos",
            "API y documentaci\u00f3n t\u00e9cnica",
            "Integraciones",
            "Billing",
            "FAQ general",
        ],
        sample_data_count=30,
    ),
    IndustryTemplate(
        template_id="consulting",
        name="Consultor\u00eda",
        description=(
            "Configuraci\u00f3n para consultoras. Scoring enfocado en presupuesto "
            "y timeline, pipeline de 5 etapas, secuencias de outreach de expertise."
        ),
        industry="consulting",
        recommended_plan="starter",
        features_enabled=[
            "sales", "support", "agents", "scoring_basic",
            "kb", "outreach",
        ],
        pipeline_stages=[
            "raw", "contacted", "qualified", "proposal", "won",
        ],
        scoring_weights={
            "budget": 0.35,
            "timeline": 0.25,
            "c_level": 0.20,
            "company_size": 0.10,
            "region": 0.10,
        },
        outreach_sequences=[
            "bienvenida_consultoria",
            "presentacion_expertise",
            "propuesta_personalizada",
        ],
        kb_categories=[
            "Servicios",
            "Metodolog\u00eda",
            "Casos de \u00e9xito",
            "FAQ general",
        ],
        sample_data_count=20,
    ),
    IndustryTemplate(
        template_id="ecommerce",
        name="E-commerce",
        description=(
            "Configuraci\u00f3n para e-commerce. Scoring enfocado en volumen "
            "y regi\u00f3n, pipeline corto de 4 etapas."
        ),
        industry="ecommerce",
        recommended_plan="starter",
        features_enabled=[
            "sales", "support", "agents", "scoring_basic",
            "auto_qualify", "kb",
        ],
        pipeline_stages=[
            "raw", "qualified", "won", "lost",
        ],
        scoring_weights={
            "volume": 0.35,
            "region": 0.25,
            "engagement": 0.20,
            "company_size": 0.20,
        },
        outreach_sequences=[
            "bienvenida_ecommerce",
            "oferta_volumen",
        ],
        kb_categories=[
            "Env\u00edos y log\u00edstica",
            "Pagos",
            "Devoluciones",
            "FAQ general",
        ],
        sample_data_count=25,
    ),
    IndustryTemplate(
        template_id="startup",
        name="Startup gen\u00e9rica",
        description=(
            "Configuraci\u00f3n ligera y MVP-friendly para startups. "
            "Ideal para arrancar r\u00e1pido con lo esencial."
        ),
        industry="tech",
        recommended_plan="free",
        features_enabled=[
            "sales", "support", "agents", "scoring_basic",
        ],
        pipeline_stages=[
            "raw", "contacted", "won", "lost",
        ],
        scoring_weights={
            "engagement": 0.40,
            "c_level": 0.30,
            "region": 0.30,
        },
        outreach_sequences=[
            "bienvenida_startup",
        ],
        kb_categories=[
            "Primeros pasos",
            "FAQ general",
        ],
        sample_data_count=10,
    ),
]


class TemplateCatalog:
    """Manages industry templates for quick onboarding."""

    def __init__(self) -> None:
        self._templates: dict[str, IndustryTemplate] = {
            t.template_id: t for t in _TEMPLATES
        }

    def list_templates(self) -> list[IndustryTemplate]:
        """Return all available industry templates."""
        return list(self._templates.values())

    def get_template(self, template_id: str) -> IndustryTemplate | None:
        """Return a single template by ID, or None."""
        return self._templates.get(template_id)

    def apply_template(self, tenant_id: str, template_id: str) -> dict[str, Any]:
        """Apply an industry template to a tenant.

        In production this would call service layers to configure the tenant.
        Here we return a summary of the applied configuration.
        """
        template = self._templates.get(template_id)
        if not template:
            raise ValueError(f"Template '{template_id}' no encontrado.")

        return {
            "tenant_id": tenant_id,
            "template_applied": template.template_id,
            "template_name": template.name,
            "recommended_plan": template.recommended_plan,
            "features_enabled": template.features_enabled,
            "pipeline_stages": template.pipeline_stages,
            "scoring_weights": template.scoring_weights,
            "outreach_sequences": template.outreach_sequences,
            "kb_categories": template.kb_categories,
            "sample_data_count": template.sample_data_count,
        }
