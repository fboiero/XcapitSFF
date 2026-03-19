"""Tests for ticket response templates."""

from xcapitsff.support.templates import (
    get_all_templates,
    get_template,
    get_templates_by_category,
    render_template,
)


def test_get_all_templates():
    templates = get_all_templates()
    assert len(templates) >= 11


def test_get_template_by_id():
    t = get_template("billing_refund_approved")
    assert t is not None
    assert t.category == "billing"


def test_get_template_not_found():
    assert get_template("nonexistent") is None


def test_get_templates_by_category():
    billing = get_templates_by_category("billing")
    assert len(billing) >= 3
    assert all(t.category == "billing" for t in billing)


def test_templates_have_required_fields():
    for t in get_all_templates():
        assert t.template_id
        assert t.category
        assert t.name
        assert t.body
        assert len(t.body) > 20


def test_render_template_basic():
    t = get_template("general_first_response")
    assert t is not None
    subject, body = render_template(t, {"contact_name": "Carlos", "sla_hours": "24"})
    assert "Carlos" in body
    assert "24" in body


def test_render_template_missing_data():
    t = get_template("billing_refund_approved")
    assert t is not None
    subject, body = render_template(t, {})
    assert "[contact_name]" in body  # fallback for missing
    assert "[amount]" in body


def test_all_categories_have_templates():
    categories = {"billing", "technical", "account", "crypto", "general"}
    for cat in categories:
        templates = get_templates_by_category(cat)
        assert len(templates) >= 1, f"No templates for {cat}"


def test_all_templates_in_spanish():
    for t in get_all_templates():
        # Check for Spanish keywords in body
        has_spanish = any(
            word in t.body.lower()
            for word in ["hola", "saludos", "equipo", "tu", "gracias"]
        )
        assert has_spanish, f"Template {t.template_id} doesn't seem to be in Spanish"


def test_security_warning_has_internal_note():
    t = get_template("crypto_security_warning")
    assert t is not None
    assert len(t.internal_note) > 0
    assert "URGENTE" in t.internal_note
