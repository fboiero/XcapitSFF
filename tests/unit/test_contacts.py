"""Tests for Contact management — CRUD, search, merge, tagging, multi-tenant."""

import pytest

from xcapitsff.core.contacts import Contact, ContactManager


@pytest.fixture
def mgr():
    return ContactManager()


@pytest.fixture
def sample_contact(mgr):
    return mgr.create("tenant-1", "John", "Doe", email="john@acme.com")


# ---------------------------------------------------------------------------
# CRUD basics
# ---------------------------------------------------------------------------


def test_create_contact(mgr):
    c = mgr.create("t1", "Alice", "Smith", email="alice@example.com")
    assert isinstance(c, Contact)
    assert c.first_name == "Alice"
    assert c.last_name == "Smith"
    assert c.email == "alice@example.com"
    assert c.tenant_id == "t1"
    assert c.source == "manual"
    assert c.id  # uuid generated


def test_create_contact_with_kwargs(mgr):
    c = mgr.create(
        "t1", "Bob", "Jones",
        email="bob@co.com",
        phone="+1234",
        title="CTO",
        company_id="comp-1",
        source="web",
        tags=["vip", "enterprise"],
        custom_fields={"region": "LATAM"},
        notes="Important lead",
        owner_id="user-1",
    )
    assert c.phone == "+1234"
    assert c.title == "CTO"
    assert c.company_id == "comp-1"
    assert c.source == "web"
    assert "vip" in c.tags
    assert c.custom_fields["region"] == "LATAM"
    assert c.notes == "Important lead"
    assert c.owner_id == "user-1"


def test_create_contact_strips_whitespace(mgr):
    c = mgr.create("t1", "  Alice  ", "  Smith  ", email="  alice@x.com  ")
    assert c.first_name == "Alice"
    assert c.last_name == "Smith"
    assert c.email == "alice@x.com"


def test_create_contact_missing_first_name(mgr):
    with pytest.raises(ValueError, match="first_name"):
        mgr.create("t1", "", "Doe")


def test_create_contact_missing_last_name(mgr):
    with pytest.raises(ValueError, match="last_name"):
        mgr.create("t1", "John", "")


def test_create_contact_missing_tenant(mgr):
    with pytest.raises(ValueError, match="tenant_id"):
        mgr.create("", "John", "Doe")


def test_create_contact_invalid_source(mgr):
    with pytest.raises(ValueError, match="Invalid source"):
        mgr.create("t1", "John", "Doe", source="invalid")


def test_get_contact(mgr, sample_contact):
    fetched = mgr.get(sample_contact.id)
    assert fetched.id == sample_contact.id
    assert fetched.first_name == "John"


def test_get_contact_not_found(mgr):
    with pytest.raises(KeyError, match="Contact not found"):
        mgr.get("nonexistent-id")


def test_update_contact(mgr, sample_contact):
    updated = mgr.update(sample_contact.id, first_name="Jonathan", title="CEO")
    assert updated.first_name == "Jonathan"
    assert updated.title == "CEO"
    assert updated.last_name == "Doe"  # unchanged


def test_update_contact_not_found(mgr):
    with pytest.raises(KeyError, match="Contact not found"):
        mgr.update("nonexistent", first_name="X")


def test_update_contact_invalid_source(mgr, sample_contact):
    with pytest.raises(ValueError, match="Invalid source"):
        mgr.update(sample_contact.id, source="invalid")


def test_delete_contact(mgr, sample_contact):
    assert mgr.delete(sample_contact.id) is True
    with pytest.raises(KeyError):
        mgr.get(sample_contact.id)


def test_delete_contact_not_found(mgr):
    assert mgr.delete("nonexistent") is False


# ---------------------------------------------------------------------------
# List & Search
# ---------------------------------------------------------------------------


def test_list_contacts_by_tenant(mgr):
    mgr.create("t1", "A", "One", email="a@one.com")
    mgr.create("t2", "B", "Two", email="b@two.com")
    mgr.create("t1", "C", "Three", email="c@three.com")

    results = mgr.list_contacts("t1")
    assert len(results) == 2
    assert all(c.tenant_id == "t1" for c in results)


def test_list_contacts_with_company_filter(mgr):
    mgr.create("t1", "A", "One", company_id="comp-1")
    mgr.create("t1", "B", "Two", company_id="comp-2")
    mgr.create("t1", "C", "Three", company_id="comp-1")

    results = mgr.list_contacts("t1", company_id="comp-1")
    assert len(results) == 2


def test_list_contacts_with_owner_filter(mgr):
    mgr.create("t1", "A", "One", owner_id="user-1")
    mgr.create("t1", "B", "Two", owner_id="user-2")

    results = mgr.list_contacts("t1", owner_id="user-1")
    assert len(results) == 1
    assert results[0].first_name == "A"


def test_list_contacts_with_search(mgr):
    mgr.create("t1", "Alice", "Wonderland", email="alice@wonder.com")
    mgr.create("t1", "Bob", "Builder", email="bob@build.com")

    results = mgr.list_contacts("t1", search="alice")
    assert len(results) == 1
    assert results[0].first_name == "Alice"


def test_list_contacts_pagination(mgr):
    for i in range(10):
        mgr.create("t1", f"User{i}", "Last")

    page1 = mgr.list_contacts("t1", limit=3, offset=0)
    page2 = mgr.list_contacts("t1", limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    assert page1[0].id != page2[0].id


def test_search_contacts(mgr):
    mgr.create("t1", "Alice", "Wonderland", email="alice@wonder.com", tags=["vip"])
    mgr.create("t1", "Bob", "Builder", email="bob@build.com")

    results = mgr.search("t1", "vip")
    assert len(results) == 1
    assert results[0].first_name == "Alice"


def test_search_contacts_empty_query(mgr):
    mgr.create("t1", "A", "B")
    assert mgr.search("t1", "") == []
    assert mgr.search("t1", "   ") == []


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


def test_merge_contacts(mgr):
    primary = mgr.create("t1", "John", "Doe", email="john@acme.com")
    secondary = mgr.create("t1", "John", "D", phone="+9999", title="CTO", tags=["enterprise"])

    merged = mgr.merge_contacts(primary.id, secondary.id)
    assert merged.email == "john@acme.com"  # kept from primary
    assert merged.phone == "+9999"  # filled from secondary
    assert merged.title == "CTO"  # filled from secondary
    assert "enterprise" in merged.tags

    # Secondary should be deleted
    with pytest.raises(KeyError):
        mgr.get(secondary.id)


def test_merge_contacts_different_tenants(mgr):
    c1 = mgr.create("t1", "A", "B")
    c2 = mgr.create("t2", "C", "D")
    with pytest.raises(ValueError, match="different tenants"):
        mgr.merge_contacts(c1.id, c2.id)


def test_merge_contacts_not_found(mgr, sample_contact):
    with pytest.raises(KeyError, match="Secondary contact not found"):
        mgr.merge_contacts(sample_contact.id, "nonexistent")


def test_merge_contacts_merges_notes(mgr):
    primary = mgr.create("t1", "A", "B", notes="Primary note")
    secondary = mgr.create("t1", "C", "D", notes="Secondary note")
    merged = mgr.merge_contacts(primary.id, secondary.id)
    assert "Primary note" in merged.notes
    assert "Secondary note" in merged.notes


def test_merge_contacts_merges_custom_fields(mgr):
    primary = mgr.create("t1", "A", "B", custom_fields={"key1": "val1"})
    secondary = mgr.create("t1", "C", "D", custom_fields={"key2": "val2", "key1": "overridden"})
    merged = mgr.merge_contacts(primary.id, secondary.id)
    assert merged.custom_fields["key1"] == "val1"  # primary takes precedence
    assert merged.custom_fields["key2"] == "val2"  # added from secondary


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


def test_contact_timeline(mgr, sample_contact):
    timeline = mgr.get_contact_timeline(sample_contact.id)
    assert len(timeline) >= 1
    assert timeline[0]["event_type"] == "created"


def test_contact_timeline_after_update(mgr, sample_contact):
    mgr.update(sample_contact.id, title="VP")
    timeline = mgr.get_contact_timeline(sample_contact.id)
    event_types = [e["event_type"] for e in timeline]
    assert "updated" in event_types


def test_contact_timeline_not_found(mgr):
    with pytest.raises(KeyError, match="Contact not found"):
        mgr.get_contact_timeline("nonexistent")


# ---------------------------------------------------------------------------
# Assign
# ---------------------------------------------------------------------------


def test_assign_contact(mgr, sample_contact):
    assigned = mgr.assign(sample_contact.id, "user-99")
    assert assigned.owner_id == "user-99"


def test_assign_contact_not_found(mgr):
    with pytest.raises(KeyError, match="Contact not found"):
        mgr.assign("nonexistent", "user-1")


# ---------------------------------------------------------------------------
# Bulk Import
# ---------------------------------------------------------------------------


def test_bulk_import(mgr):
    rows = [
        {"first_name": "Alice", "last_name": "A", "email": "a@a.com"},
        {"first_name": "Bob", "last_name": "B"},
        {"first_name": "", "last_name": "C"},  # invalid
    ]
    result = mgr.bulk_import("t1", rows)
    assert result["imported"] == 2
    assert result["skipped"] == 1
    assert len(result["errors"]) == 1


def test_bulk_import_empty(mgr):
    result = mgr.bulk_import("t1", [])
    assert result["imported"] == 0
    assert result["skipped"] == 0


# ---------------------------------------------------------------------------
# Company contacts
# ---------------------------------------------------------------------------


def test_get_contacts_by_company(mgr):
    mgr.create("t1", "A", "One", company_id="comp-1")
    mgr.create("t1", "B", "Two", company_id="comp-2")
    mgr.create("t1", "C", "Three", company_id="comp-1")

    results = mgr.get_contacts_by_company("comp-1")
    assert len(results) == 2
    assert all(c.company_id == "comp-1" for c in results)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def test_add_tag(mgr, sample_contact):
    mgr.add_tag(sample_contact.id, "VIP")
    assert "vip" in sample_contact.tags


def test_add_tag_idempotent(mgr, sample_contact):
    mgr.add_tag(sample_contact.id, "vip")
    mgr.add_tag(sample_contact.id, "vip")
    assert sample_contact.tags.count("vip") == 1


def test_add_tag_empty(mgr, sample_contact):
    with pytest.raises(ValueError, match="Tag cannot be empty"):
        mgr.add_tag(sample_contact.id, "   ")


def test_remove_tag(mgr, sample_contact):
    mgr.add_tag(sample_contact.id, "vip")
    mgr.remove_tag(sample_contact.id, "vip")
    assert "vip" not in sample_contact.tags


def test_remove_tag_nonexistent(mgr, sample_contact):
    # Should not raise, just no-op
    contact = mgr.remove_tag(sample_contact.id, "nonexistent")
    assert contact.id == sample_contact.id


def test_tag_not_found_contact(mgr):
    with pytest.raises(KeyError, match="Contact not found"):
        mgr.add_tag("nonexistent", "vip")


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


def test_multi_tenant_isolation(mgr):
    mgr.create("t1", "Alice", "T1")
    mgr.create("t2", "Bob", "T2")
    mgr.create("t1", "Charlie", "T1b")

    t1_contacts = mgr.list_contacts("t1")
    t2_contacts = mgr.list_contacts("t2")

    assert len(t1_contacts) == 2
    assert len(t2_contacts) == 1
    assert all(c.tenant_id == "t1" for c in t1_contacts)
    assert all(c.tenant_id == "t2" for c in t2_contacts)


def test_search_multi_tenant_isolation(mgr):
    mgr.create("t1", "Alice", "Common")
    mgr.create("t2", "Bob", "Common")

    results = mgr.search("t1", "Common")
    assert len(results) == 1
    assert results[0].tenant_id == "t1"
