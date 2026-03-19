"""Outreach Template Engine — composable, personalised sales messaging.

This module provides a complete template system for multi-channel outreach
(email, LinkedIn, WhatsApp) with:

- A registry of 12+ Spanish-language templates covering hot/warm/cool leads,
  C-level vs. non-C-level contacts, LATAM vs. Iberia language variants, and
  follow-up sequences.
- Automatic template selection based on lead data (region, seniority, score).
- Message composition with personalisation scoring.
- A/B variant generation for split testing.
- Follow-up sequence management (up to 3 attempts).
- Batch composition for bulk outreach campaigns.

Templates use Python's ``str.format_map`` for variable interpolation — no
external dependencies required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Channel(str, Enum):
    """Supported outreach channels."""

    EMAIL = "email"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"


class Language(str, Enum):
    """Spanish language variants."""

    ES_LATAM = "es_latam"
    ES_IBERIA = "es_iberia"


class LeadTemperature(str, Enum):
    """Lead classification by engagement temperature."""

    HOT = "hot"
    WARM = "warm"
    COOL = "cool"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Template:
    """An outreach message template.

    Attributes:
        id: Unique template identifier.
        channel: Target channel (email, linkedin, whatsapp).
        language: Language variant.
        lead_temperature: Temperature segment the template targets.
        is_c_level: Whether the template is tailored for C-level contacts.
        subject: Email subject line (may be ``None`` for non-email channels).
        body: Message body with ``{placeholder}`` variables.
        cta: Call-to-action text.
        is_followup: Whether this is a follow-up template.
        followup_attempt: Attempt number (1, 2, 3) if ``is_followup`` is True.
    """

    id: str
    channel: Channel
    language: Language
    lead_temperature: LeadTemperature
    is_c_level: bool
    subject: str | None
    body: str
    cta: str
    is_followup: bool = False
    followup_attempt: int = 0


@dataclass
class OutreachDraft:
    """A fully composed outreach message ready for sending.

    Attributes:
        subject: Rendered subject line (``None`` for non-email channels).
        body: Rendered message body.
        channel: The channel this draft targets.
        template_used: Identifier of the template that was used.
        personalization_score: Float 0-1 indicating how many personalisation
            placeholders could be filled with real lead data.
    """

    subject: str | None
    body: str
    channel: Channel
    template_used: str
    personalization_score: float


# ---------------------------------------------------------------------------
# Personalisation placeholders & helpers
# ---------------------------------------------------------------------------

# All placeholders that templates may reference.
ALL_PLACEHOLDERS: set[str] = {
    "contact_name",
    "company_name",
    "region",
    "product_interest",
    "sender_name",
    "sender_title",
}

# Default fallback values when lead data is incomplete.
_DEFAULTS: dict[str, str] = {
    "contact_name": "estimado/a",
    "company_name": "su empresa",
    "region": "",
    "product_interest": "soluciones de inversion automatizada",
    "sender_name": "El equipo de Xcapit",
    "sender_title": "Asesor de Inversiones",
}


def _build_format_map(lead_data: dict[str, Any]) -> dict[str, str]:
    """Build a safe format-map from lead data, filling missing keys with defaults."""
    fmt: dict[str, str] = {}
    for key in ALL_PLACEHOLDERS:
        value = lead_data.get(key)
        if value is not None and str(value).strip():
            fmt[key] = str(value).strip()
        else:
            fmt[key] = _DEFAULTS.get(key, "")
    return fmt


def _compute_personalization_score(lead_data: dict[str, Any]) -> float:
    """Return 0-1 score based on how many personalisation fields are filled."""
    filled = 0
    for key in ALL_PLACEHOLDERS:
        value = lead_data.get(key)
        if value is not None and str(value).strip():
            filled += 1
    return round(filled / len(ALL_PLACEHOLDERS), 2) if ALL_PLACEHOLDERS else 0.0


def _safe_render(template_str: str, fmt: dict[str, str]) -> str:
    """Render a template string using ``str.format_map`` with safe fallbacks."""
    try:
        return template_str.format_map(fmt)
    except (KeyError, ValueError, IndexError):
        return template_str


# ---------------------------------------------------------------------------
# Detect language from lead data
# ---------------------------------------------------------------------------


def _detect_language(lead_data: dict[str, Any]) -> Language:
    """Infer the language variant from the lead's region."""
    region = str(lead_data.get("region", "LATAM")).strip().upper()
    if region in ("IBERIA", "IBÉRIA"):
        return Language.ES_IBERIA
    return Language.ES_LATAM


# ---------------------------------------------------------------------------
# Detect lead temperature from lead data
# ---------------------------------------------------------------------------


def _detect_temperature(lead_data: dict[str, Any]) -> LeadTemperature:
    """Infer lead temperature from classification or score."""
    classification = str(lead_data.get("classification", "")).strip().lower()
    if classification in ("hot",):
        return LeadTemperature.HOT
    if classification in ("warm",):
        return LeadTemperature.WARM
    if classification in ("cool", "cold"):
        return LeadTemperature.COOL

    # Fallback: derive from numeric score
    score = lead_data.get("score_icp") or lead_data.get("score")
    if score is not None:
        try:
            s = float(score)
        except (TypeError, ValueError):
            return LeadTemperature.COOL
        if s >= 70:
            return LeadTemperature.HOT
        if s >= 45:
            return LeadTemperature.WARM
        return LeadTemperature.COOL

    # Fallback: afinidad-based
    afinidad = str(lead_data.get("afinidad", "")).strip().upper()
    if afinidad == "HIGH":
        return LeadTemperature.HOT
    if afinidad == "MEDIUM":
        return LeadTemperature.WARM
    return LeadTemperature.COOL


# ---------------------------------------------------------------------------
# Template Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Template] = {}


def _register(t: Template) -> Template:
    """Add a template to the global registry."""
    _REGISTRY[t.id] = t
    return t


def get_registry() -> dict[str, Template]:
    """Return a shallow copy of the template registry."""
    return dict(_REGISTRY)


def get_template(template_id: str) -> Template | None:
    """Look up a template by its identifier."""
    return _REGISTRY.get(template_id)


# ---------------------------------------------------------------------------
# EMAIL templates
# ---------------------------------------------------------------------------

# 1. Hot C-level LATAM
_register(Template(
    id="email_hot_clevel_latam",
    channel=Channel.EMAIL,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.HOT,
    is_c_level=True,
    subject="Oportunidad exclusiva para {company_name}: rendimientos optimizados con Xcapit",
    body=(
        "Hola {contact_name},\n\n"
        "Soy {sender_name}, {sender_title} en Xcapit. Trabajo con ejecutivos de alto nivel "
        "en la region que estan transformando la manera en que sus organizaciones gestionan "
        "activos digitales.\n\n"
        "Entendemos que en {company_name} buscan maximizar retornos con estrategias innovadoras. "
        "Nuestras soluciones de inversion automatizada y estrategias DeFi han generado "
        "rendimientos consistentes para empresas lideres en LATAM.\n\n"
        "Me encantaria compartir como podriamos optimizar el portafolio de {company_name} "
        "con nuestro enfoque de gestion de activos digitales.\n\n"
        "Quedo a su disposicion para coordinar una reunion esta semana."
    ),
    cta="Agendar una reunion de 20 minutos para explorar oportunidades de inversion",
))

# 2. Warm non-C-level LATAM
_register(Template(
    id="email_warm_nonclevel_latam",
    channel=Channel.EMAIL,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.WARM,
    is_c_level=False,
    subject="Como {company_name} puede optimizar su gestion de activos digitales",
    body=(
        "Hola {contact_name},\n\n"
        "Soy {sender_name} de Xcapit. Ayudamos a empresas como {company_name} a implementar "
        "soluciones de inversion automatizada que simplifican la gestion de portafolios "
        "y maximizan rendimientos.\n\n"
        "Nuestras herramientas de optimizacion de portafolio y estrategias de rendimiento DeFi "
        "estan disenadas para equipos que buscan eficiencia sin sacrificar control.\n\n"
        "Me gustaria entender mejor los objetivos de inversion de {company_name} y compartir "
        "como nuestras soluciones pueden ayudarlos."
    ),
    cta="Solicitar una demo personalizada de la plataforma Xcapit",
))

# 3. Cool Iberia
_register(Template(
    id="email_cool_iberia",
    channel=Channel.EMAIL,
    language=Language.ES_IBERIA,
    lead_temperature=LeadTemperature.COOL,
    is_c_level=False,
    subject="Descubrid como Xcapit esta transformando la gestion de activos digitales",
    body=(
        "Hola {contact_name},\n\n"
        "Soy {sender_name} de Xcapit. Os escribo porque creemos que {company_name} "
        "podria beneficiarse de las tendencias en gestion de activos digitales que "
        "estamos viendo en el mercado.\n\n"
        "En Xcapit ofrecemos soluciones de inversion automatizada, gestion de activos "
        "digitales y estrategias de rendimiento DeFi adaptadas al mercado iberico.\n\n"
        "Hemos preparado un informe sobre optimizacion de portafolio que podria ser "
        "relevante para vuestro equipo."
    ),
    cta="Descargar el informe gratuito sobre optimizacion de portafolio",
))

# ---------------------------------------------------------------------------
# LINKEDIN templates
# ---------------------------------------------------------------------------

# 4. LinkedIn hot
_register(Template(
    id="linkedin_hot",
    channel=Channel.LINKEDIN,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.HOT,
    is_c_level=True,
    subject=None,
    body=(
        "Hola {contact_name}, vi tu perfil y me parecio muy interesante tu trayectoria "
        "en {company_name}.\n\n"
        "Lidero el area de alianzas estrategicas en Xcapit, donde ayudamos a empresas "
        "a implementar soluciones de inversion automatizada y gestion de activos digitales.\n\n"
        "Me encantaria conectar y explorar posibles sinergias entre nuestros equipos."
    ),
    cta="Conectar para explorar oportunidades de colaboracion",
))

# 5. LinkedIn warm
_register(Template(
    id="linkedin_warm",
    channel=Channel.LINKEDIN,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.WARM,
    is_c_level=False,
    subject=None,
    body=(
        "Hola {contact_name}, trabajo en Xcapit donde desarrollamos soluciones de "
        "inversion automatizada y estrategias de rendimiento DeFi.\n\n"
        "Vi que {company_name} esta en un sector donde la optimizacion de portafolio "
        "puede generar un impacto significativo. Me gustaria compartir algunas ideas "
        "que podrian ser utiles."
    ),
    cta="Me gustaria conectar y compartir ideas",
))

# 6. LinkedIn cool
_register(Template(
    id="linkedin_cool",
    channel=Channel.LINKEDIN,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.COOL,
    is_c_level=False,
    subject=None,
    body=(
        "Hola {contact_name}, soy {sender_name} de Xcapit. Publicamos contenido "
        "sobre tendencias en inversion automatizada y gestion de activos digitales "
        "que podria interesarte.\n\n"
        "Si te parece relevante, me encantaria conectar."
    ),
    cta="Conectar para mantenernos en contacto",
))

# ---------------------------------------------------------------------------
# WHATSAPP templates
# ---------------------------------------------------------------------------

# 7. WhatsApp hot
_register(Template(
    id="whatsapp_hot",
    channel=Channel.WHATSAPP,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.HOT,
    is_c_level=True,
    subject=None,
    body=(
        "Hola {contact_name}! Soy {sender_name} de Xcapit. "
        "Queria comentarte sobre una oportunidad exclusiva de inversion automatizada "
        "para {company_name}. Nuestras estrategias DeFi estan generando resultados "
        "muy interesantes en la region. Te gustaria que coordinemos una llamada breve?"
    ),
    cta="Coordinar llamada de 15 minutos",
))

# 8. WhatsApp warm
_register(Template(
    id="whatsapp_warm",
    channel=Channel.WHATSAPP,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.WARM,
    is_c_level=False,
    subject=None,
    body=(
        "Hola {contact_name}! Soy {sender_name} de Xcapit. "
        "Ayudamos a empresas como {company_name} con soluciones de inversion "
        "automatizada y optimizacion de portafolio. Te comparto informacion? "
        "Sin compromiso."
    ),
    cta="Recibir informacion sobre soluciones Xcapit",
))

# 9. WhatsApp cool
_register(Template(
    id="whatsapp_cool",
    channel=Channel.WHATSAPP,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.COOL,
    is_c_level=False,
    subject=None,
    body=(
        "Hola {contact_name}! De Xcapit. Tenemos un informe gratuito sobre "
        "gestion de activos digitales y estrategias de rendimiento que puede "
        "ser util para {company_name}. Te interesa recibirlo?"
    ),
    cta="Recibir informe gratuito",
))

# ---------------------------------------------------------------------------
# FOLLOW-UP templates
# ---------------------------------------------------------------------------

# 10. First follow-up (attempt 1)
_register(Template(
    id="followup_1",
    channel=Channel.EMAIL,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.WARM,
    is_c_level=False,
    subject="Siguiendo con nuestra conversacion — {company_name} y Xcapit",
    body=(
        "Hola {contact_name},\n\n"
        "Te escribo para dar seguimiento a mi mensaje anterior. En Xcapit "
        "seguimos trabajando con empresas de la region para implementar soluciones "
        "de inversion automatizada y estrategias de rendimiento DeFi.\n\n"
        "Entiendo que los tiempos pueden ser ajustados, pero me encantaria encontrar "
        "un momento para conversar sobre como podemos ayudar a {company_name} a "
        "optimizar su gestion de activos digitales.\n\n"
        "Quedo atento a tu respuesta."
    ),
    cta="Responder para coordinar una breve llamada",
    is_followup=True,
    followup_attempt=1,
))

# 11. Second follow-up (attempt 2)
_register(Template(
    id="followup_2",
    channel=Channel.EMAIL,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.WARM,
    is_c_level=False,
    subject="Caso de exito relevante para {company_name}",
    body=(
        "Hola {contact_name},\n\n"
        "Queria compartirte brevemente un caso de exito reciente. Una empresa "
        "similar a {company_name} logro optimizar su portafolio un 35% utilizando "
        "nuestras soluciones de inversion automatizada y estrategias DeFi.\n\n"
        "Si te interesa conocer los detalles y ver como podriamos replicar esos "
        "resultados para {company_name}, estoy disponible para una llamada rapida.\n\n"
        "Saludos cordiales,\n{sender_name}"
    ),
    cta="Conocer el caso de exito completo",
    is_followup=True,
    followup_attempt=2,
))

# 12. Final follow-up (attempt 3)
_register(Template(
    id="followup_3",
    channel=Channel.EMAIL,
    language=Language.ES_LATAM,
    lead_temperature=LeadTemperature.WARM,
    is_c_level=False,
    subject="Ultimo contacto — recursos para {company_name}",
    body=(
        "Hola {contact_name},\n\n"
        "Entiendo que quizas no sea el momento adecuado para explorar nuevas "
        "soluciones de gestion de activos digitales. No quiero ser insistente.\n\n"
        "Te dejo un enlace a nuestros recursos gratuitos sobre inversion "
        "automatizada y optimizacion de portafolio por si resultan utiles en el "
        "futuro.\n\n"
        "Si en algun momento {company_name} necesita apoyo en esta area, no dudes "
        "en contactarme.\n\n"
        "Un saludo,\n{sender_name}"
    ),
    cta="Acceder a recursos gratuitos de Xcapit",
    is_followup=True,
    followup_attempt=3,
))


# ---------------------------------------------------------------------------
# Template selection logic
# ---------------------------------------------------------------------------


def select_template(
    channel: Channel | str,
    lead_data: dict[str, Any],
) -> Template:
    """Auto-select the best template for a given channel and lead profile.

    Selection criteria (in priority order):
    1. Channel must match.
    2. Language variant derived from the lead's region.
    3. Lead temperature derived from classification / score / afinidad.
    4. C-level preference: prefer a matching ``is_c_level`` template when
       available; otherwise fall back to the closest match.

    Args:
        channel: Target outreach channel.
        lead_data: Dict containing lead attributes (``region``, ``c_level``,
            ``classification``, ``score_icp``, ``afinidad``, etc.).

    Returns:
        The best-matching ``Template`` from the registry.

    Raises:
        ValueError: If no suitable template is found for the channel.
    """
    if isinstance(channel, str):
        channel = Channel(channel.lower())

    language = _detect_language(lead_data)
    temperature = _detect_temperature(lead_data)
    is_c_level = bool(lead_data.get("c_level", False))

    # Gather non-followup templates for the given channel
    candidates = [
        t for t in _REGISTRY.values()
        if t.channel == channel and not t.is_followup
    ]

    if not candidates:
        raise ValueError(f"No templates registered for channel '{channel.value}'")

    def _score_template(t: Template) -> int:
        """Higher is better."""
        s = 0
        if t.language == language:
            s += 4
        if t.lead_temperature == temperature:
            s += 2
        if t.is_c_level == is_c_level:
            s += 1
        return s

    candidates.sort(key=_score_template, reverse=True)
    return candidates[0]


# ---------------------------------------------------------------------------
# Message composition
# ---------------------------------------------------------------------------


def compose_message(
    lead_data: dict[str, Any],
    channel: Channel | str,
    template_override: str | None = None,
) -> OutreachDraft:
    """Compose a personalised outreach message for a single lead.

    Args:
        lead_data: Lead attributes used for template selection and rendering.
        channel: Target outreach channel.
        template_override: If provided, use this template ID instead of
            auto-selection.

    Returns:
        An ``OutreachDraft`` ready for review or sending.

    Raises:
        ValueError: If the override template ID is not found, or no suitable
            template exists for the channel.
    """
    if isinstance(channel, str):
        channel = Channel(channel.lower())

    if template_override is not None:
        tmpl = get_template(template_override)
        if tmpl is None:
            raise ValueError(f"Template '{template_override}' not found in registry")
    else:
        tmpl = select_template(channel, lead_data)

    fmt = _build_format_map(lead_data)
    p_score = _compute_personalization_score(lead_data)

    rendered_subject = _safe_render(tmpl.subject, fmt) if tmpl.subject else None
    rendered_body = _safe_render(tmpl.body, fmt)

    return OutreachDraft(
        subject=rendered_subject,
        body=rendered_body,
        channel=channel,
        template_used=tmpl.id,
        personalization_score=p_score,
    )


# ---------------------------------------------------------------------------
# A/B variant generation
# ---------------------------------------------------------------------------


def generate_ab_variants(
    lead_data: dict[str, Any],
    channel: Channel | str,
) -> tuple[OutreachDraft, OutreachDraft]:
    """Generate two message variants for A/B testing.

    Variant A uses the best-matching template.  Variant B uses the
    second-best template (different temperature or style).

    Args:
        lead_data: Lead attributes.
        channel: Target outreach channel.

    Returns:
        A tuple ``(variant_a, variant_b)`` of ``OutreachDraft`` objects.

    Raises:
        ValueError: If fewer than 2 non-followup templates exist for the
            channel.
    """
    if isinstance(channel, str):
        channel = Channel(channel.lower())

    language = _detect_language(lead_data)
    temperature = _detect_temperature(lead_data)
    is_c_level = bool(lead_data.get("c_level", False))

    candidates = [
        t for t in _REGISTRY.values()
        if t.channel == channel and not t.is_followup
    ]

    if len(candidates) < 2:
        raise ValueError(
            f"Need at least 2 templates for A/B testing on channel "
            f"'{channel.value}', found {len(candidates)}"
        )

    def _score_template(t: Template) -> int:
        s = 0
        if t.language == language:
            s += 4
        if t.lead_temperature == temperature:
            s += 2
        if t.is_c_level == is_c_level:
            s += 1
        return s

    candidates.sort(key=_score_template, reverse=True)

    fmt = _build_format_map(lead_data)
    p_score = _compute_personalization_score(lead_data)

    drafts: list[OutreachDraft] = []
    for tmpl in candidates[:2]:
        rendered_subject = _safe_render(tmpl.subject, fmt) if tmpl.subject else None
        rendered_body = _safe_render(tmpl.body, fmt)
        drafts.append(OutreachDraft(
            subject=rendered_subject,
            body=rendered_body,
            channel=channel,
            template_used=tmpl.id,
            personalization_score=p_score,
        ))

    return (drafts[0], drafts[1])


# ---------------------------------------------------------------------------
# Follow-up sequence
# ---------------------------------------------------------------------------


def get_followup_sequence(
    lead_data: dict[str, Any],
    channel: Channel | str,
    attempt: int,
) -> OutreachDraft:
    """Return the appropriate follow-up message for the given attempt number.

    Args:
        lead_data: Lead attributes.
        channel: Target outreach channel (currently follow-ups are email-only
            but the parameter is accepted for forward compatibility).
        attempt: Follow-up attempt number (1, 2, or 3).

    Returns:
        An ``OutreachDraft`` for the requested follow-up step.

    Raises:
        ValueError: If the attempt number is out of range or no matching
            follow-up template exists.
    """
    if isinstance(channel, str):
        channel = Channel(channel.lower())

    if attempt < 1 or attempt > 3:
        raise ValueError(f"Follow-up attempt must be 1, 2, or 3; got {attempt}")

    template_id = f"followup_{attempt}"
    tmpl = get_template(template_id)

    if tmpl is None:
        raise ValueError(f"Follow-up template '{template_id}' not found in registry")

    fmt = _build_format_map(lead_data)
    p_score = _compute_personalization_score(lead_data)

    rendered_subject = _safe_render(tmpl.subject, fmt) if tmpl.subject else None
    rendered_body = _safe_render(tmpl.body, fmt)

    return OutreachDraft(
        subject=rendered_subject,
        body=rendered_body,
        channel=channel,
        template_used=tmpl.id,
        personalization_score=p_score,
    )


# ---------------------------------------------------------------------------
# Batch composition
# ---------------------------------------------------------------------------


def compose_batch(
    leads_data: list[dict[str, Any]],
    channel: Channel | str,
) -> list[OutreachDraft]:
    """Compose outreach messages for a batch of leads.

    Each lead is processed independently via :func:`compose_message`.

    Args:
        leads_data: List of lead attribute dicts.
        channel: Target outreach channel for all messages.

    Returns:
        A list of ``OutreachDraft`` objects, one per lead.
    """
    if isinstance(channel, str):
        channel = Channel(channel.lower())

    return [compose_message(lead, channel) for lead in leads_data]
