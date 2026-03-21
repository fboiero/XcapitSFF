"""Email Template Manager — reusable email templates with variable rendering.

Manages a library of email templates organized by category, with support
for {{variable}} placeholders, rendering, previewing, and default templates
in Spanish for common CRM workflows.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

_VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


class TemplateCategory(str, Enum):
    OUTREACH = "outreach"
    FOLLOW_UP = "follow_up"
    WELCOME = "welcome"
    ONBOARDING = "onboarding"
    NURTURE = "nurture"
    RE_ENGAGEMENT = "re_engagement"
    ANNOUNCEMENT = "announcement"
    INTERNAL = "internal"


@dataclass
class EmailTemplate:
    id: str
    tenant_id: str
    name: str
    category: TemplateCategory
    subject: str
    body_html: str
    body_text: str
    variables: list[str]
    thumbnail_preview: str = ""
    tags: list[str] = field(default_factory=list)
    is_default: bool = False
    usage_count: int = 0
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=None))
    updated_at: datetime = field(default_factory=lambda: datetime.now(tz=None))


def _extract_variables(subject: str, body_html: str, body_text: str = "") -> list[str]:
    """Extract unique {{variable}} names from subject, body_html, and body_text."""
    combined = f"{subject} {body_html} {body_text}"
    return sorted(set(_VARIABLE_PATTERN.findall(combined)))


def _render_text(text: str, variables: dict) -> str:
    """Replace {{variable}} placeholders with values from the variables dict."""
    def replacer(match: re.Match) -> str:
        key = match.group(1)
        return str(variables.get(key, match.group(0)))
    return _VARIABLE_PATTERN.sub(replacer, text)


def _strip_html(html: str) -> str:
    """Naive HTML tag stripping for auto-generating body_text."""
    return re.sub(r"<[^>]+>", "", html).strip()


# ---------------------------------------------------------------------------
# Default templates (Spanish, 15+ covering every category)
# ---------------------------------------------------------------------------

_DEFAULT_TEMPLATES: list[dict] = [
    # OUTREACH (3)
    {
        "name": "Primer contacto comercial",
        "category": TemplateCategory.OUTREACH,
        "subject": "{{empresa}}, potenciemos juntos su crecimiento",
        "body_html": "<p>Hola {{nombre}},</p><p>Soy {{remitente}} de Xcapit. Noté que {{empresa}} está creciendo en {{region}} y creo que podemos ayudarles a acelerar sus resultados.</p><p>¿Le interesaría una llamada breve esta semana?</p><p>Saludos,<br>{{remitente}}</p>",
        "tags": ["cold", "comercial"],
    },
    {
        "name": "Propuesta de valor técnica",
        "category": TemplateCategory.OUTREACH,
        "subject": "Solución técnica para {{empresa}}",
        "body_html": "<p>Hola {{nombre}},</p><p>En Xcapit hemos desarrollado una plataforma que resuelve {{problema}} de forma automatizada. Empresas como {{referencia}} ya la utilizan con excelentes resultados.</p><p>¿Podemos agendar una demo de 20 minutos?</p><p>{{remitente}}</p>",
        "tags": ["técnico", "demo"],
    },
    {
        "name": "Introducción ejecutiva",
        "category": TemplateCategory.OUTREACH,
        "subject": "{{nombre}}, una oportunidad para {{empresa}}",
        "body_html": "<p>Estimado/a {{nombre}},</p><p>Me dirijo a usted porque {{empresa}} está en una posición ideal para beneficiarse de nuestra tecnología. Me encantaría presentarle brevemente cómo podemos agregar valor.</p><p>Quedo atento,<br>{{remitente}}</p>",
        "tags": ["ejecutivo", "c-level"],
    },
    # FOLLOW_UP (2)
    {
        "name": "Seguimiento post-llamada",
        "category": TemplateCategory.FOLLOW_UP,
        "subject": "Resumen de nuestra conversación, {{nombre}}",
        "body_html": "<p>Hola {{nombre}},</p><p>Gracias por su tiempo hoy. Como conversamos, los próximos pasos son:</p><ul><li>{{paso_1}}</li><li>{{paso_2}}</li></ul><p>Quedo a disposición.<br>{{remitente}}</p>",
        "tags": ["seguimiento", "post-llamada"],
    },
    {
        "name": "Seguimiento sin respuesta",
        "category": TemplateCategory.FOLLOW_UP,
        "subject": "{{nombre}}, ¿pudo revisar nuestra propuesta?",
        "body_html": "<p>Hola {{nombre}},</p><p>Le escribo para dar seguimiento a mi mensaje anterior. Entiendo que tiene una agenda ocupada; estaré disponible cuando le sea conveniente.</p><p>Saludos,<br>{{remitente}}</p>",
        "tags": ["seguimiento", "reminder"],
    },
    # WELCOME (2)
    {
        "name": "Bienvenida nuevo cliente",
        "category": TemplateCategory.WELCOME,
        "subject": "¡Bienvenido/a a Xcapit, {{nombre}}!",
        "body_html": "<p>Hola {{nombre}},</p><p>¡Nos alegra tenerle como parte de la familia Xcapit! Su cuenta para {{empresa}} ya está activa.</p><p>Estos son los primeros pasos recomendados:</p><ol><li>Completar su perfil</li><li>Explorar el dashboard</li><li>Agendar su onboarding</li></ol><p>{{remitente}}</p>",
        "tags": ["bienvenida", "nuevo-cliente"],
    },
    {
        "name": "Bienvenida trial",
        "category": TemplateCategory.WELCOME,
        "subject": "Su prueba gratuita está lista, {{nombre}}",
        "body_html": "<p>Hola {{nombre}},</p><p>Su trial de {{dias_trial}} días para {{empresa}} está activo. Aproveche al máximo explorando nuestras funcionalidades principales.</p><p>¿Necesita ayuda? Responda este email.<br>{{remitente}}</p>",
        "tags": ["trial", "bienvenida"],
    },
    # ONBOARDING (2)
    {
        "name": "Guía de onboarding paso 1",
        "category": TemplateCategory.ONBOARDING,
        "subject": "Paso 1: Configure su cuenta, {{nombre}}",
        "body_html": "<p>Hola {{nombre}},</p><p>Para comenzar con {{producto}}, el primer paso es configurar su equipo. Aquí tiene una guía rápida:</p><p>{{instrucciones}}</p><p>Si tiene dudas, estamos para ayudarle.<br>{{remitente}}</p>",
        "tags": ["onboarding", "paso-1"],
    },
    {
        "name": "Onboarding completado",
        "category": TemplateCategory.ONBOARDING,
        "subject": "¡Felicitaciones {{nombre}}, onboarding completado!",
        "body_html": "<p>Hola {{nombre}},</p><p>Ha completado todos los pasos de configuración de {{producto}}. Ahora puede aprovechar al máximo todas las funcionalidades.</p><p>Recuerde que nuestro equipo de soporte está siempre disponible.<br>{{remitente}}</p>",
        "tags": ["onboarding", "completado"],
    },
    # NURTURE (2)
    {
        "name": "Contenido educativo",
        "category": TemplateCategory.NURTURE,
        "subject": "{{nombre}}, {{titulo_contenido}} que le puede interesar",
        "body_html": "<p>Hola {{nombre}},</p><p>Preparamos este recurso especialmente para profesionales como usted:</p><p><strong>{{titulo_contenido}}</strong></p><p>{{descripcion_contenido}}</p><p><a href='{{link_contenido}}'>Leer ahora</a></p><p>{{remitente}}</p>",
        "tags": ["nurture", "contenido"],
    },
    {
        "name": "Caso de éxito",
        "category": TemplateCategory.NURTURE,
        "subject": "Cómo {{empresa_caso}} logró {{resultado}}",
        "body_html": "<p>Hola {{nombre}},</p><p>Queríamos compartir cómo {{empresa_caso}} logró {{resultado}} utilizando nuestra plataforma.</p><p>¿Le gustaría conocer cómo replicar estos resultados en {{empresa}}?</p><p>{{remitente}}</p>",
        "tags": ["nurture", "caso-exito"],
    },
    # RE_ENGAGEMENT (2)
    {
        "name": "Reactivación de lead frío",
        "category": TemplateCategory.RE_ENGAGEMENT,
        "subject": "{{nombre}}, tenemos novedades para {{empresa}}",
        "body_html": "<p>Hola {{nombre}},</p><p>Hace un tiempo conversamos sobre cómo podíamos ayudar a {{empresa}}. Desde entonces hemos lanzado {{novedad}} que creemos puede ser de gran valor.</p><p>¿Le interesa retomar la conversación?<br>{{remitente}}</p>",
        "tags": ["reactivación", "lead-frío"],
    },
    {
        "name": "Oferta especial reactivación",
        "category": TemplateCategory.RE_ENGAGEMENT,
        "subject": "{{nombre}}, oferta exclusiva para {{empresa}}",
        "body_html": "<p>Hola {{nombre}},</p><p>Porque valoramos la relación con {{empresa}}, le ofrecemos {{oferta}} válida hasta {{fecha_limite}}.</p><p>¿Conversamos?<br>{{remitente}}</p>",
        "tags": ["reactivación", "oferta"],
    },
    # ANNOUNCEMENT (1)
    {
        "name": "Anuncio de nueva funcionalidad",
        "category": TemplateCategory.ANNOUNCEMENT,
        "subject": "Nuevo en Xcapit: {{funcionalidad}}",
        "body_html": "<p>Hola {{nombre}},</p><p>Nos complace anunciar el lanzamiento de <strong>{{funcionalidad}}</strong>.</p><p>{{descripcion_funcionalidad}}</p><p>Ya está disponible en su cuenta. ¡Explórela hoy!</p><p>El equipo de Xcapit</p>",
        "tags": ["anuncio", "producto"],
    },
    # INTERNAL (1)
    {
        "name": "Notificación interna de lead caliente",
        "category": TemplateCategory.INTERNAL,
        "subject": "[INTERNO] Lead caliente: {{empresa}} - Score {{score}}",
        "body_html": "<p>Equipo,</p><p>El lead <strong>{{empresa}}</strong> (contacto: {{nombre}}, email: {{email}}) ha alcanzado un score de {{score}}.</p><p>Acción recomendada: {{accion}}</p><p>— Sistema automático</p>",
        "tags": ["interno", "alerta"],
    },
]


class EmailTemplateManager:
    """Manages email templates with in-memory storage."""

    def __init__(self) -> None:
        self._templates: dict[str, EmailTemplate] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(
        self,
        tenant_id: str,
        name: str,
        category: TemplateCategory | str,
        subject: str,
        body_html: str,
        body_text: str | None = None,
        tags: list[str] | None = None,
        created_by: str | None = None,
        is_default: bool = False,
    ) -> EmailTemplate:
        if isinstance(category, str):
            category = TemplateCategory(category)

        if body_text is None:
            body_text = _strip_html(body_html)

        variables = _extract_variables(subject, body_html, body_text)

        template = EmailTemplate(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name,
            category=category,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            variables=variables,
            tags=tags or [],
            is_default=is_default,
            created_by=created_by,
        )
        self._templates[template.id] = template
        logger.info("Email template created: %s — %s", template.id, name)
        return template

    def update(self, template_id: str, **kwargs) -> EmailTemplate:
        template = self._templates.get(template_id)
        if not template:
            raise KeyError(f"Template {template_id} not found")

        for key, value in kwargs.items():
            if key == "category" and isinstance(value, str):
                value = TemplateCategory(value)
            if hasattr(template, key) and key not in ("id", "tenant_id", "created_at"):
                setattr(template, key, value)

        # Re-extract variables if subject or body changed
        if any(k in kwargs for k in ("subject", "body_html", "body_text")):
            template.variables = _extract_variables(
                template.subject, template.body_html, template.body_text
            )

        template.updated_at = datetime.now(tz=None)
        logger.info("Email template updated: %s", template_id)
        return template

    def delete(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            logger.info("Email template deleted: %s", template_id)
            return True
        return False

    def get(self, template_id: str) -> EmailTemplate | None:
        return self._templates.get(template_id)

    def list_templates(
        self,
        tenant_id: str,
        category: TemplateCategory | str | None = None,
        search: str | None = None,
    ) -> list[EmailTemplate]:
        if isinstance(category, str):
            category = TemplateCategory(category)

        results = [t for t in self._templates.values() if t.tenant_id == tenant_id]

        if category is not None:
            results = [t for t in results if t.category == category]

        if search:
            search_lower = search.lower()
            results = [
                t
                for t in results
                if search_lower in t.name.lower()
                or search_lower in t.subject.lower()
                or any(search_lower in tag.lower() for tag in t.tags)
            ]

        return sorted(results, key=lambda t: t.created_at, reverse=True)

    # ------------------------------------------------------------------
    # Render / Preview
    # ------------------------------------------------------------------

    def render(self, template_id: str, variables: dict) -> dict:
        template = self._templates.get(template_id)
        if not template:
            raise KeyError(f"Template {template_id} not found")

        return {
            "subject": _render_text(template.subject, variables),
            "body_html": _render_text(template.body_html, variables),
            "body_text": _render_text(template.body_text, variables),
        }

    def preview(self, template_id: str, sample_data: dict | None = None) -> dict:
        template = self._templates.get(template_id)
        if not template:
            raise KeyError(f"Template {template_id} not found")

        if sample_data is None:
            sample_data = {var: f"[{var}]" for var in template.variables}

        return self.render(template_id, sample_data)

    # ------------------------------------------------------------------
    # Duplicate
    # ------------------------------------------------------------------

    def duplicate(self, template_id: str, new_name: str) -> EmailTemplate:
        template = self._templates.get(template_id)
        if not template:
            raise KeyError(f"Template {template_id} not found")

        return self.create(
            tenant_id=template.tenant_id,
            name=new_name,
            category=template.category,
            subject=template.subject,
            body_html=template.body_html,
            body_text=template.body_text,
            tags=list(template.tags),
            created_by=template.created_by,
        )

    # ------------------------------------------------------------------
    # Usage tracking
    # ------------------------------------------------------------------

    def increment_usage(self, template_id: str) -> None:
        template = self._templates.get(template_id)
        if template:
            template.usage_count += 1

    # ------------------------------------------------------------------
    # Default templates
    # ------------------------------------------------------------------

    def get_default_templates(self) -> list[dict]:
        """Return the list of pre-built default template definitions."""
        return list(_DEFAULT_TEMPLATES)

    def setup_defaults(self, tenant_id: str) -> list[EmailTemplate]:
        """Create default templates for a new tenant. Returns created templates."""
        created: list[EmailTemplate] = []
        for tpl in _DEFAULT_TEMPLATES:
            template = self.create(
                tenant_id=tenant_id,
                name=tpl["name"],
                category=tpl["category"],
                subject=tpl["subject"],
                body_html=tpl["body_html"],
                tags=tpl.get("tags", []),
                is_default=True,
            )
            created.append(template)
        logger.info(
            "Set up %d default email templates for tenant %s",
            len(created),
            tenant_id,
        )
        return created


# Singleton
email_template_manager = EmailTemplateManager()
