"""Tests for the email integration module.

Covers:
- MockProvider: send, batch send, failure mode, reset, log
- EmailService: outreach, ticket notification (all types), welcome
- Message construction and field population
- HTML template rendering for outreach, ticket, and welcome emails
- Edge cases: unknown message type, missing fields, default values
"""

import pytest

from xcapitsff.integrations.email import (
    EmailConfig,
    EmailMessage,
    EmailResult,
    EmailService,
    MockProvider,
    SMTPProvider,
    render_outreach_html,
    render_ticket_notification_html,
    render_welcome_html,
    _safe_format,
    _TICKET_MESSAGE_TYPES,
)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def mock_provider():
    """A fresh MockProvider instance."""
    return MockProvider()


@pytest.fixture
def email_service(mock_provider):
    """EmailService backed by a MockProvider."""
    return EmailService(mock_provider)


@pytest.fixture
def sample_lead():
    """Sample lead data for outreach tests."""
    return {
        "contact_name": "Maria Garcia",
        "contact_email": "maria@fincorp.com",
        "company_name": "FinCorp SA",
        "sender_name": "Carlos Lopez",
    }


@pytest.fixture
def sample_draft():
    """Sample outreach draft."""
    return {
        "subject": "Oportunidad exclusiva para FinCorp SA",
        "body": (
            "Hola Maria,\n\n"
            "Queria comentarte sobre nuestras soluciones de inversion.\n\n"
            "Saludos cordiales"
        ),
    }


@pytest.fixture
def sample_ticket():
    """Sample ticket data for notification tests."""
    return {
        "id": 42,
        "subject": "Error en la plataforma",
        "status": "open",
        "priority": "high",
        "customer_email": "cliente@empresa.com",
        "customer_name": "Juan Perez",
    }


@pytest.fixture
def sample_customer():
    """Sample customer data for welcome tests."""
    return {
        "contact_name": "Ana Martinez",
        "contact_email": "ana@startup.io",
        "company_name": "Startup IO",
        "plan": "Premium",
    }


# -----------------------------------------------------------------------
# MockProvider tests
# -----------------------------------------------------------------------


class TestMockProvider:
    """Tests for MockProvider send / batch / failure."""

    def test_send_success(self, mock_provider):
        """MockProvider.send records the message and returns success."""
        msg = EmailMessage(to="a@b.com", subject="Test", body_html="<p>Hi</p>")
        result = mock_provider.send(msg)

        assert result.success is True
        assert result.message_id  # non-empty UUID
        assert result.error is None
        assert len(mock_provider.sent_messages) == 1
        assert mock_provider.sent_messages[0].to == "a@b.com"

    def test_send_failure_mode(self, mock_provider):
        """MockProvider returns failure when should_fail is set."""
        mock_provider.should_fail = True
        mock_provider.fail_error = "Connection refused"

        msg = EmailMessage(to="a@b.com", subject="Test", body_html="<p>Hi</p>")
        result = mock_provider.send(msg)

        assert result.success is False
        assert result.error == "Connection refused"
        # The message should NOT be stored in sent_messages on failure
        assert len(mock_provider.sent_messages) == 0
        # But the result IS stored in results
        assert len(mock_provider.results) == 1

    def test_batch_send(self, mock_provider):
        """send_batch sends all messages and returns matching results."""
        messages = [
            EmailMessage(to=f"user{i}@test.com", subject=f"Msg {i}", body_html=f"<p>{i}</p>")
            for i in range(5)
        ]
        results = mock_provider.send_batch(messages)

        assert len(results) == 5
        assert all(r.success for r in results)
        assert len(mock_provider.sent_messages) == 5

    def test_reset_clears_state(self, mock_provider):
        """MockProvider.reset clears messages and results."""
        msg = EmailMessage(to="a@b.com", subject="Test", body_html="<p>Hi</p>")
        mock_provider.send(msg)
        mock_provider.should_fail = True

        mock_provider.reset()

        assert len(mock_provider.sent_messages) == 0
        assert len(mock_provider.results) == 0
        assert mock_provider.should_fail is False

    def test_results_log_accumulates(self, mock_provider):
        """Each send appends to the results list."""
        for i in range(3):
            msg = EmailMessage(to=f"u{i}@t.com", subject="S", body_html="<p>B</p>")
            mock_provider.send(msg)

        assert len(mock_provider.results) == 3
        assert all(r.success for r in mock_provider.results)


# -----------------------------------------------------------------------
# EmailService outreach tests
# -----------------------------------------------------------------------


class TestEmailServiceOutreach:
    """Tests for EmailService.send_outreach."""

    def test_send_outreach_success(self, email_service, mock_provider, sample_lead, sample_draft):
        """send_outreach delivers an email and returns success."""
        result = email_service.send_outreach(sample_lead, sample_draft)

        assert result.success is True
        assert len(mock_provider.sent_messages) == 1

        sent = mock_provider.sent_messages[0]
        assert sent.to == "maria@fincorp.com"
        assert sent.subject == "Oportunidad exclusiva para FinCorp SA"

    def test_outreach_html_contains_lead_name(self, email_service, mock_provider, sample_lead, sample_draft):
        """Outreach HTML body includes the contact name."""
        email_service.send_outreach(sample_lead, sample_draft)
        sent = mock_provider.sent_messages[0]

        assert "Maria Garcia" in sent.body_html

    def test_outreach_plain_text_body(self, email_service, mock_provider, sample_lead, sample_draft):
        """Outreach email includes a plain-text body."""
        email_service.send_outreach(sample_lead, sample_draft)
        sent = mock_provider.sent_messages[0]

        assert "soluciones de inversion" in sent.body_text

    def test_outreach_logs_result(self, email_service, sample_lead, sample_draft):
        """send_outreach appends to the sent log."""
        email_service.send_outreach(sample_lead, sample_draft)
        log = email_service.get_sent_log()

        assert len(log) == 1
        assert log[0].success is True


# -----------------------------------------------------------------------
# EmailService ticket notification tests
# -----------------------------------------------------------------------


class TestEmailServiceTicketNotification:
    """Tests for EmailService.send_ticket_notification."""

    def test_ticket_created_notification(self, email_service, mock_provider, sample_ticket):
        """Ticket 'created' notification sends correctly."""
        result = email_service.send_ticket_notification(sample_ticket, "created")

        assert result.success is True
        sent = mock_provider.sent_messages[0]
        assert sent.to == "cliente@empresa.com"
        assert "#42" in sent.subject
        assert "creado" in sent.subject

    def test_ticket_resolved_notification(self, email_service, mock_provider, sample_ticket):
        """Ticket 'resolved' notification includes resolution copy."""
        result = email_service.send_ticket_notification(sample_ticket, "resolved")

        assert result.success is True
        sent = mock_provider.sent_messages[0]
        assert "resuelto" in sent.subject

    def test_ticket_escalated_notification(self, email_service, mock_provider, sample_ticket):
        """Ticket 'escalated' notification sends correctly."""
        result = email_service.send_ticket_notification(sample_ticket, "escalated")

        assert result.success is True
        sent = mock_provider.sent_messages[0]
        assert "escalado" in sent.subject

    def test_unknown_message_type_returns_error(self, email_service, sample_ticket):
        """Unknown message_type returns a failed EmailResult."""
        result = email_service.send_ticket_notification(sample_ticket, "nonexistent")

        assert result.success is False
        assert "Unknown message_type" in result.error

    def test_ticket_notification_html_has_ticket_id(self, email_service, mock_provider, sample_ticket):
        """Ticket notification HTML includes the ticket ID."""
        email_service.send_ticket_notification(sample_ticket, "created")
        sent = mock_provider.sent_messages[0]

        assert "#42" in sent.body_html

    def test_ticket_notification_plain_text(self, email_service, mock_provider, sample_ticket):
        """Ticket notification includes a plain-text fallback."""
        email_service.send_ticket_notification(sample_ticket, "updated")
        sent = mock_provider.sent_messages[0]

        assert "Ticket: #42" in sent.body_text
        assert "Estado: open" in sent.body_text


# -----------------------------------------------------------------------
# EmailService welcome tests
# -----------------------------------------------------------------------


class TestEmailServiceWelcome:
    """Tests for EmailService.send_welcome."""

    def test_welcome_email_success(self, email_service, mock_provider, sample_customer):
        """Welcome email is sent successfully."""
        result = email_service.send_welcome(sample_customer)

        assert result.success is True
        sent = mock_provider.sent_messages[0]
        assert sent.to == "ana@startup.io"
        assert "Bienvenido" in sent.subject
        assert "Ana Martinez" in sent.subject

    def test_welcome_html_contains_plan(self, email_service, mock_provider, sample_customer):
        """Welcome HTML includes the customer plan name."""
        email_service.send_welcome(sample_customer)
        sent = mock_provider.sent_messages[0]

        assert "Premium" in sent.body_html

    def test_welcome_html_contains_company(self, email_service, mock_provider, sample_customer):
        """Welcome HTML includes the company name."""
        email_service.send_welcome(sample_customer)
        sent = mock_provider.sent_messages[0]

        assert "Startup IO" in sent.body_html

    def test_welcome_default_plan(self, email_service, mock_provider):
        """Welcome email uses 'Estandar' as the default plan."""
        customer = {
            "contact_name": "Test User",
            "contact_email": "test@example.com",
            "company_name": "Test Co",
        }
        email_service.send_welcome(customer)
        sent = mock_provider.sent_messages[0]

        assert "Estandar" in sent.body_html


# -----------------------------------------------------------------------
# Message construction tests
# -----------------------------------------------------------------------


class TestMessageConstruction:
    """Tests for EmailMessage dataclass defaults and fields."""

    def test_message_defaults(self):
        """EmailMessage has sensible defaults for optional fields."""
        msg = EmailMessage(to="a@b.com", subject="S", body_html="<p>B</p>")

        assert msg.body_text == ""
        assert msg.cc == []
        assert msg.bcc == []
        assert msg.reply_to is None
        assert msg.attachments == []

    def test_message_with_all_fields(self):
        """EmailMessage can be fully populated."""
        msg = EmailMessage(
            to="a@b.com",
            subject="Full",
            body_html="<p>HTML</p>",
            body_text="Plain",
            cc=["cc@b.com"],
            bcc=["bcc@b.com"],
            reply_to="reply@b.com",
            attachments=[("file.txt", b"data")],
        )

        assert msg.cc == ["cc@b.com"]
        assert msg.bcc == ["bcc@b.com"]
        assert msg.reply_to == "reply@b.com"
        assert len(msg.attachments) == 1

    def test_email_result_defaults(self):
        """EmailResult has sensible defaults."""
        result = EmailResult(success=True, message_id="abc-123")

        assert result.error is None
        assert result.timestamp is not None


# -----------------------------------------------------------------------
# HTML template rendering tests
# -----------------------------------------------------------------------


class TestHTMLTemplateRendering:
    """Tests for standalone template rendering functions."""

    def test_render_outreach_html_structure(self):
        """Outreach HTML contains the expected structural elements."""
        html = render_outreach_html("Juan", "<p>Contenido</p>", "Ana")

        assert "<!DOCTYPE html>" in html
        assert "Juan" in html
        assert "Contenido" in html
        assert "Ana" in html
        assert "Xcapit" in html

    def test_render_ticket_notification_html(self):
        """Ticket notification HTML contains ticket details."""
        html = render_ticket_notification_html(
            contact_name="Cliente",
            title="Ticket creado",
            message="Hemos recibido tu solicitud.",
            ticket_id=99,
            subject="Bug report",
            status="open",
            priority="high",
        )

        assert "#99" in html
        assert "Bug report" in html
        assert "open" in html
        assert "high" in html
        assert "Soporte" in html

    def test_render_welcome_html(self):
        """Welcome HTML contains customer and plan information."""
        html = render_welcome_html("Pedro", "Acme Corp", "Enterprise")

        assert "Pedro" in html
        assert "Acme Corp" in html
        assert "Enterprise" in html
        assert "Bienvenido" in html

    def test_safe_format_handles_missing_keys(self):
        """_safe_format does not raise on missing keys."""
        result = _safe_format("Hello {name}, your {missing} is ready", {"name": "Test"})

        assert "Test" in result


# -----------------------------------------------------------------------
# EmailConfig and SMTPProvider instantiation
# -----------------------------------------------------------------------


class TestEmailConfig:
    """Tests for EmailConfig dataclass."""

    def test_config_creation(self):
        """EmailConfig stores all fields correctly."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_email="noreply@example.com",
            from_name="My App",
            use_tls=True,
        )

        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.from_name == "My App"
        assert config.use_tls is True

    def test_config_default_values(self):
        """EmailConfig has sensible defaults."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_email="noreply@example.com",
        )

        assert config.from_name == "Xcapit"
        assert config.use_tls is True

    def test_smtp_provider_instantiation(self):
        """SMTPProvider can be created with a config."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass",
            from_email="noreply@example.com",
        )
        provider = SMTPProvider(config)

        assert provider.config is config


# -----------------------------------------------------------------------
# Sent log tests
# -----------------------------------------------------------------------


class TestSentLog:
    """Tests for EmailService.get_sent_log."""

    def test_log_is_empty_initially(self, email_service):
        """Sent log starts empty."""
        assert email_service.get_sent_log() == []

    def test_log_accumulates_across_methods(self, email_service, sample_lead, sample_draft, sample_ticket, sample_customer):
        """Sent log records results from all send methods."""
        email_service.send_outreach(sample_lead, sample_draft)
        email_service.send_ticket_notification(sample_ticket, "created")
        email_service.send_welcome(sample_customer)

        log = email_service.get_sent_log()
        assert len(log) == 3
        assert all(r.success for r in log)

    def test_log_returns_copy(self, email_service, sample_lead, sample_draft):
        """get_sent_log returns a copy, not a reference."""
        email_service.send_outreach(sample_lead, sample_draft)
        log1 = email_service.get_sent_log()
        log2 = email_service.get_sent_log()

        assert log1 is not log2
        assert log1[0].message_id == log2[0].message_id
