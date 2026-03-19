"""Tests for custom fields and tagging system.

Covers:
- CustomFieldManager: define, validate, set/get, search, delete
- TagManager: create, tag/untag, find, popular, merge, suggest
"""

import pytest

from xcapitsff.core.custom_fields import (
    CustomFieldDefinition,
    CustomFieldManager,
    CustomFieldValue,
    FieldType,
)
from xcapitsff.core.tags import Tag, TagManager


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


@pytest.fixture
def cfm() -> CustomFieldManager:
    return CustomFieldManager()


@pytest.fixture
def tm() -> TagManager:
    return TagManager()


TENANT = "tenant-001"


# =======================================================================
# Custom Fields — Field Definition
# =======================================================================


class TestDefineField:
    def test_define_text_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "website", "Website", FieldType.TEXT)
        assert defn.field_type == FieldType.TEXT
        assert defn.name == "website"
        assert defn.tenant_id == TENANT
        assert defn.entity_type == "lead"

    def test_define_number_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "customer", "revenue", "Annual Revenue", FieldType.NUMBER)
        assert defn.field_type == FieldType.NUMBER

    def test_define_date_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "ticket", "due_date", "Due Date", FieldType.DATE)
        assert defn.field_type == FieldType.DATE

    def test_define_boolean_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "vip", "VIP", FieldType.BOOLEAN)
        assert defn.field_type == FieldType.BOOLEAN

    def test_define_select_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(
            TENANT, "lead", "industry", "Industry", FieldType.SELECT,
            options=["Tech", "Finance", "Healthcare"],
        )
        assert defn.field_type == FieldType.SELECT
        assert defn.options == ["Tech", "Finance", "Healthcare"]

    def test_define_multi_select_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(
            TENANT, "lead", "interests", "Interests", FieldType.MULTI_SELECT,
            options=["AI", "Cloud", "Security"],
        )
        assert defn.field_type == FieldType.MULTI_SELECT

    def test_define_url_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "customer", "docs_url", "Docs URL", FieldType.URL)
        assert defn.field_type == FieldType.URL

    def test_define_email_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "alt_email", "Alt Email", FieldType.EMAIL)
        assert defn.field_type == FieldType.EMAIL

    def test_define_phone_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "customer", "phone", "Phone", FieldType.PHONE)
        assert defn.field_type == FieldType.PHONE

    def test_select_without_options_raises(self, cfm: CustomFieldManager):
        with pytest.raises(ValueError, match="requires a non-empty options list"):
            cfm.define_field(TENANT, "lead", "status", "Status", FieldType.SELECT)

    def test_invalid_entity_type_raises(self, cfm: CustomFieldManager):
        with pytest.raises(ValueError, match="Invalid entity_type"):
            cfm.define_field(TENANT, "invoice", "num", "Num", FieldType.TEXT)

    def test_duplicate_name_raises(self, cfm: CustomFieldManager):
        cfm.define_field(TENANT, "lead", "website", "Website", FieldType.TEXT)
        with pytest.raises(ValueError, match="already exists"):
            cfm.define_field(TENANT, "lead", "website", "Website 2", FieldType.TEXT)

    def test_field_type_from_string(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "notes", "Notes", "text")
        assert defn.field_type == FieldType.TEXT


# =======================================================================
# Custom Fields — Validation
# =======================================================================


class TestValidation:
    def test_text_accepts_string(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "notes", "Notes", FieldType.TEXT)
        ok, err = cfm.validate_value(defn, "Hello")
        assert ok is True
        assert err is None

    def test_text_rejects_number(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "notes", "Notes", FieldType.TEXT)
        ok, err = cfm.validate_value(defn, 42)
        assert ok is False
        assert "text" in err.lower()

    def test_number_accepts_int(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "count", "Count", FieldType.NUMBER)
        ok, err = cfm.validate_value(defn, 42)
        assert ok is True

    def test_number_accepts_float(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "rate", "Rate", FieldType.NUMBER)
        ok, err = cfm.validate_value(defn, 3.14)
        assert ok is True

    def test_number_rejects_string(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "count", "Count", FieldType.NUMBER)
        ok, err = cfm.validate_value(defn, "forty-two")
        assert ok is False

    def test_boolean_accepts_true(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "active", "Active", FieldType.BOOLEAN)
        ok, err = cfm.validate_value(defn, True)
        assert ok is True

    def test_boolean_rejects_string(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "active", "Active", FieldType.BOOLEAN)
        ok, err = cfm.validate_value(defn, "yes")
        assert ok is False

    def test_date_accepts_valid_string(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "dob", "DOB", FieldType.DATE)
        ok, err = cfm.validate_value(defn, "2024-01-15")
        assert ok is True

    def test_date_rejects_bad_format(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "dob", "DOB", FieldType.DATE)
        ok, err = cfm.validate_value(defn, "15/01/2024")
        assert ok is False

    def test_select_accepts_valid_option(self, cfm: CustomFieldManager):
        defn = cfm.define_field(
            TENANT, "lead", "tier", "Tier", FieldType.SELECT,
            options=["Gold", "Silver", "Bronze"],
        )
        ok, err = cfm.validate_value(defn, "Gold")
        assert ok is True

    def test_select_rejects_invalid_option(self, cfm: CustomFieldManager):
        defn = cfm.define_field(
            TENANT, "lead", "tier", "Tier", FieldType.SELECT,
            options=["Gold", "Silver", "Bronze"],
        )
        ok, err = cfm.validate_value(defn, "Platinum")
        assert ok is False
        assert "not in allowed options" in err

    def test_multi_select_accepts_valid_list(self, cfm: CustomFieldManager):
        defn = cfm.define_field(
            TENANT, "lead", "skills", "Skills", FieldType.MULTI_SELECT,
            options=["Python", "Go", "Rust"],
        )
        ok, err = cfm.validate_value(defn, ["Python", "Rust"])
        assert ok is True

    def test_multi_select_rejects_non_list(self, cfm: CustomFieldManager):
        defn = cfm.define_field(
            TENANT, "lead", "skills", "Skills", FieldType.MULTI_SELECT,
            options=["Python", "Go", "Rust"],
        )
        ok, err = cfm.validate_value(defn, "Python")
        assert ok is False

    def test_url_accepts_valid(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "site", "Site", FieldType.URL)
        ok, err = cfm.validate_value(defn, "https://example.com")
        assert ok is True

    def test_url_rejects_no_scheme(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "site", "Site", FieldType.URL)
        ok, err = cfm.validate_value(defn, "example.com")
        assert ok is False

    def test_email_accepts_valid(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "email2", "Email 2", FieldType.EMAIL)
        ok, err = cfm.validate_value(defn, "user@example.com")
        assert ok is True

    def test_email_rejects_invalid(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "email2", "Email 2", FieldType.EMAIL)
        ok, err = cfm.validate_value(defn, "not-an-email")
        assert ok is False

    def test_phone_accepts_valid(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "phone", "Phone", FieldType.PHONE)
        ok, err = cfm.validate_value(defn, "+1 (555) 123-4567")
        assert ok is True

    def test_phone_rejects_invalid(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "phone", "Phone", FieldType.PHONE)
        ok, err = cfm.validate_value(defn, "abc")
        assert ok is False

    def test_required_field_rejects_none(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "req", "Required", FieldType.TEXT, required=True)
        ok, err = cfm.validate_value(defn, None)
        assert ok is False
        assert "required" in err.lower()

    def test_optional_field_accepts_none(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "opt", "Optional", FieldType.TEXT)
        ok, err = cfm.validate_value(defn, None)
        assert ok is True


# =======================================================================
# Custom Fields — Set / Get / Search / Delete
# =======================================================================


class TestSetGetSearch:
    def test_set_and_get_value(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "website", "Website", FieldType.TEXT)
        cfm.set_value(defn.field_id, 1, "https://example.com")
        assert cfm.get_value(defn.field_id, 1) == "https://example.com"

    def test_get_value_returns_default(self, cfm: CustomFieldManager):
        defn = cfm.define_field(
            TENANT, "lead", "source", "Source", FieldType.TEXT, default_value="organic"
        )
        assert cfm.get_value(defn.field_id, 999) == "organic"

    def test_get_values_returns_all(self, cfm: CustomFieldManager):
        d1 = cfm.define_field(TENANT, "lead", "f1", "F1", FieldType.TEXT)
        d2 = cfm.define_field(TENANT, "lead", "f2", "F2", FieldType.NUMBER)
        cfm.set_value(d1.field_id, 1, "hello")
        cfm.set_value(d2.field_id, 1, 42)
        vals = cfm.get_values(1)
        assert vals == {"f1": "hello", "f2": 42}

    def test_set_value_validates(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "count", "Count", FieldType.NUMBER)
        with pytest.raises(ValueError):
            cfm.set_value(defn.field_id, 1, "not-a-number")

    def test_search_by_field(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "city", "City", FieldType.TEXT)
        cfm.set_value(defn.field_id, 1, "Buenos Aires")
        cfm.set_value(defn.field_id, 2, "Madrid")
        cfm.set_value(defn.field_id, 3, "Buenos Aires")
        results = cfm.search_by_field(TENANT, defn.field_id, "Buenos Aires")
        assert sorted(results) == [1, 3]

    def test_search_by_field_wrong_tenant(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "city", "City", FieldType.TEXT)
        cfm.set_value(defn.field_id, 1, "Buenos Aires")
        results = cfm.search_by_field("other-tenant", defn.field_id, "Buenos Aires")
        assert results == []

    def test_delete_field_removes_definition_and_values(self, cfm: CustomFieldManager):
        defn = cfm.define_field(TENANT, "lead", "temp", "Temp", FieldType.TEXT)
        cfm.set_value(defn.field_id, 1, "val")
        assert cfm.delete_field(defn.field_id) is True
        assert cfm.get_field(defn.field_id) is None
        assert cfm.get_value(defn.field_id, 1) is None

    def test_delete_nonexistent_field(self, cfm: CustomFieldManager):
        assert cfm.delete_field("nonexistent") is False

    def test_get_fields_sorted_by_display_order(self, cfm: CustomFieldManager):
        cfm.define_field(TENANT, "lead", "z_last", "Last", FieldType.TEXT, display_order=10)
        cfm.define_field(TENANT, "lead", "a_first", "First", FieldType.TEXT, display_order=1)
        cfm.define_field(TENANT, "lead", "m_mid", "Mid", FieldType.TEXT, display_order=5)
        fields = cfm.get_fields(TENANT, "lead")
        assert [f.name for f in fields] == ["a_first", "m_mid", "z_last"]


# =======================================================================
# Tags — CRUD
# =======================================================================


class TestTagCrud:
    def test_create_tag(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "important", "#FF0000", "lead")
        assert tag.name == "important"
        assert tag.color == "#FF0000"
        assert tag.entity_type == "lead"
        assert tag.tenant_id == TENANT

    def test_create_tag_default_color(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "basic")
        assert tag.color == "#3B82F6"
        assert tag.entity_type == "all"

    def test_duplicate_tag_raises(self, tm: TagManager):
        tm.create_tag(TENANT, "urgent", "#FF0000", "ticket")
        with pytest.raises(ValueError, match="already exists"):
            tm.create_tag(TENANT, "urgent", "#00FF00", "ticket")

    def test_invalid_color_raises(self, tm: TagManager):
        with pytest.raises(ValueError, match="hex color"):
            tm.create_tag(TENANT, "bad", "red", "lead")

    def test_empty_name_raises(self, tm: TagManager):
        with pytest.raises(ValueError, match="cannot be empty"):
            tm.create_tag(TENANT, "   ", "#FF0000")

    def test_invalid_entity_type_raises(self, tm: TagManager):
        with pytest.raises(ValueError, match="Invalid entity_type"):
            tm.create_tag(TENANT, "tag", "#FF0000", "invoice")

    def test_get_tags_filters_by_entity_type(self, tm: TagManager):
        tm.create_tag(TENANT, "lead-tag", "#FF0000", "lead")
        tm.create_tag(TENANT, "ticket-tag", "#00FF00", "ticket")
        tm.create_tag(TENANT, "global-tag", "#0000FF", "all")
        lead_tags = tm.get_tags(TENANT, "lead")
        names = [t.name for t in lead_tags]
        assert "lead-tag" in names
        assert "global-tag" in names  # "all" tags are included
        assert "ticket-tag" not in names

    def test_delete_tag(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "temp", "#FF0000")
        assert tm.delete_tag(tag.tag_id) is True
        assert tm.get_tag(tag.tag_id) is None


# =======================================================================
# Tags — Tag / Untag entities
# =======================================================================


class TestTagEntities:
    def test_tag_and_get_entity_tags(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "vip", "#FFD700", "all")
        tm.tag_entity(tag.tag_id, "lead", 1)
        tags = tm.get_entity_tags("lead", 1)
        assert len(tags) == 1
        assert tags[0].name == "vip"

    def test_tag_entity_twice_returns_false(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "dup", "#FF0000")
        assert tm.tag_entity(tag.tag_id, "lead", 1) is True
        assert tm.tag_entity(tag.tag_id, "lead", 1) is False

    def test_untag_entity(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "remove-me", "#FF0000")
        tm.tag_entity(tag.tag_id, "lead", 1)
        assert tm.untag_entity(tag.tag_id, "lead", 1) is True
        assert tm.get_entity_tags("lead", 1) == []

    def test_untag_nonexistent_returns_false(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "ghost", "#FF0000")
        assert tm.untag_entity(tag.tag_id, "lead", 999) is False

    def test_tag_entity_type_mismatch_raises(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "lead-only", "#FF0000", "lead")
        with pytest.raises(ValueError, match="restricted to entity type"):
            tm.tag_entity(tag.tag_id, "ticket", 1)

    def test_find_by_tag(self, tm: TagManager):
        tag = tm.create_tag(TENANT, "hot", "#FF0000", "all")
        tm.tag_entity(tag.tag_id, "lead", 1)
        tm.tag_entity(tag.tag_id, "lead", 2)
        tm.tag_entity(tag.tag_id, "customer", 10)
        results = tm.find_by_tag(tag.tag_id)
        assert len(results) == 3
        assert ("lead", 1) in results
        assert ("customer", 10) in results


# =======================================================================
# Tags — Popular, Merge, Suggest
# =======================================================================


class TestTagAdvanced:
    def test_popular_tags(self, tm: TagManager):
        t1 = tm.create_tag(TENANT, "popular", "#FF0000")
        t2 = tm.create_tag(TENANT, "niche", "#00FF00")
        for i in range(5):
            tm.tag_entity(t1.tag_id, "lead", i)
        tm.tag_entity(t2.tag_id, "lead", 100)
        popular = tm.get_popular_tags(TENANT, limit=10)
        assert len(popular) == 2
        # Most popular first
        assert popular[0][0].name == "popular"
        assert popular[0][1] == 5
        assert popular[1][0].name == "niche"
        assert popular[1][1] == 1

    def test_popular_tags_includes_zero_usage(self, tm: TagManager):
        tm.create_tag(TENANT, "unused", "#FF0000")
        popular = tm.get_popular_tags(TENANT)
        assert len(popular) == 1
        assert popular[0][1] == 0

    def test_merge_tags(self, tm: TagManager):
        source = tm.create_tag(TENANT, "src", "#FF0000")
        target = tm.create_tag(TENANT, "tgt", "#00FF00")
        tm.tag_entity(source.tag_id, "lead", 1)
        tm.tag_entity(source.tag_id, "lead", 2)
        tm.tag_entity(target.tag_id, "lead", 3)
        migrated = tm.merge_tags(source.tag_id, target.tag_id)
        assert migrated == 2
        # Source tag is deleted
        assert tm.get_tag(source.tag_id) is None
        # Target now has all entities
        results = tm.find_by_tag(target.tag_id)
        entity_ids = [eid for _, eid in results]
        assert sorted(entity_ids) == [1, 2, 3]

    def test_merge_tags_deduplicates(self, tm: TagManager):
        source = tm.create_tag(TENANT, "src2", "#FF0000")
        target = tm.create_tag(TENANT, "tgt2", "#00FF00")
        tm.tag_entity(source.tag_id, "lead", 1)
        tm.tag_entity(target.tag_id, "lead", 1)  # same entity already on target
        migrated = tm.merge_tags(source.tag_id, target.tag_id)
        assert migrated == 0  # no net migration since entity already tagged
        results = tm.find_by_tag(target.tag_id)
        assert len(results) == 1

    def test_merge_cross_tenant_raises(self, tm: TagManager):
        source = tm.create_tag("tenant-a", "src", "#FF0000")
        target = tm.create_tag("tenant-b", "tgt", "#00FF00")
        with pytest.raises(ValueError, match="different tenants"):
            tm.merge_tags(source.tag_id, target.tag_id)

    def test_suggest_tags_exact_match(self, tm: TagManager):
        tm.create_tag(TENANT, "billing", "#FF0000")
        tm.create_tag(TENANT, "login", "#00FF00")
        tm.create_tag(TENANT, "performance", "#0000FF")
        suggestions = tm.suggest_tags("I have a billing issue", TENANT)
        assert len(suggestions) >= 1
        assert suggestions[0].name == "billing"

    def test_suggest_tags_partial_word_match(self, tm: TagManager):
        tm.create_tag(TENANT, "machine learning", "#FF0000")
        tm.create_tag(TENANT, "web design", "#00FF00")
        suggestions = tm.suggest_tags("Our machine learning pipeline is slow", TENANT)
        assert any(t.name == "machine learning" for t in suggestions)

    def test_suggest_tags_empty_text(self, tm: TagManager):
        tm.create_tag(TENANT, "anything", "#FF0000")
        suggestions = tm.suggest_tags("", TENANT)
        assert suggestions == []

    def test_suggest_tags_no_match(self, tm: TagManager):
        tm.create_tag(TENANT, "billing", "#FF0000")
        suggestions = tm.suggest_tags("The weather is nice today", TENANT)
        assert len(suggestions) == 0
