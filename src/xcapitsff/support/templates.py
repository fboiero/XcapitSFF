"""Ticket response templates — pre-built responses for common scenarios.

Templates are used by the support agent and human operators to quickly
respond to common ticket types with consistent, professional messaging.
"""

from dataclasses import dataclass, field
from enum import Enum


class TemplateLanguage(str, Enum):
    ES_LATAM = "es_latam"
    ES_IBERIA = "es_iberia"


@dataclass(frozen=True)
class TicketTemplate:
    template_id: str
    category: str
    name: str
    language: TemplateLanguage
    subject: str
    body: str
    internal_note: str = ""
    tags: list[str] = field(default_factory=list)


# Pre-built templates for common scenarios
TEMPLATES: list[TicketTemplate] = [
    # === BILLING ===
    TicketTemplate(
        template_id="billing_refund_approved",
        category="billing",
        name="Reembolso aprobado",
        language=TemplateLanguage.ES_LATAM,
        subject="Tu reembolso ha sido procesado",
        body=(
            "Hola {contact_name},\n\n"
            "Te confirmamos que tu solicitud de reembolso ha sido procesada exitosamente. "
            "El monto de {amount} será acreditado en tu cuenta dentro de los próximos 5-10 días hábiles.\n\n"
            "Si tenés alguna consulta adicional, no dudes en escribirnos.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        internal_note="Verificar que el reembolso fue procesado en el sistema antes de enviar.",
        tags=["billing", "refund"],
    ),
    TicketTemplate(
        template_id="billing_plan_change",
        category="billing",
        name="Cambio de plan confirmado",
        language=TemplateLanguage.ES_LATAM,
        subject="Tu cambio de plan fue procesado",
        body=(
            "Hola {contact_name},\n\n"
            "Te confirmamos que tu plan fue actualizado a {new_plan}. "
            "Los cambios se reflejarán en tu próxima facturación.\n\n"
            "Podés ver los detalles de tu nuevo plan en la sección de configuración de tu cuenta.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        tags=["billing", "plan"],
    ),
    TicketTemplate(
        template_id="billing_invoice_sent",
        category="billing",
        name="Factura enviada",
        language=TemplateLanguage.ES_LATAM,
        subject="Tu factura está disponible",
        body=(
            "Hola {contact_name},\n\n"
            "Tu factura del período {period} ya está disponible. "
            "Podés descargarla desde tu panel de cuenta.\n\n"
            "Si tenés dudas sobre algún cargo, contactanos.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        tags=["billing", "invoice"],
    ),

    # === TECHNICAL ===
    TicketTemplate(
        template_id="tech_bug_acknowledged",
        category="technical",
        name="Bug reconocido",
        language=TemplateLanguage.ES_LATAM,
        subject="Estamos investigando tu reporte",
        body=(
            "Hola {contact_name},\n\n"
            "Gracias por reportar este problema. Nuestro equipo técnico ya está investigando "
            "la situación que describiste.\n\n"
            "Te mantendremos informado sobre el progreso. Si podés, compartinos:\n"
            "- ¿En qué dispositivo/navegador ocurre?\n"
            "- ¿Podés reproducir el error consistentemente?\n\n"
            "Saludos,\nEquipo Técnico Xcapit"
        ),
        internal_note="Crear ticket en el sistema de bugs con los pasos de reproducción.",
        tags=["technical", "bug"],
    ),
    TicketTemplate(
        template_id="tech_resolved",
        category="technical",
        name="Problema técnico resuelto",
        language=TemplateLanguage.ES_LATAM,
        subject="Tu problema fue solucionado",
        body=(
            "Hola {contact_name},\n\n"
            "Te informamos que el problema que reportaste fue solucionado. "
            "Por favor verificá que todo funcione correctamente de tu lado.\n\n"
            "Si el problema persiste, respondé a este mensaje y lo revisamos nuevamente.\n\n"
            "Saludos,\nEquipo Técnico Xcapit"
        ),
        tags=["technical", "resolved"],
    ),

    # === ACCOUNT ===
    TicketTemplate(
        template_id="account_password_reset",
        category="account",
        name="Reset de contraseña",
        language=TemplateLanguage.ES_LATAM,
        subject="Instrucciones para restablecer tu contraseña",
        body=(
            "Hola {contact_name},\n\n"
            "Para restablecer tu contraseña, seguí estos pasos:\n"
            "1. Ingresá a la página de login\n"
            "2. Hacé clic en '¿Olvidaste tu contraseña?'\n"
            "3. Ingresá tu email: {contact_email}\n"
            "4. Revisá tu bandeja de entrada (y spam) para el link de reset\n\n"
            "Si no recibís el email en 5 minutos, contactanos nuevamente.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        tags=["account", "password"],
    ),
    TicketTemplate(
        template_id="account_kyc_pending",
        category="account",
        name="KYC en revisión",
        language=TemplateLanguage.ES_LATAM,
        subject="Tu verificación está en proceso",
        body=(
            "Hola {contact_name},\n\n"
            "Tu documentación de verificación (KYC) está siendo revisada por nuestro equipo. "
            "Este proceso puede tomar hasta 48 horas hábiles.\n\n"
            "Te notificaremos por email cuando la verificación esté completa.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        tags=["account", "kyc"],
    ),

    # === CRYPTO ===
    TicketTemplate(
        template_id="crypto_tx_pending",
        category="crypto",
        name="Transacción pendiente",
        language=TemplateLanguage.ES_LATAM,
        subject="Tu transacción está siendo procesada",
        body=(
            "Hola {contact_name},\n\n"
            "Tu transacción está siendo procesada en la blockchain. "
            "Los tiempos de confirmación dependen de la congestión de la red.\n\n"
            "Podés verificar el estado con tu hash de transacción: {tx_hash}\n\n"
            "Si la transacción no se confirma en {expected_time}, contactanos.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        internal_note="Verificar el hash en el explorer de la red correspondiente.",
        tags=["crypto", "transaction"],
    ),
    TicketTemplate(
        template_id="crypto_security_warning",
        category="crypto",
        name="Alerta de seguridad",
        language=TemplateLanguage.ES_LATAM,
        subject="Alerta de seguridad en tu cuenta",
        body=(
            "Hola {contact_name},\n\n"
            "Detectamos actividad inusual en tu cuenta. Por seguridad, "
            "te recomendamos:\n\n"
            "1. Cambiar tu contraseña inmediatamente\n"
            "2. Activar autenticación de dos factores (2FA)\n"
            "3. Revisar los dispositivos conectados a tu cuenta\n"
            "4. Verificar tus últimas transacciones\n\n"
            "Si no reconocés alguna actividad, contactanos urgentemente.\n\n"
            "Saludos,\nEquipo de Seguridad Xcapit"
        ),
        internal_note="URGENTE: Verificar con equipo de seguridad antes de enviar. Congelar cuenta si es necesario.",
        tags=["crypto", "security", "urgent"],
    ),

    # === GENERAL ===
    TicketTemplate(
        template_id="general_first_response",
        category="general",
        name="Primera respuesta",
        language=TemplateLanguage.ES_LATAM,
        subject="Recibimos tu consulta",
        body=(
            "Hola {contact_name},\n\n"
            "Gracias por contactarnos. Recibimos tu consulta y estamos "
            "trabajando para darte una respuesta lo antes posible.\n\n"
            "Nuestro tiempo de respuesta estimado es de {sla_hours} horas.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        tags=["general", "first_response"],
    ),
    TicketTemplate(
        template_id="general_escalation",
        category="general",
        name="Escalación",
        language=TemplateLanguage.ES_LATAM,
        subject="Tu caso fue escalado a un especialista",
        body=(
            "Hola {contact_name},\n\n"
            "Tu caso requiere atención especializada y fue escalado a nuestro "
            "equipo senior. Un especialista se pondrá en contacto con vos "
            "dentro de las próximas {escalation_hours} horas.\n\n"
            "Disculpá las molestias y gracias por tu paciencia.\n\n"
            "Saludos,\nEquipo de Soporte Xcapit"
        ),
        tags=["general", "escalation"],
    ),
]


def get_template(template_id: str) -> TicketTemplate | None:
    """Get a template by ID."""
    for t in TEMPLATES:
        if t.template_id == template_id:
            return t
    return None


def get_templates_by_category(category: str) -> list[TicketTemplate]:
    """Get all templates for a category."""
    return [t for t in TEMPLATES if t.category == category]


def get_all_templates() -> list[TicketTemplate]:
    """Get all available templates."""
    return list(TEMPLATES)


def render_template(template: TicketTemplate, data: dict) -> tuple[str, str]:
    """Render a template with data. Returns (subject, body)."""
    safe_data = {}
    for key in ["contact_name", "contact_email", "amount", "new_plan", "period",
                 "tx_hash", "expected_time", "sla_hours", "escalation_hours"]:
        safe_data[key] = data.get(key, f"[{key}]")

    subject = template.subject.format_map(safe_data)
    body = template.body.format_map(safe_data)
    return subject, body
