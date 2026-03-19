"""Tests for Campaign Manager."""

import pytest

from xcapitsff.sales.campaigns import (
    Campaign,
    CampaignManager,
    CampaignMetrics,
    CampaignStatus,
    CampaignTarget,
    CampaignType,
)


@pytest.fixture
def manager():
    return CampaignManager()


def test_create_campaign(manager):
    c = manager.create("Test Campaign", CampaignType.OUTREACH)
    assert c.campaign_id.startswith("CAMP-")
    assert c.name == "Test Campaign"
    assert c.status == CampaignStatus.DRAFT


def test_create_with_string_type(manager):
    c = manager.create("Test", "nurturing")
    assert c.campaign_type == CampaignType.NURTURING


def test_start_campaign(manager):
    c = manager.create("Test", CampaignType.OUTREACH)
    c.start()
    assert c.status == CampaignStatus.ACTIVE
    assert c.started_at is not None


def test_cannot_start_active_campaign(manager):
    c = manager.create("Test", CampaignType.OUTREACH)
    c.start()
    with pytest.raises(ValueError):
        c.start()


def test_pause_and_resume(manager):
    c = manager.create("Test", CampaignType.OUTREACH)
    c.start()
    c.pause()
    assert c.status == CampaignStatus.PAUSED
    c.resume()
    assert c.status == CampaignStatus.ACTIVE


def test_complete_campaign(manager):
    c = manager.create("Test", CampaignType.OUTREACH)
    c.start()
    c.complete()
    assert c.status == CampaignStatus.COMPLETED
    assert c.completed_at is not None


def test_cancel_campaign(manager):
    c = manager.create("Test", CampaignType.OUTREACH)
    c.cancel()
    assert c.status == CampaignStatus.CANCELLED


def test_list_campaigns(manager):
    manager.create("A", CampaignType.OUTREACH)
    manager.create("B", CampaignType.NURTURING)
    manager.create("C", CampaignType.REACTIVATION)
    assert len(manager.list_campaigns()) == 3


def test_list_by_status(manager):
    c1 = manager.create("A", CampaignType.OUTREACH)
    c2 = manager.create("B", CampaignType.OUTREACH)
    c1.start()
    active = manager.list_campaigns(status=CampaignStatus.ACTIVE)
    assert len(active) == 1
    drafts = manager.list_campaigns(status=CampaignStatus.DRAFT)
    assert len(drafts) == 1


def test_metrics_recalculate():
    m = CampaignMetrics(total_targeted=100, messages_sent=50, replies_received=10)
    m.recalculate()
    assert m.reply_rate == 20.0
    assert m.conversion_rate == 0.0


def test_update_metrics(manager):
    c = manager.create("Test", CampaignType.OUTREACH)
    manager.update_metrics(c.campaign_id, messages_sent=100, replies_received=25)
    assert c.metrics.messages_sent == 100
    assert c.metrics.reply_rate == 25.0


def test_get_stats(manager):
    c1 = manager.create("A", CampaignType.OUTREACH)
    c2 = manager.create("B", CampaignType.NURTURING)
    c1.start()
    manager.update_metrics(c1.campaign_id, messages_sent=50, replies_received=5)
    stats = manager.get_stats()
    assert stats["total_campaigns"] == 2
    assert stats["total_messages_sent"] == 50
    assert stats["total_replies"] == 5


def test_target_defaults():
    t = CampaignTarget()
    assert t.regions is None
    assert t.c_level_only is False
    assert t.exclude_contacted_days == 30


def test_campaign_with_target(manager):
    target = CampaignTarget(
        regions=["LATAM"],
        score_min=60,
        c_level_only=True,
    )
    c = manager.create("VIP Campaign", CampaignType.OUTREACH, target=target)
    assert c.target.regions == ["LATAM"]
    assert c.target.score_min == 60
    assert c.target.c_level_only is True
