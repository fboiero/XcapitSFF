"""Email integration module — send outreach, support, and welcome communications.

Provides a provider-based architecture for sending emails:

- ``SMTPProvider``: real SMTP delivery via :mod:`smtplib`.
- ``MockProvider``: in-memory mock that stores sent messages (for testing).
- ``EmailService``: high-level service that composes and sends outreach,
  ticket-notification, and welcome emails using HTML templates with simple
  string formatting (no Jinja2 dependency).

Typical usage::

    config = EmailConfig(smtp_host="smtp.example.com", ...)
    provider = SMTPProvider(config)
    service = EmailService(provider)
    result = service.send_welcome(customer_data)
"""

from __future__ import annotations

import logging
import smtplib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class EmailConfig:
    """SMTP connection configuration.

    Attributes:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (587 for TLS, 465 for SSL, 25 for plain).
        username: SMTP authentication username.
        password: SMTP authentication password.
        from_email: Sender email address.
        from_name: Sender display name.
        use_tls: Whether to use STARTTLS (default ``True``).
    """

    smtp_host: str
    smtp_port: int
    username: str
    password: str
    from_email: str
    from_name: str = "Xcapit"
    use_tls: bool = True


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


@dataclass
class EmailMessage:
    """An email message ready for delivery.

    Attributes:
        to: Primary recipient email address.
        subject: Email subject line.
        body_html: HTML body content.
        body_text: Plain-text fallback body.
        cc: Carbon-copy recipient addresses.
        bcc: Blind carbon-copy recipient addresses.
        reply_to: Reply-to address.
        attachments: List of ``(filename, content_bytes)`` tuples.
    """

    to: str
    subject: str
    body_html: str
    body_text: str = ""
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    reply_to: str | None = None
    attachments: list[tuple[str, bytes]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class EmailResult:
    """Outcome of a single email send attempt.

    Attributes:
        success: Whether the send succeeded.
        message_id: Unique identifier for the sent message.
        error: Error description if the send failed.
        timestamp: When the attempt was made.
    """

    success: bool
    message_id: str
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Provider protocol / ABC
# ---------------------------------------------------------------------------


class EmailProvider(ABC):
    """Abstract base for email delivery backends."""

    @abstractmethod
    def send(self, message: EmailMessage) -> EmailResult:
        """Send a single email message.

        Args:
            message: The message to send.

        Returns:
            An ``EmailResult`` indicating success or failure.
        """

    def send_batch(self, messages: list[EmailMessage]) -> list[EmailResult]:
        """Send multiple messages sequentially.

        Subclasses may override for bulk-optimised delivery.

        Args:
            messages: The messages to send.

        Returns:
            A list of ``EmailResult`` objects, one per message.
        """
        return [self.send(m) for m in messages]


# ---------------------------------------------------------------------------
# SMTP provider (real)
# ---------------------------------------------------------------------------


class SMTPProvider(EmailProvider):
    """Real SMTP delivery using :mod:`smtplib`."""

    def __init__(self, config: EmailConfig) -> None:
        self.config = config

    def _build_mime(self, message: EmailMessage) -> MIMEMultipart:
        """Build a ``MIMEMultipart`` from an ``EmailMessage``."""
        mime = MIMEMultipart("alternative")
        mime["From"] = f"{self.config.from_name} <{self.config.from_email}>"
        mime["To"] = message.to
        mime["Subject"] = message.subject

        if message.cc:
            mime["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            mime["Reply-To"] = message.reply_to

        # Attach plain text first, then HTML (clients prefer the last part)
        if message.body_text:
            mime.attach(MIMEText(message.body_text, "plain", "utf-8"))
        mime.attach(MIMEText(message.body_html, "html", "utf-8"))

        return mime

    def send(self, message: EmailMessage) -> EmailResult:
        """Send a single email via SMTP."""
        message_id = str(uuid.uuid4())
        try:
            mime = self._build_mime(message)
            mime["Message-ID"] = f"<{message_id}@{self.config.smtp_host}>"

            all_recipients = [message.to] + message.cc + message.bcc

            if self.config.use_tls:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.starttls()
                    server.login(self.config.username, self.config.password)
                    server.sendmail(self.config.from_email, all_recipients, mime.as_string())
            else:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.login(self.config.username, self.config.password)
                    server.sendmail(self.config.from_email, all_recipients, mime.as_string())

            logger.info("Email sent successfully: %s -> %s", message_id, message.to)
            return EmailResult(success=True, message_id=message_id)

        except Exception as exc:
            logger.error("Email send failed: %s -> %s: %s", message_id, message.to, exc)
            return EmailResult(success=False, message_id=message_id, error=str(exc))


# ---------------------------------------------------------------------------
# Mock provider (testing)
# ---------------------------------------------------------------------------


class MockProvider(EmailProvider):
    """In-memory mock provider that stores sent messages for testing."""

    def __init__(self) -> None:
        self.sent_messages: list[EmailMessage] = []
        self.results: list[EmailResult] = []
        self.should_fail: bool = False
        self.fail_error: str = "Mock failure"

    def send(self, message: EmailMessage) -> EmailResult:
        """Record the message and return a result."""
        message_id = str(uuid.uuid4())

        if self.should_fail:
            result = EmailResult(
                success=False, message_id=message_id, error=self.fail_error
            )
            self.results.append(result)
            return result

        self.sent_messages.append(message)
        result = EmailResult(success=True, message_id=message_id)
        self.results.append(result)
        return result

    def reset(self) -> None:
        """Clear all stored messages and results."""
        self.sent_messages.clear()
        self.results.clear()
        self.should_fail = False


# ---------------------------------------------------------------------------
# HTML templates (simple string formatting)
# ---------------------------------------------------------------------------

OUTREACH_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #1a73e8; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="margin: 0; font-size: 22px;">Xcapit</h1>
    </div>
    <div style="padding: 20px; border: 1px solid #e0e0e0; border-top: none;">
      <p>Hola {contact_name},</p>
      {body}
      <p style="margin-top: 20px;">Saludos cordiales,<br><strong>{sender_name}</strong></p>
    </div>
    <div style="padding: 10px 20px; font-size: 12px; color: #888; text-align: center;">
      Xcapit &mdash; Soluciones de inversi&oacute;n automatizada
    </div>
  </div>
</body>
</html>"""

TICKET_NOTIFICATION_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #34a853; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="margin: 0; font-size: 22px;">Xcapit Soporte</h1>
    </div>
    <div style="padding: 20px; border: 1px solid #e0e0e0; border-top: none;">
      <h2 style="color: #34a853;">{title}</h2>
      <p>Hola {contact_name},</p>
      <p>{message}</p>
      <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 15px 0;">
        <strong>Ticket:</strong> #{ticket_id}<br>
        <strong>Asunto:</strong> {subject}<br>
        <strong>Estado:</strong> {status}<br>
        <strong>Prioridad:</strong> {priority}
      </div>
      <p>{footer}</p>
    </div>
    <div style="padding: 10px 20px; font-size: 12px; color: #888; text-align: center;">
      Xcapit Soporte &mdash; Estamos para ayudarte
    </div>
  </div>
</body>
</html>"""

WELCOME_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
  <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: #1a73e8; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
      <h1 style="margin: 0; font-size: 22px;">Bienvenido a Xcapit</h1>
    </div>
    <div style="padding: 20px; border: 1px solid #e0e0e0; border-top: none;">
      <h2>Hola {contact_name}, bienvenido!</h2>
      <p>Nos alegra mucho que {company_name} se haya unido a la familia Xcapit.</p>
      <p>Con tu plan <strong>{plan}</strong>, tienes acceso a:</p>
      <ul>
        <li>Gestion automatizada de portafolios</li>
        <li>Estrategias de rendimiento DeFi</li>
        <li>Soporte dedicado de nuestro equipo</li>
        <li>Reportes y analiticas en tiempo real</li>
      </ul>
      <p>Nuestro equipo esta disponible para ayudarte a configurar tu cuenta y
         resolver cualquier duda que tengas.</p>
      <div style="text-align: center; margin: 25px 0;">
        <a href="https://app.xcapit.com" style="background: #1a73e8; color: white; padding: 12px 30px; text-decoration: none; border-radius: 4px; font-weight: bold;">
          Acceder a tu cuenta
        </a>
      </div>
      <p>Saludos cordiales,<br><strong>El equipo de Xcapit</strong></p>
    </div>
    <div style="padding: 10px 20px; font-size: 12px; color: #888; text-align: center;">
      Xcapit &mdash; Soluciones de inversi&oacute;n automatizada
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Template rendering helpers
# ---------------------------------------------------------------------------


def _safe_format(template: str, data: dict[str, Any]) -> str:
    """Render a template string with ``str.format_map``, falling back on errors."""
    try:
        return template.format_map(data)
    except (KeyError, ValueError, IndexError):
        # Best-effort: replace known keys, leave unknown ones as-is
        result = template
        for key, value in data.items():
            result = result.replace("{" + key + "}", str(value))
        return result


def render_outreach_html(
    contact_name: str,
    body: str,
    sender_name: str = "El equipo de Xcapit",
) -> str:
    """Render the outreach email HTML template."""
    return _safe_format(OUTREACH_HTML_TEMPLATE, {
        "contact_name": contact_name,
        "body": body,
        "sender_name": sender_name,
    })


def render_ticket_notification_html(
    contact_name: str,
    title: str,
    message: str,
    ticket_id: str | int,
    subject: str,
    status: str,
    priority: str,
    footer: str = "Si tienes alguna pregunta, no dudes en responder a este correo.",
) -> str:
    """Render the ticket notification email HTML template."""
    return _safe_format(TICKET_NOTIFICATION_HTML_TEMPLATE, {
        "contact_name": contact_name,
        "title": title,
        "message": message,
        "ticket_id": str(ticket_id),
        "subject": subject,
        "status": status,
        "priority": priority,
        "footer": footer,
    })


def render_welcome_html(
    contact_name: str,
    company_name: str,
    plan: str = "Estandar",
) -> str:
    """Render the welcome email HTML template."""
    return _safe_format(WELCOME_HTML_TEMPLATE, {
        "contact_name": contact_name,
        "company_name": company_name,
        "plan": plan,
    })


# ---------------------------------------------------------------------------
# Ticket notification message types
# ---------------------------------------------------------------------------

_TICKET_MESSAGE_TYPES: dict[str, dict[str, str]] = {
    "created": {
        "subject": "Ticket #{ticket_id} creado: {ticket_subject}",
        "title": "Tu ticket ha sido creado",
        "message": "Hemos recibido tu solicitud y nuestro equipo la esta revisando.",
        "footer": "Te notificaremos cuando haya una actualizacion.",
    },
    "updated": {
        "subject": "Actualizacion del Ticket #{ticket_id}: {ticket_subject}",
        "title": "Tu ticket ha sido actualizado",
        "message": "Hay una nueva actualizacion en tu ticket de soporte.",
        "footer": "Revisa los detalles y respondenos si necesitas mas ayuda.",
    },
    "resolved": {
        "subject": "Ticket #{ticket_id} resuelto: {ticket_subject}",
        "title": "Tu ticket ha sido resuelto",
        "message": "Nos complace informarte que tu ticket ha sido resuelto.",
        "footer": "Si el problema persiste, puedes reabrir el ticket respondiendo a este correo.",
    },
    "escalated": {
        "subject": "Ticket #{ticket_id} escalado: {ticket_subject}",
        "title": "Tu ticket ha sido escalado",
        "message": "Tu ticket ha sido escalado a un especialista para una atencion mas rapida.",
        "footer": "Un miembro senior de nuestro equipo se comunicara contigo pronto.",
    },
}


# ---------------------------------------------------------------------------
# EmailService — high-level orchestration
# ---------------------------------------------------------------------------


class EmailService:
    """High-level email service that composes and sends domain-specific emails.

    Uses an ``EmailProvider`` for actual delivery and maintains an internal
    log of all send results.

    Args:
        provider: The email provider backend to use for delivery.
    """

    def __init__(self, provider: EmailProvider) -> None:
        self.provider = provider
        self._sent_log: list[EmailResult] = []

    # -- Outreach -----------------------------------------------------------

    def send_outreach(
        self,
        lead_data: dict[str, Any],
        draft: dict[str, Any],
    ) -> EmailResult:
        """Send an outreach email to a lead.

        Args:
            lead_data: Dict with at least ``contact_email``, ``contact_name``,
                ``company_name``.
            draft: Dict with ``subject`` and ``body`` (plain-text body from the
                outreach template engine).

        Returns:
            An ``EmailResult`` indicating success or failure.
        """
        contact_name = lead_data.get("contact_name", "estimado/a")
        contact_email = lead_data.get("contact_email", "")
        sender_name = lead_data.get("sender_name", "El equipo de Xcapit")

        subject = draft.get("subject", "Informacion de Xcapit")
        body_text = draft.get("body", "")

        # Wrap body paragraphs in <p> tags for HTML
        body_paragraphs = "".join(
            f"<p>{p.strip()}</p>" for p in body_text.split("\n\n") if p.strip()
        )

        body_html = render_outreach_html(
            contact_name=contact_name,
            body=body_paragraphs,
            sender_name=sender_name,
        )

        message = EmailMessage(
            to=contact_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )

        result = self.provider.send(message)
        self._sent_log.append(result)
        return result

    # -- Ticket notification ------------------------------------------------

    def send_ticket_notification(
        self,
        ticket: dict[str, Any],
        message_type: str = "created",
    ) -> EmailResult:
        """Send a ticket lifecycle notification.

        Args:
            ticket: Dict with ``id``, ``subject``, ``status``, ``priority``,
                ``customer_email``, ``customer_name``.
            message_type: One of ``"created"``, ``"updated"``, ``"resolved"``,
                ``"escalated"``.

        Returns:
            An ``EmailResult``.
        """
        type_config = _TICKET_MESSAGE_TYPES.get(message_type)
        if type_config is None:
            return EmailResult(
                success=False,
                message_id="",
                error=f"Unknown message_type: {message_type}",
            )

        ticket_id = ticket.get("id", "?")
        ticket_subject = ticket.get("subject", "Sin asunto")
        customer_email = ticket.get("customer_email", "")
        customer_name = ticket.get("customer_name", "Cliente")
        status = ticket.get("status", "open")
        priority = ticket.get("priority", "medium")

        subject = _safe_format(type_config["subject"], {
            "ticket_id": str(ticket_id),
            "ticket_subject": ticket_subject,
        })

        body_html = render_ticket_notification_html(
            contact_name=customer_name,
            title=type_config["title"],
            message=type_config["message"],
            ticket_id=ticket_id,
            subject=ticket_subject,
            status=status,
            priority=priority,
            footer=type_config["footer"],
        )

        body_text = (
            f"{type_config['title']}\n\n"
            f"{type_config['message']}\n\n"
            f"Ticket: #{ticket_id}\n"
            f"Asunto: {ticket_subject}\n"
            f"Estado: {status}\n"
            f"Prioridad: {priority}\n\n"
            f"{type_config['footer']}"
        )

        message = EmailMessage(
            to=customer_email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )

        result = self.provider.send(message)
        self._sent_log.append(result)
        return result

    # -- Welcome email ------------------------------------------------------

    def send_welcome(self, customer: dict[str, Any]) -> EmailResult:
        """Send a welcome email to a newly registered customer.

        Args:
            customer: Dict with ``contact_email``, ``contact_name``,
                ``company_name``, and optionally ``plan``.

        Returns:
            An ``EmailResult``.
        """
        contact_name = customer.get("contact_name", "Cliente")
        contact_email = customer.get("contact_email", "")
        company_name = customer.get("company_name", "tu empresa")
        plan = customer.get("plan", "Estandar")

        body_html = render_welcome_html(
            contact_name=contact_name,
            company_name=company_name,
            plan=plan,
        )

        body_text = (
            f"Hola {contact_name}, bienvenido!\n\n"
            f"Nos alegra mucho que {company_name} se haya unido a la familia Xcapit.\n\n"
            f"Con tu plan {plan}, tienes acceso a:\n"
            "- Gestion automatizada de portafolios\n"
            "- Estrategias de rendimiento DeFi\n"
            "- Soporte dedicado de nuestro equipo\n"
            "- Reportes y analiticas en tiempo real\n\n"
            "Saludos cordiales,\nEl equipo de Xcapit"
        )

        message = EmailMessage(
            to=contact_email,
            subject=f"Bienvenido a Xcapit, {contact_name}!",
            body_html=body_html,
            body_text=body_text,
        )

        result = self.provider.send(message)
        self._sent_log.append(result)
        return result

    # -- Log ----------------------------------------------------------------

    def get_sent_log(self) -> list[EmailResult]:
        """Return the log of all email send results."""
        return list(self._sent_log)
