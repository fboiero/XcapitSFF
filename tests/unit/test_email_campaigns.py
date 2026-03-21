"""Tests for Email Campaign Manager."""

import pytest

from xcapitsff.core.email_campaigns import (
    CampaignStats,
    CampaignStatus,
    CampaignType,
    EmailCampaign,
    EmailCampaignManager,
    Recipient,
    RecipientStatus,
)


@pytest.fixture
def manager():
    return EmailCampaignManager()


@pytest.fixture
def campaign_with_recipients(manager):
    """Create a campaign with 3 recipients for reuse in tests."""
    c = manager.create("t1", "Newsletter", CampaignType.ONE_TIME, "tpl-1")
    manager.add_recipients(c.id, [
        {"email": "a@test.com", "name": "Alice"},
        {"email": "b@test.com", "name": "Bob"},
        {"email": "c@test.com", "name": "Charlie"},
    ])
    return c


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------


def test_create_campaign(manager):
    c = manager.create("t1", "Launch Campaign", CampaignType.ONE_TIME, "tpl-1")
    assert c.id is not None
    assert c.tenant_id == "t1"
    assert c.name == "Launch Campaign"
    assert c.type == CampaignType.ONE_TIME
    assert c.status == CampaignStatus.DRAFT
    assert c.template_id == "tpl-1"


def test_create_campaign_string_type(manager):
    c = manager.create("t1", "Drip", "drip", "tpl-2")
    assert c.type == CampaignType.DRIP


def test_create_with_created_by(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1", created_by="user@test.com")
    assert c.created_by == "user@test.com"


def test_get_campaign(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    found = manager.get(c.id)
    assert found is not None
    assert found.name == "Test"


def test_get_nonexistent(manager):
    assert manager.get("nonexistent") is None


def test_update_campaign(manager):
    c = manager.create("t1", "Original", CampaignType.ONE_TIME, "tpl-1")
    updated = manager.update(c.id, name="Updated", subject_override="New Subject")
    assert updated.name == "Updated"
    assert updated.subject_override == "New Subject"


def test_update_nonexistent_raises(manager):
    with pytest.raises(KeyError):
        manager.update("nonexistent", name="X")


def test_delete_campaign(manager):
    c = manager.create("t1", "To Delete", CampaignType.ONE_TIME, "tpl-1")
    assert manager.delete(c.id) is True
    assert manager.get(c.id) is None


def test_delete_nonexistent(manager):
    assert manager.delete("nonexistent") is False


def test_list_campaigns_by_tenant(manager):
    manager.create("t1", "A", CampaignType.ONE_TIME, "tpl-1")
    manager.create("t2", "B", CampaignType.ONE_TIME, "tpl-1")
    results = manager.list_campaigns("t1")
    assert len(results) == 1
    assert results[0].name == "A"


def test_list_campaigns_filter_status(manager):
    c1 = manager.create("t1", "Draft", CampaignType.ONE_TIME, "tpl-1")
    c2 = manager.create("t1", "Scheduled", CampaignType.ONE_TIME, "tpl-1")
    manager.schedule(c2.id, "2026-04-01T10:00:00")
    results = manager.list_campaigns("t1", status=CampaignStatus.SCHEDULED)
    assert len(results) == 1
    assert results[0].status == CampaignStatus.SCHEDULED


# ------------------------------------------------------------------
# Recipients
# ------------------------------------------------------------------


def test_add_recipients(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    manager.add_recipients(c.id, [
        {"email": "a@test.com", "name": "Alice"},
        {"email": "b@test.com", "name": "Bob"},
    ])
    assert len(c.recipients) == 2
    assert c.recipients[0].email == "a@test.com"
    assert c.recipients[0].name == "Alice"
    assert c.recipients[0].status == RecipientStatus.PENDING


def test_add_recipients_deduplication(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    manager.add_recipients(c.id, [{"email": "a@test.com"}])
    manager.add_recipients(c.id, [{"email": "a@test.com"}, {"email": "b@test.com"}])
    assert len(c.recipients) == 2


def test_add_recipients_nonexistent_raises(manager):
    with pytest.raises(KeyError):
        manager.add_recipients("nonexistent", [{"email": "a@test.com"}])


def test_remove_recipient(manager, campaign_with_recipients):
    c = campaign_with_recipients
    assert manager.remove_recipient(c.id, "b@test.com") is True
    assert len(c.recipients) == 2
    assert all(r.email != "b@test.com" for r in c.recipients)


def test_remove_nonexistent_recipient(manager, campaign_with_recipients):
    c = campaign_with_recipients
    assert manager.remove_recipient(c.id, "z@test.com") is False


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


def test_schedule_campaign(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    result = manager.schedule(c.id, "2026-04-01T10:00:00")
    assert result.status == CampaignStatus.SCHEDULED
    assert result.scheduled_at == "2026-04-01T10:00:00"


def test_schedule_sent_campaign_raises(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    with pytest.raises(ValueError):
        manager.schedule(c.id, "2026-04-01T10:00:00")


def test_send_campaign(manager, campaign_with_recipients):
    c = campaign_with_recipients
    result = manager.send(c.id)
    assert result.status == CampaignStatus.SENT
    assert result.started_at is not None
    assert result.completed_at is not None
    assert all(r.status == RecipientStatus.SENT for r in result.recipients)
    assert all(r.sent_at is not None for r in result.recipients)


def test_send_already_sent_raises(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    with pytest.raises(ValueError):
        manager.send(c.id)


def test_pause_scheduled_campaign(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    manager.schedule(c.id, "2026-04-01T10:00:00")
    result = manager.pause(c.id)
    assert result.status == CampaignStatus.PAUSED


def test_pause_draft_raises(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    with pytest.raises(ValueError):
        manager.pause(c.id)


def test_resume_paused_campaign(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    manager.schedule(c.id, "2026-04-01T10:00:00")
    manager.pause(c.id)
    result = manager.resume(c.id)
    assert result.status == CampaignStatus.SCHEDULED


def test_resume_non_paused_raises(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    with pytest.raises(ValueError):
        manager.resume(c.id)


def test_cancel_campaign(manager):
    c = manager.create("t1", "Test", CampaignType.ONE_TIME, "tpl-1")
    result = manager.cancel(c.id)
    assert result.status == CampaignStatus.CANCELLED
    assert result.completed_at is not None


def test_cancel_sent_raises(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    with pytest.raises(ValueError):
        manager.cancel(c.id)


# ------------------------------------------------------------------
# Tracking events
# ------------------------------------------------------------------


def test_record_open(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    assert manager.record_open(c.id, "a@test.com") is True
    recipient = next(r for r in c.recipients if r.email == "a@test.com")
    assert recipient.status == RecipientStatus.OPENED
    assert recipient.opened_at is not None


def test_record_open_nonexistent_email(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    assert manager.record_open(c.id, "z@test.com") is False


def test_record_click(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    assert manager.record_click(c.id, "a@test.com") is True
    recipient = next(r for r in c.recipients if r.email == "a@test.com")
    assert recipient.status == RecipientStatus.CLICKED
    assert recipient.clicked_at is not None
    assert recipient.opened_at is not None  # auto-set on click


def test_record_bounce(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    assert manager.record_bounce(c.id, "b@test.com") is True
    recipient = next(r for r in c.recipients if r.email == "b@test.com")
    assert recipient.status == RecipientStatus.BOUNCED


def test_record_unsubscribe(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    assert manager.record_unsubscribe(c.id, "c@test.com") is True
    recipient = next(r for r in c.recipients if r.email == "c@test.com")
    assert recipient.status == RecipientStatus.UNSUBSCRIBED


def test_record_on_nonexistent_campaign(manager):
    assert manager.record_open("nonexistent", "a@test.com") is False
    assert manager.record_click("nonexistent", "a@test.com") is False
    assert manager.record_bounce("nonexistent", "a@test.com") is False
    assert manager.record_unsubscribe("nonexistent", "a@test.com") is False


# ------------------------------------------------------------------
# Stats
# ------------------------------------------------------------------


def test_get_stats_empty(manager):
    c = manager.create("t1", "Empty", CampaignType.ONE_TIME, "tpl-1")
    stats = manager.get_stats(c.id)
    assert stats.total_recipients == 0
    assert stats.sent == 0
    assert stats.open_rate == 0.0


def test_get_stats_after_send(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    stats = manager.get_stats(c.id)
    assert stats.total_recipients == 3
    assert stats.sent == 3
    assert stats.delivered == 3
    assert stats.bounced == 0
    assert stats.bounce_rate == 0.0


def test_get_stats_with_events(manager, campaign_with_recipients):
    c = campaign_with_recipients
    manager.send(c.id)
    manager.record_open(c.id, "a@test.com")
    manager.record_click(c.id, "b@test.com")
    manager.record_bounce(c.id, "c@test.com")
    stats = manager.get_stats(c.id)
    assert stats.total_recipients == 3
    assert stats.sent == 3
    assert stats.bounced == 1
    assert stats.delivered == 2
    assert stats.opened == 2  # a opened + b clicked (click implies open)
    assert stats.clicked == 1  # b clicked
    assert stats.open_rate == 100.0  # 2 opened / 2 delivered
    assert stats.click_rate == 50.0  # 1 clicked / 2 delivered


def test_get_stats_nonexistent_raises(manager):
    with pytest.raises(KeyError):
        manager.get_stats("nonexistent")


def test_get_campaign_performance(manager):
    c1 = manager.create("t1", "C1", CampaignType.ONE_TIME, "tpl-1")
    manager.add_recipients(c1.id, [
        {"email": "a@test.com"},
        {"email": "b@test.com"},
    ])
    manager.send(c1.id)
    manager.record_open(c1.id, "a@test.com")

    c2 = manager.create("t1", "C2", CampaignType.ONE_TIME, "tpl-1")
    manager.add_recipients(c2.id, [{"email": "c@test.com"}])
    manager.send(c2.id)

    perf = manager.get_campaign_performance("t1", days=30)
    assert perf["total_campaigns"] == 2
    assert perf["total_recipients"] == 3
    assert perf["total_sent"] == 3
    assert perf["total_opened"] == 1


def test_get_campaign_performance_empty_tenant(manager):
    perf = manager.get_campaign_performance("empty-tenant", days=30)
    assert perf["total_campaigns"] == 0
    assert perf["avg_open_rate"] == 0.0


# ------------------------------------------------------------------
# Enum values
# ------------------------------------------------------------------


def test_campaign_status_values():
    assert CampaignStatus.DRAFT.value == "draft"
    assert CampaignStatus.SCHEDULED.value == "scheduled"
    assert CampaignStatus.SENDING.value == "sending"
    assert CampaignStatus.SENT.value == "sent"
    assert CampaignStatus.PAUSED.value == "paused"
    assert CampaignStatus.CANCELLED.value == "cancelled"


def test_campaign_type_values():
    assert CampaignType.ONE_TIME.value == "one_time"
    assert CampaignType.DRIP.value == "drip"
    assert CampaignType.TRIGGERED.value == "triggered"
    assert CampaignType.AB_TEST.value == "ab_test"


def test_recipient_status_values():
    assert RecipientStatus.PENDING.value == "pending"
    assert RecipientStatus.SENT.value == "sent"
    assert RecipientStatus.BOUNCED.value == "bounced"
    assert RecipientStatus.OPENED.value == "opened"
    assert RecipientStatus.CLICKED.value == "clicked"
    assert RecipientStatus.UNSUBSCRIBED.value == "unsubscribed"
