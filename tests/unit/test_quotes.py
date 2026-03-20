"""Tests for Quotes & Proposals management."""

import pytest

from xcapitsff.core.quotes import (
    LineItem,
    Quote,
    QuoteManager,
    QuoteStatus,
)


@pytest.fixture
def mgr():
    """Return a fresh QuoteManager for each test."""
    return QuoteManager()


def _sample_items():
    return [
        {"description": "Consulting hours", "quantity": 10, "unit_price": 150.0},
        {"description": "Software license", "quantity": 1, "unit_price": 5000.0, "discount_percent": 10, "tax_percent": 21},
    ]


@pytest.fixture
def sample_quote(mgr):
    """Create a sample quote and return (manager, quote)."""
    quote = mgr.create(
        tenant_id="t1",
        deal_id="deal-1",
        title="Q1 Proposal",
        client_name="Acme Corp",
        client_email="buyer@acme.com",
        line_items=_sample_items(),
        notes="Net 30 payment",
        terms="Standard T&C",
    )
    return mgr, quote


# ---------------------------------------------------------------------------
# LineItem
# ---------------------------------------------------------------------------


def test_line_item_total_no_discount_no_tax():
    item = LineItem(id="1", description="Service", quantity=5, unit_price=100.0)
    assert item.total == 500.0


def test_line_item_total_with_discount():
    item = LineItem(id="1", description="Service", quantity=10, unit_price=100.0, discount_percent=20)
    # 10*100 = 1000, discount=200, after=800, no tax
    assert item.total == 800.0


def test_line_item_total_with_tax():
    item = LineItem(id="1", description="Service", quantity=1, unit_price=1000.0, tax_percent=21)
    # 1000, no discount, tax=210
    assert item.total == 1210.0


def test_line_item_total_with_discount_and_tax():
    item = LineItem(
        id="1", description="Service", quantity=2, unit_price=500.0,
        discount_percent=10, tax_percent=21,
    )
    # subtotal=1000, discount=100, after=900, tax=189
    assert item.total == 1089.0


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


def test_create_quote_defaults(sample_quote):
    mgr, quote = sample_quote
    assert quote.tenant_id == "t1"
    assert quote.deal_id == "deal-1"
    assert quote.title == "Q1 Proposal"
    assert quote.client_name == "Acme Corp"
    assert quote.status == QuoteStatus.DRAFT
    assert quote.quote_number == "QT-0001"
    assert len(quote.line_items) == 2
    assert quote.subtotal > 0
    assert quote.total > 0
    assert quote.created_at
    assert quote.valid_until


def test_create_quote_auto_calculates_totals(mgr):
    quote = mgr.create(
        tenant_id="t1",
        deal_id="d1",
        title="Test",
        client_name="Client",
        client_email="c@c.com",
        line_items=[
            {"description": "Item A", "quantity": 2, "unit_price": 100.0, "discount_percent": 0, "tax_percent": 0},
        ],
    )
    assert quote.subtotal == 200.0
    assert quote.discount_total == 0.0
    assert quote.tax_total == 0.0
    assert quote.total == 200.0


def test_create_quote_increments_number(mgr):
    q1 = mgr.create("t1", "d1", "A", "C", "c@c.com", [{"description": "X", "unit_price": 100}])
    q2 = mgr.create("t1", "d1", "B", "C", "c@c.com", [{"description": "Y", "unit_price": 200}])
    assert q1.quote_number == "QT-0001"
    assert q2.quote_number == "QT-0002"


def test_create_quote_unique_ids(mgr):
    q1 = mgr.create("t1", "d1", "A", "C", "c@c.com", [{"description": "X", "unit_price": 100}])
    q2 = mgr.create("t1", "d1", "B", "C", "c@c.com", [{"description": "Y", "unit_price": 200}])
    assert q1.id != q2.id


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_get_quote(sample_quote):
    mgr, quote = sample_quote
    fetched = mgr.get(quote.id)
    assert fetched.title == "Q1 Proposal"


def test_get_quote_not_found(mgr):
    with pytest.raises(KeyError):
        mgr.get("nonexistent")


def test_update_quote(sample_quote):
    mgr, quote = sample_quote
    updated = mgr.update(quote.id, title="Updated Proposal", notes="Revised")
    assert updated.title == "Updated Proposal"
    assert updated.notes == "Revised"


def test_update_quote_not_found(mgr):
    with pytest.raises(KeyError):
        mgr.update("nonexistent", title="X")


def test_delete_quote(sample_quote):
    mgr, quote = sample_quote
    assert mgr.delete(quote.id) is True
    with pytest.raises(KeyError):
        mgr.get(quote.id)


def test_delete_quote_not_found(mgr):
    assert mgr.delete("nonexistent") is False


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_quotes_by_tenant(mgr):
    mgr.create("t1", "d1", "A", "C", "c@c.com", [{"description": "X", "unit_price": 100}])
    mgr.create("t2", "d2", "B", "C", "c@c.com", [{"description": "Y", "unit_price": 200}])
    assert len(mgr.list_quotes("t1")) == 1
    assert len(mgr.list_quotes("t2")) == 1


def test_list_quotes_filter_by_deal(mgr):
    mgr.create("t1", "d1", "A", "C", "c@c.com", [{"description": "X", "unit_price": 100}])
    mgr.create("t1", "d2", "B", "C", "c@c.com", [{"description": "Y", "unit_price": 200}])
    results = mgr.list_quotes("t1", deal_id="d1")
    assert len(results) == 1
    assert results[0].deal_id == "d1"


def test_list_quotes_filter_by_status(sample_quote):
    mgr, quote = sample_quote
    mgr.send(quote.id)
    drafts = mgr.list_quotes("t1", status=QuoteStatus.DRAFT)
    sent = mgr.list_quotes("t1", status=QuoteStatus.SENT)
    assert len(drafts) == 0
    assert len(sent) == 1


# ---------------------------------------------------------------------------
# Status lifecycle
# ---------------------------------------------------------------------------


def test_send_quote(sample_quote):
    mgr, quote = sample_quote
    sent = mgr.send(quote.id)
    assert sent.status == QuoteStatus.SENT
    assert sent.sent_at is not None


def test_mark_viewed(sample_quote):
    mgr, quote = sample_quote
    viewed = mgr.mark_viewed(quote.id)
    assert viewed.status == QuoteStatus.VIEWED
    assert viewed.viewed_at is not None


def test_accept_quote(sample_quote):
    mgr, quote = sample_quote
    accepted = mgr.accept(quote.id)
    assert accepted.status == QuoteStatus.ACCEPTED
    assert accepted.accepted_at is not None


def test_reject_quote(sample_quote):
    mgr, quote = sample_quote
    rejected = mgr.reject(quote.id)
    assert rejected.status == QuoteStatus.REJECTED


# ---------------------------------------------------------------------------
# Duplicate
# ---------------------------------------------------------------------------


def test_duplicate_quote(sample_quote):
    mgr, quote = sample_quote
    dup = mgr.duplicate(quote.id)
    assert dup.id != quote.id
    assert dup.quote_number != quote.quote_number
    assert dup.status == QuoteStatus.DRAFT
    assert dup.title == quote.title
    assert dup.client_name == quote.client_name
    assert dup.total == quote.total
    assert len(dup.line_items) == len(quote.line_items)
    # Line items should have new IDs
    original_ids = {li.id for li in quote.line_items}
    dup_ids = {li.id for li in dup.line_items}
    assert original_ids.isdisjoint(dup_ids)


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------


def test_export_markdown(sample_quote):
    mgr, quote = sample_quote
    md = mgr.export_markdown(quote.id)
    assert f"# Quote {quote.quote_number}" in md
    assert "Acme Corp" in md
    assert "Consulting hours" in md
    assert "Software license" in md
    assert "Subtotal" in md
    assert "Net 30 payment" in md
    assert "Standard T&C" in md
    assert "XcapitSFF" in md


# ---------------------------------------------------------------------------
# Line item management
# ---------------------------------------------------------------------------


def test_add_line_item(sample_quote):
    mgr, quote = sample_quote
    old_total = quote.total
    old_count = len(quote.line_items)
    updated = mgr.add_line_item(quote.id, "Extra service", 5, 200.0)
    assert len(updated.line_items) == old_count + 1
    assert updated.total > old_total


def test_remove_line_item(sample_quote):
    mgr, quote = sample_quote
    item_id = quote.line_items[0].id
    old_count = len(quote.line_items)
    updated = mgr.remove_line_item(quote.id, item_id)
    assert len(updated.line_items) == old_count - 1
    remaining_ids = [li.id for li in updated.line_items]
    assert item_id not in remaining_ids


def test_add_then_remove_recalculates(mgr):
    quote = mgr.create(
        "t1", "d1", "Test", "C", "c@c.com",
        [{"description": "Base", "quantity": 1, "unit_price": 1000}],
    )
    assert quote.total == 1000.0
    mgr.add_line_item(quote.id, "Extra", 1, 500.0)
    assert quote.total == 1500.0
    # Remove the extra item (second one)
    extra_id = quote.line_items[1].id
    mgr.remove_line_item(quote.id, extra_id)
    assert quote.total == 1000.0


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_quote_stats(mgr):
    q1 = mgr.create("t1", "d1", "A", "C", "c@c.com", [{"description": "X", "unit_price": 1000}])
    q2 = mgr.create("t1", "d2", "B", "C", "c@c.com", [{"description": "Y", "unit_price": 2000}])
    q3 = mgr.create("t1", "d3", "C", "C", "c@c.com", [{"description": "Z", "unit_price": 3000}])

    mgr.send(q1.id)
    mgr.send(q2.id)
    mgr.accept(q2.id)
    mgr.send(q3.id)
    mgr.reject(q3.id)

    stats = mgr.get_quote_stats("t1")
    assert stats["total_sent"] == 3  # sent + accepted + rejected
    assert stats["total_accepted"] == 1
    assert stats["acceptance_rate"] == pytest.approx(33.3, abs=0.1)
    assert stats["total_value_sent"] == 6000.0
    assert stats["total_value_accepted"] == 2000.0


def test_quote_stats_empty(mgr):
    stats = mgr.get_quote_stats("empty-tenant")
    assert stats["total_sent"] == 0
    assert stats["total_accepted"] == 0
    assert stats["acceptance_rate"] == 0.0
