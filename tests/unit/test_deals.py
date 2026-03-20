"""Tests for Deals pipeline management."""

import pytest
from datetime import datetime, timedelta

from xcapitsff.core.deals import (
    Deal,
    DealManager,
    DealPriority,
    DealStage,
    DEAL_STAGE_TRANSITIONS,
    STAGE_PROBABILITY,
)


@pytest.fixture
def mgr():
    """Return a fresh DealManager for each test."""
    return DealManager()


@pytest.fixture
def sample_deal(mgr):
    """Create a sample deal and return (manager, deal)."""
    deal = mgr.create("t1", "Acme Corp Deal", 50000.0, owner_id="user-1")
    return mgr, deal


# ---------------------------------------------------------------------------
# Creation
# ---------------------------------------------------------------------------


def test_create_deal_defaults(mgr):
    """Create a deal with default values."""
    deal = mgr.create("t1", "Test Deal", 10000.0)
    assert deal.tenant_id == "t1"
    assert deal.name == "Test Deal"
    assert deal.amount == 10000.0
    assert deal.stage == DealStage.PROSPECTING
    assert deal.priority == DealPriority.MEDIUM
    assert deal.currency == "USD"
    assert deal.probability == STAGE_PROBABILITY[DealStage.PROSPECTING]
    assert deal.created_at
    assert deal.updated_at
    assert deal.closed_at is None
    assert deal.lost_reason is None


def test_create_deal_custom_fields(mgr):
    """Create a deal with all optional fields."""
    deal = mgr.create(
        "t1",
        "Enterprise Deal",
        200000.0,
        stage=DealStage.QUALIFICATION,
        priority=DealPriority.HIGH,
        currency="EUR",
        probability=30.0,
        expected_close_date="2026-06-15",
        owner_id="rep-1",
        company_id="comp-1",
        contact_id="contact-1",
        lead_id="lead-1",
        tags=["enterprise", "latam"],
        custom_fields={"source": "referral"},
    )
    assert deal.stage == DealStage.QUALIFICATION
    assert deal.priority == DealPriority.HIGH
    assert deal.currency == "EUR"
    assert deal.probability == 30.0
    assert deal.expected_close_date == "2026-06-15"
    assert deal.company_id == "comp-1"
    assert deal.lead_id == "lead-1"
    assert "enterprise" in deal.tags
    assert deal.custom_fields["source"] == "referral"


def test_create_deal_generates_unique_ids(mgr):
    """Each deal gets a unique UUID."""
    d1 = mgr.create("t1", "Deal A", 1000)
    d2 = mgr.create("t1", "Deal B", 2000)
    assert d1.id != d2.id


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_get_deal(sample_deal):
    mgr, deal = sample_deal
    fetched = mgr.get(deal.id)
    assert fetched.name == "Acme Corp Deal"


def test_get_deal_not_found(mgr):
    with pytest.raises(KeyError):
        mgr.get("nonexistent-id")


def test_update_deal(sample_deal):
    mgr, deal = sample_deal
    updated = mgr.update(deal.id, name="Acme Renamed", amount=75000.0)
    assert updated.name == "Acme Renamed"
    assert updated.amount == 75000.0


def test_update_deal_not_found(mgr):
    with pytest.raises(KeyError):
        mgr.update("nonexistent-id", name="X")


def test_delete_deal(sample_deal):
    mgr, deal = sample_deal
    assert mgr.delete(deal.id) is True
    with pytest.raises(KeyError):
        mgr.get(deal.id)


def test_delete_deal_not_found(mgr):
    assert mgr.delete("nonexistent-id") is False


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_deals_by_tenant(mgr):
    mgr.create("t1", "Deal A", 1000)
    mgr.create("t1", "Deal B", 2000)
    mgr.create("t2", "Deal C", 3000)
    assert len(mgr.list_deals("t1")) == 2
    assert len(mgr.list_deals("t2")) == 1


def test_list_deals_filter_by_stage(mgr):
    mgr.create("t1", "Deal A", 1000, stage=DealStage.PROSPECTING)
    mgr.create("t1", "Deal B", 2000, stage=DealStage.PROPOSAL)
    results = mgr.list_deals("t1", stage=DealStage.PROPOSAL)
    assert len(results) == 1
    assert results[0].name == "Deal B"


def test_list_deals_filter_by_owner(mgr):
    mgr.create("t1", "Deal A", 1000, owner_id="rep-1")
    mgr.create("t1", "Deal B", 2000, owner_id="rep-2")
    results = mgr.list_deals("t1", owner_id="rep-1")
    assert len(results) == 1


def test_list_deals_pagination(mgr):
    for i in range(5):
        mgr.create("t1", f"Deal {i}", 1000)
    assert len(mgr.list_deals("t1", limit=2)) == 2
    assert len(mgr.list_deals("t1", limit=2, offset=3)) == 2


# ---------------------------------------------------------------------------
# Stage transitions
# ---------------------------------------------------------------------------


def test_move_stage_valid(sample_deal):
    mgr, deal = sample_deal
    assert deal.stage == DealStage.PROSPECTING
    updated = mgr.move_stage(deal.id, DealStage.QUALIFICATION)
    assert updated.stage == DealStage.QUALIFICATION
    assert updated.probability == STAGE_PROBABILITY[DealStage.QUALIFICATION]


def test_move_stage_invalid(sample_deal):
    mgr, deal = sample_deal
    with pytest.raises(ValueError, match="Invalid transition"):
        mgr.move_stage(deal.id, DealStage.CLOSED_WON)


def test_move_stage_to_closed_won(mgr):
    deal = mgr.create("t1", "Deal", 10000, stage=DealStage.NEGOTIATION)
    # Need to set stage directly for test since we can't transition through all stages
    won = mgr.move_stage(deal.id, DealStage.CLOSED_WON)
    assert won.stage == DealStage.CLOSED_WON
    assert won.closed_at is not None
    assert won.probability == 100.0


def test_move_stage_to_closed_lost_with_reason(sample_deal):
    mgr, deal = sample_deal
    lost = mgr.move_stage(deal.id, DealStage.CLOSED_LOST, lost_reason="Budget cut")
    assert lost.stage == DealStage.CLOSED_LOST
    assert lost.closed_at is not None
    assert lost.lost_reason == "Budget cut"
    assert lost.probability == 0.0


# ---------------------------------------------------------------------------
# Pipeline summary
# ---------------------------------------------------------------------------


def test_pipeline_summary(mgr):
    mgr.create("t1", "Active 1", 10000, stage=DealStage.PROSPECTING)
    mgr.create("t1", "Active 2", 20000, stage=DealStage.PROPOSAL)
    d3 = mgr.create("t1", "Won", 30000, stage=DealStage.NEGOTIATION)
    mgr.move_stage(d3.id, DealStage.CLOSED_WON)

    summary = mgr.get_pipeline_summary("t1")
    assert summary["by_stage"]["prospecting"]["count"] == 1
    assert summary["by_stage"]["proposal"]["count"] == 1
    assert summary["by_stage"]["closed_won"]["count"] == 1
    assert summary["total_pipeline"] == 30000.0  # only active deals
    assert summary["weighted_pipeline"] > 0
    assert summary["avg_deal_size"] == 15000.0
    assert summary["win_rate"] == 100.0  # 1 won, 0 lost


def test_pipeline_summary_empty(mgr):
    summary = mgr.get_pipeline_summary("empty-tenant")
    assert summary["total_pipeline"] == 0.0
    assert summary["avg_deal_size"] == 0.0
    assert summary["win_rate"] == 0.0


# ---------------------------------------------------------------------------
# Forecast
# ---------------------------------------------------------------------------


def test_forecast(mgr):
    now = datetime.now(tz=None)
    close_date = (now + timedelta(days=15)).isoformat()
    mgr.create("t1", "Deal 1", 10000, expected_close_date=close_date)
    forecast = mgr.get_forecast("t1", months=3)
    assert "by_month" in forecast
    assert "total_forecast" in forecast
    assert forecast["total_forecast"] >= 0


# ---------------------------------------------------------------------------
# Won / Lost / Aging
# ---------------------------------------------------------------------------


def test_get_won_deals(mgr):
    d = mgr.create("t1", "Won Deal", 5000, stage=DealStage.NEGOTIATION)
    mgr.move_stage(d.id, DealStage.CLOSED_WON)
    won = mgr.get_won_deals("t1", days=30)
    assert len(won) == 1
    assert won[0].id == d.id


def test_get_lost_deals(mgr):
    d = mgr.create("t1", "Lost Deal", 5000)
    mgr.move_stage(d.id, DealStage.CLOSED_LOST, lost_reason="No budget")
    lost = mgr.get_lost_deals("t1", days=30)
    assert len(lost) == 1
    assert lost[0].lost_reason == "No budget"


def test_get_aging_deals(mgr):
    d = mgr.create("t1", "Old Deal", 3000)
    # Simulate old updated_at
    d.updated_at = (datetime.now(tz=None) - timedelta(days=60)).isoformat()
    aging = mgr.get_aging_deals("t1", days=30)
    assert len(aging) == 1
    assert aging[0].id == d.id


# ---------------------------------------------------------------------------
# Lead conversion
# ---------------------------------------------------------------------------


def test_convert_from_lead(mgr):
    deal = mgr.convert_from_lead("t1", lead_id="lead-42", name="Converted Deal", amount=25000)
    assert deal.lead_id == "lead-42"
    assert deal.name == "Converted Deal"
    assert deal.amount == 25000
    assert deal.stage == DealStage.PROSPECTING


# ---------------------------------------------------------------------------
# Stage transitions map
# ---------------------------------------------------------------------------


def test_stage_transitions_completeness():
    """All stages have entries in the transitions map."""
    for stage in DealStage:
        assert stage in DEAL_STAGE_TRANSITIONS
