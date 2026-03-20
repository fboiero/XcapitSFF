"""Tests for Company management — CRUD, search, hierarchy, enrichment, merge, tagging, multi-tenant."""

import pytest

from xcapitsff.core.companies import Company, CompanyManager
from xcapitsff.core.contacts import ContactManager


@pytest.fixture
def contact_mgr():
    return ContactManager()


@pytest.fixture
def mgr(contact_mgr):
    return CompanyManager(contact_manager=contact_mgr)


@pytest.fixture
def sample_company(mgr):
    return mgr.create("tenant-1", "Acme Corp", domain="acme.com", industry="Technology")


# ---------------------------------------------------------------------------
# CRUD basics
# ---------------------------------------------------------------------------


def test_create_company(mgr):
    c = mgr.create("t1", "TestCo", domain="testco.com", industry="Finance")
    assert isinstance(c, Company)
    assert c.name == "TestCo"
    assert c.domain == "testco.com"
    assert c.industry == "Finance"
    assert c.tenant_id == "t1"
    assert c.id  # uuid generated


def test_create_company_with_all_kwargs(mgr):
    c = mgr.create(
        "t1", "BigCorp",
        domain="bigcorp.com",
        industry="Tech",
        size="201-1000",
        revenue_range="$10M-$50M",
        country="US",
        city="San Francisco",
        address="123 Main St",
        phone="+1-555-0100",
        website="https://bigcorp.com",
        logo_url="https://bigcorp.com/logo.png",
        description="A big corp",
        tags=["enterprise", "tech"],
        custom_fields={"tier": "platinum"},
        parent_company_id=None,
        owner_id="user-1",
    )
    assert c.size == "201-1000"
    assert c.revenue_range == "$10M-$50M"
    assert c.country == "US"
    assert c.city == "San Francisco"
    assert "enterprise" in c.tags
    assert c.custom_fields["tier"] == "platinum"
    assert c.owner_id == "user-1"


def test_create_company_strips_name(mgr):
    c = mgr.create("t1", "  Acme Corp  ")
    assert c.name == "Acme Corp"


def test_create_company_missing_name(mgr):
    with pytest.raises(ValueError, match="name is required"):
        mgr.create("t1", "")


def test_create_company_missing_tenant(mgr):
    with pytest.raises(ValueError, match="tenant_id is required"):
        mgr.create("", "TestCo")


def test_create_company_invalid_size(mgr):
    with pytest.raises(ValueError, match="Invalid size"):
        mgr.create("t1", "TestCo", size="huge")


def test_get_company(mgr, sample_company):
    fetched = mgr.get(sample_company.id)
    assert fetched.id == sample_company.id
    assert fetched.name == "Acme Corp"


def test_get_company_not_found(mgr):
    with pytest.raises(KeyError, match="Company not found"):
        mgr.get("nonexistent-id")


def test_update_company(mgr, sample_company):
    updated = mgr.update(sample_company.id, industry="Fintech", city="Buenos Aires")
    assert updated.industry == "Fintech"
    assert updated.city == "Buenos Aires"
    assert updated.name == "Acme Corp"  # unchanged


def test_update_company_not_found(mgr):
    with pytest.raises(KeyError, match="Company not found"):
        mgr.update("nonexistent", name="X")


def test_update_company_invalid_size(mgr, sample_company):
    with pytest.raises(ValueError, match="Invalid size"):
        mgr.update(sample_company.id, size="huge")


def test_delete_company(mgr, sample_company):
    assert mgr.delete(sample_company.id) is True
    with pytest.raises(KeyError):
        mgr.get(sample_company.id)


def test_delete_company_not_found(mgr):
    assert mgr.delete("nonexistent") is False


# ---------------------------------------------------------------------------
# List & Search
# ---------------------------------------------------------------------------


def test_list_companies_by_tenant(mgr):
    mgr.create("t1", "CompA")
    mgr.create("t2", "CompB")
    mgr.create("t1", "CompC")

    results = mgr.list_companies("t1")
    assert len(results) == 2
    assert all(c.tenant_id == "t1" for c in results)


def test_list_companies_with_industry_filter(mgr):
    mgr.create("t1", "FinCo", industry="Finance")
    mgr.create("t1", "TechCo", industry="Technology")
    mgr.create("t1", "FinCo2", industry="Finance")

    results = mgr.list_companies("t1", industry="Finance")
    assert len(results) == 2


def test_list_companies_with_search(mgr):
    mgr.create("t1", "Acme Corp", domain="acme.com")
    mgr.create("t1", "Beta Inc", domain="beta.io")

    results = mgr.list_companies("t1", search="acme")
    assert len(results) == 1
    assert results[0].name == "Acme Corp"


def test_list_companies_pagination(mgr):
    for i in range(10):
        mgr.create("t1", f"Company{i}")

    page1 = mgr.list_companies("t1", limit=3, offset=0)
    page2 = mgr.list_companies("t1", limit=3, offset=3)
    assert len(page1) == 3
    assert len(page2) == 3
    assert page1[0].id != page2[0].id


def test_search_companies(mgr):
    mgr.create("t1", "TechStartup", industry="Technology", tags=["saas"])
    mgr.create("t1", "Bank Corp", industry="Finance")

    results = mgr.search("t1", "saas")
    assert len(results) == 1
    assert results[0].name == "TechStartup"


def test_search_companies_empty_query(mgr):
    mgr.create("t1", "A")
    assert mgr.search("t1", "") == []
    assert mgr.search("t1", "   ") == []


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------


def test_hierarchy_parent_children(mgr):
    parent = mgr.create("t1", "HoldingCo")
    child1 = mgr.create("t1", "SubCo A", parent_company_id=parent.id)
    child2 = mgr.create("t1", "SubCo B", parent_company_id=parent.id)

    hierarchy = mgr.get_hierarchy(parent.id)
    assert hierarchy["parent"] is None
    assert len(hierarchy["children"]) == 2
    child_ids = {c.id for c in hierarchy["children"]}
    assert child1.id in child_ids
    assert child2.id in child_ids


def test_hierarchy_siblings(mgr):
    parent = mgr.create("t1", "Parent")
    child1 = mgr.create("t1", "Child1", parent_company_id=parent.id)
    child2 = mgr.create("t1", "Child2", parent_company_id=parent.id)

    hierarchy = mgr.get_hierarchy(child1.id)
    assert hierarchy["parent"].id == parent.id
    assert len(hierarchy["siblings"]) == 1
    assert hierarchy["siblings"][0].id == child2.id


def test_hierarchy_not_found(mgr):
    with pytest.raises(KeyError, match="Company not found"):
        mgr.get_hierarchy("nonexistent")


# ---------------------------------------------------------------------------
# Company contacts (delegation)
# ---------------------------------------------------------------------------


def test_get_company_contacts(mgr, contact_mgr):
    company = mgr.create("t1", "TestCo")
    contact_mgr.create("t1", "Alice", "A", company_id=company.id)
    contact_mgr.create("t1", "Bob", "B", company_id=company.id)
    contact_mgr.create("t1", "Charlie", "C", company_id="other")

    contacts = mgr.get_company_contacts(company.id)
    assert len(contacts) == 2


def test_get_company_contacts_not_found(mgr):
    with pytest.raises(KeyError, match="Company not found"):
        mgr.get_company_contacts("nonexistent")


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


def test_merge_companies(mgr):
    primary = mgr.create("t1", "CompA", industry="Tech")
    secondary = mgr.create("t1", "CompB", domain="compb.com", country="US", tags=["saas"])

    merged = mgr.merge_companies(primary.id, secondary.id)
    assert merged.name == "CompA"
    assert merged.domain == "compb.com"  # filled from secondary
    assert merged.country == "US"
    assert "saas" in merged.tags

    with pytest.raises(KeyError):
        mgr.get(secondary.id)


def test_merge_companies_different_tenants(mgr):
    c1 = mgr.create("t1", "A")
    c2 = mgr.create("t2", "B")
    with pytest.raises(ValueError, match="different tenants"):
        mgr.merge_companies(c1.id, c2.id)


def test_merge_companies_not_found(mgr, sample_company):
    with pytest.raises(KeyError, match="Secondary company not found"):
        mgr.merge_companies(sample_company.id, "nonexistent")


def test_merge_companies_reparents_children(mgr):
    primary = mgr.create("t1", "Primary")
    secondary = mgr.create("t1", "Secondary")
    child = mgr.create("t1", "Child", parent_company_id=secondary.id)

    mgr.merge_companies(primary.id, secondary.id)
    assert child.parent_company_id == primary.id


def test_merge_companies_reassigns_contacts(mgr, contact_mgr):
    primary = mgr.create("t1", "Primary")
    secondary = mgr.create("t1", "Secondary")
    contact = contact_mgr.create("t1", "Alice", "A", company_id=secondary.id)

    mgr.merge_companies(primary.id, secondary.id)
    assert contact.company_id == primary.id


def test_merge_companies_merges_custom_fields(mgr):
    primary = mgr.create("t1", "A", custom_fields={"k1": "v1"})
    secondary = mgr.create("t1", "B", custom_fields={"k2": "v2", "k1": "overridden"})
    merged = mgr.merge_companies(primary.id, secondary.id)
    assert merged.custom_fields["k1"] == "v1"  # primary wins
    assert merged.custom_fields["k2"] == "v2"


# ---------------------------------------------------------------------------
# Enrichment
# ---------------------------------------------------------------------------


def test_enrich_company_with_domain(mgr):
    c = mgr.create("t1", "Acme", domain="acme.com")
    enriched = mgr.enrich(c.id)
    assert enriched.website == "https://acme.com"
    assert enriched.country == "US"


def test_enrich_company_ar_domain(mgr):
    c = mgr.create("t1", "ArgCo", domain="argco.com.ar")
    enriched = mgr.enrich(c.id)
    assert enriched.country == "AR"


def test_enrich_company_no_domain(mgr):
    c = mgr.create("t1", "NoDomain")
    enriched = mgr.enrich(c.id)
    assert enriched.website is None  # no domain, nothing to enrich


def test_enrich_does_not_overwrite_existing(mgr):
    c = mgr.create("t1", "Acme", domain="acme.com", country="AR", website="https://custom.com")
    enriched = mgr.enrich(c.id)
    assert enriched.country == "AR"  # not overwritten
    assert enriched.website == "https://custom.com"  # not overwritten


def test_enrich_not_found(mgr):
    with pytest.raises(KeyError, match="Company not found"):
        mgr.enrich("nonexistent")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_get_stats(mgr, contact_mgr):
    company = mgr.create("t1", "TestCo")
    contact_mgr.create("t1", "A", "One", company_id=company.id)
    contact_mgr.create("t1", "B", "Two", company_id=company.id)

    stats = mgr.get_stats(company.id)
    assert stats["company_id"] == company.id
    assert stats["contact_count"] == 2
    assert stats["lead_count"] == 0
    assert stats["ticket_count"] == 0


def test_get_stats_not_found(mgr):
    with pytest.raises(KeyError, match="Company not found"):
        mgr.get_stats("nonexistent")


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def test_add_tag(mgr, sample_company):
    mgr.add_tag(sample_company.id, "Enterprise")
    assert "enterprise" in sample_company.tags


def test_add_tag_idempotent(mgr, sample_company):
    mgr.add_tag(sample_company.id, "enterprise")
    mgr.add_tag(sample_company.id, "enterprise")
    assert sample_company.tags.count("enterprise") == 1


def test_add_tag_empty(mgr, sample_company):
    with pytest.raises(ValueError, match="Tag cannot be empty"):
        mgr.add_tag(sample_company.id, "   ")


def test_remove_tag(mgr, sample_company):
    mgr.add_tag(sample_company.id, "enterprise")
    mgr.remove_tag(sample_company.id, "enterprise")
    assert "enterprise" not in sample_company.tags


def test_remove_tag_nonexistent(mgr, sample_company):
    # Should not raise
    company = mgr.remove_tag(sample_company.id, "nonexistent")
    assert company.id == sample_company.id


def test_tag_not_found_company(mgr):
    with pytest.raises(KeyError, match="Company not found"):
        mgr.add_tag("nonexistent", "vip")


# ---------------------------------------------------------------------------
# Multi-tenant isolation
# ---------------------------------------------------------------------------


def test_multi_tenant_isolation(mgr):
    mgr.create("t1", "Company T1a")
    mgr.create("t2", "Company T2")
    mgr.create("t1", "Company T1b")

    t1 = mgr.list_companies("t1")
    t2 = mgr.list_companies("t2")

    assert len(t1) == 2
    assert len(t2) == 1
    assert all(c.tenant_id == "t1" for c in t1)
    assert all(c.tenant_id == "t2" for c in t2)


def test_search_multi_tenant_isolation(mgr):
    mgr.create("t1", "Shared Name")
    mgr.create("t2", "Shared Name")

    results = mgr.search("t1", "Shared")
    assert len(results) == 1
    assert results[0].tenant_id == "t1"
