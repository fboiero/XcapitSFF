"""Tests for Email Template Manager."""

import pytest

from xcapitsff.core.email_templates import (
    EmailTemplate,
    EmailTemplateManager,
    TemplateCategory,
    _extract_variables,
    _render_text,
    _strip_html,
)


@pytest.fixture
def manager():
    return EmailTemplateManager()


# ------------------------------------------------------------------
# Variable extraction
# ------------------------------------------------------------------


def test_extract_variables_from_subject_and_body():
    variables = _extract_variables(
        "Hola {{nombre}}", "<p>{{empresa}} en {{region}}</p>", ""
    )
    assert variables == ["empresa", "nombre", "region"]


def test_extract_variables_deduplicates():
    variables = _extract_variables(
        "{{nombre}}", "<p>{{nombre}} {{nombre}}</p>", "{{nombre}}"
    )
    assert variables == ["nombre"]


def test_extract_no_variables():
    variables = _extract_variables("Asunto simple", "<p>Cuerpo sin variables</p>", "")
    assert variables == []


# ------------------------------------------------------------------
# Rendering
# ------------------------------------------------------------------


def test_render_text_replaces_variables():
    result = _render_text("Hola {{nombre}}, de {{empresa}}", {"nombre": "Ana", "empresa": "Xcapit"})
    assert result == "Hola Ana, de Xcapit"


def test_render_text_preserves_unknown_variables():
    result = _render_text("Hola {{nombre}}", {})
    assert result == "Hola {{nombre}}"


def test_strip_html():
    assert _strip_html("<p>Hola <strong>mundo</strong></p>") == "Hola mundo"


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


def test_create_template(manager):
    t = manager.create(
        tenant_id="t1",
        name="Test",
        category=TemplateCategory.OUTREACH,
        subject="Hola {{nombre}}",
        body_html="<p>Contenido para {{empresa}}</p>",
    )
    assert t.id is not None
    assert t.tenant_id == "t1"
    assert t.name == "Test"
    assert t.category == TemplateCategory.OUTREACH
    assert "nombre" in t.variables
    assert "empresa" in t.variables
    assert t.body_text == "Contenido para {{empresa}}"


def test_create_template_with_string_category(manager):
    t = manager.create(
        tenant_id="t1", name="Test", category="welcome",
        subject="Bienvenido", body_html="<p>Hola</p>",
    )
    assert t.category == TemplateCategory.WELCOME


def test_create_template_with_explicit_body_text(manager):
    t = manager.create(
        tenant_id="t1", name="Test", category=TemplateCategory.OUTREACH,
        subject="Sub", body_html="<p>HTML</p>", body_text="Plain text",
    )
    assert t.body_text == "Plain text"


def test_get_template(manager):
    t = manager.create(
        tenant_id="t1", name="Test", category=TemplateCategory.OUTREACH,
        subject="S", body_html="<p>B</p>",
    )
    found = manager.get(t.id)
    assert found is not None
    assert found.name == "Test"


def test_get_nonexistent_template(manager):
    assert manager.get("nonexistent") is None


def test_update_template(manager):
    t = manager.create(
        tenant_id="t1", name="Original", category=TemplateCategory.OUTREACH,
        subject="Old {{var}}", body_html="<p>Old</p>",
    )
    updated = manager.update(t.id, name="Updated", subject="New {{new_var}}")
    assert updated.name == "Updated"
    assert updated.subject == "New {{new_var}}"
    assert "new_var" in updated.variables


def test_update_nonexistent_raises(manager):
    with pytest.raises(KeyError):
        manager.update("nonexistent", name="X")


def test_delete_template(manager):
    t = manager.create(
        tenant_id="t1", name="To Delete", category=TemplateCategory.OUTREACH,
        subject="S", body_html="<p>B</p>",
    )
    assert manager.delete(t.id) is True
    assert manager.get(t.id) is None


def test_delete_nonexistent_returns_false(manager):
    assert manager.delete("nonexistent") is False


def test_list_templates_by_tenant(manager):
    manager.create(tenant_id="t1", name="A", category=TemplateCategory.OUTREACH, subject="S", body_html="<p>B</p>")
    manager.create(tenant_id="t2", name="B", category=TemplateCategory.OUTREACH, subject="S", body_html="<p>B</p>")
    results = manager.list_templates("t1")
    assert len(results) == 1
    assert results[0].name == "A"


def test_list_templates_filter_by_category(manager):
    manager.create(tenant_id="t1", name="A", category=TemplateCategory.OUTREACH, subject="S", body_html="<p>B</p>")
    manager.create(tenant_id="t1", name="B", category=TemplateCategory.WELCOME, subject="S", body_html="<p>B</p>")
    results = manager.list_templates("t1", category=TemplateCategory.WELCOME)
    assert len(results) == 1
    assert results[0].category == TemplateCategory.WELCOME


def test_list_templates_search(manager):
    manager.create(tenant_id="t1", name="Cold Outreach", category=TemplateCategory.OUTREACH, subject="S", body_html="<p>B</p>", tags=["cold"])
    manager.create(tenant_id="t1", name="Welcome Email", category=TemplateCategory.WELCOME, subject="S", body_html="<p>B</p>")
    results = manager.list_templates("t1", search="cold")
    assert len(results) == 1
    assert results[0].name == "Cold Outreach"


# ------------------------------------------------------------------
# Render / Preview
# ------------------------------------------------------------------


def test_render_template(manager):
    t = manager.create(
        tenant_id="t1", name="Test", category=TemplateCategory.OUTREACH,
        subject="Hola {{nombre}}", body_html="<p>De {{empresa}}</p>",
    )
    result = manager.render(t.id, {"nombre": "Ana", "empresa": "Xcapit"})
    assert result["subject"] == "Hola Ana"
    assert "Xcapit" in result["body_html"]
    assert "Xcapit" in result["body_text"]


def test_render_nonexistent_raises(manager):
    with pytest.raises(KeyError):
        manager.render("nonexistent", {})


def test_preview_with_defaults(manager):
    t = manager.create(
        tenant_id="t1", name="Test", category=TemplateCategory.OUTREACH,
        subject="Hola {{nombre}}", body_html="<p>{{empresa}}</p>",
    )
    result = manager.preview(t.id)
    assert "[nombre]" in result["subject"]
    assert "[empresa]" in result["body_html"]


def test_preview_with_sample_data(manager):
    t = manager.create(
        tenant_id="t1", name="Test", category=TemplateCategory.OUTREACH,
        subject="Hola {{nombre}}", body_html="<p>{{empresa}}</p>",
    )
    result = manager.preview(t.id, sample_data={"nombre": "Test", "empresa": "Demo"})
    assert result["subject"] == "Hola Test"


# ------------------------------------------------------------------
# Duplicate
# ------------------------------------------------------------------


def test_duplicate_template(manager):
    t = manager.create(
        tenant_id="t1", name="Original", category=TemplateCategory.OUTREACH,
        subject="{{nombre}}", body_html="<p>Body</p>", tags=["tag1"],
    )
    dup = manager.duplicate(t.id, "Copy of Original")
    assert dup.id != t.id
    assert dup.name == "Copy of Original"
    assert dup.subject == t.subject
    assert dup.body_html == t.body_html
    assert dup.tags == t.tags
    assert dup.tenant_id == t.tenant_id


def test_duplicate_nonexistent_raises(manager):
    with pytest.raises(KeyError):
        manager.duplicate("nonexistent", "Copy")


# ------------------------------------------------------------------
# Usage tracking
# ------------------------------------------------------------------


def test_increment_usage(manager):
    t = manager.create(
        tenant_id="t1", name="Test", category=TemplateCategory.OUTREACH,
        subject="S", body_html="<p>B</p>",
    )
    assert t.usage_count == 0
    manager.increment_usage(t.id)
    manager.increment_usage(t.id)
    assert t.usage_count == 2


def test_increment_nonexistent_is_noop(manager):
    manager.increment_usage("nonexistent")  # should not raise


# ------------------------------------------------------------------
# Default templates
# ------------------------------------------------------------------


def test_get_default_templates(manager):
    defaults = manager.get_default_templates()
    assert len(defaults) >= 15


def test_setup_defaults(manager):
    templates = manager.setup_defaults("tenant-new")
    assert len(templates) >= 15
    assert all(t.tenant_id == "tenant-new" for t in templates)
    assert all(t.is_default is True for t in templates)
    # Verify they are stored
    stored = manager.list_templates("tenant-new")
    assert len(stored) == len(templates)


# ------------------------------------------------------------------
# Template category enum
# ------------------------------------------------------------------


def test_template_category_values():
    assert TemplateCategory.OUTREACH.value == "outreach"
    assert TemplateCategory.FOLLOW_UP.value == "follow_up"
    assert TemplateCategory.WELCOME.value == "welcome"
    assert TemplateCategory.ONBOARDING.value == "onboarding"
    assert TemplateCategory.NURTURE.value == "nurture"
    assert TemplateCategory.RE_ENGAGEMENT.value == "re_engagement"
    assert TemplateCategory.ANNOUNCEMENT.value == "announcement"
    assert TemplateCategory.INTERNAL.value == "internal"
