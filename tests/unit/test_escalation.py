"""Tests for escalation workflow engine."""

import pytest

from xcapitsff.support.escalation import (
    EscalationEngine,
    EscalationLevel,
    EscalationReason,
)


@pytest.fixture
def engine():
    return EscalationEngine()


def test_default_level_is_l1(engine):
    assert engine.get_current_level(1) == EscalationLevel.L1


@pytest.mark.asyncio
async def test_escalate_l1_to_l2(engine):
    action = await engine.escalate(1, EscalationReason.SLA_BREACH)
    assert action is not None
    assert action.from_level == EscalationLevel.L1
    assert action.to_level == EscalationLevel.L2
    assert engine.get_current_level(1) == EscalationLevel.L2


@pytest.mark.asyncio
async def test_escalate_to_l3(engine):
    await engine.escalate(1, EscalationReason.SLA_BREACH)
    action = await engine.escalate(1, EscalationReason.CUSTOMER_DISSATISFIED)
    assert action.to_level == EscalationLevel.L3


@pytest.mark.asyncio
async def test_escalate_to_l4(engine):
    await engine.escalate(1, EscalationReason.SLA_BREACH)
    await engine.escalate(1, EscalationReason.SLA_BREACH)
    action = await engine.escalate(1, EscalationReason.FINANCIAL_RISK)
    assert action.to_level == EscalationLevel.L4


@pytest.mark.asyncio
async def test_cannot_escalate_beyond_l4(engine):
    for _ in range(3):
        await engine.escalate(1, EscalationReason.SLA_BREACH)
    # Now at L4
    action = await engine.escalate(1, EscalationReason.SLA_BREACH)
    assert action is None


def test_should_auto_escalate_timeout(engine):
    should, reason = engine.should_auto_escalate(1, age_minutes=120, interactions_without_resolution=0)
    assert should is True
    assert reason == EscalationReason.SLA_BREACH


def test_should_auto_escalate_repeated(engine):
    should, reason = engine.should_auto_escalate(1, age_minutes=10, interactions_without_resolution=3)
    assert should is True
    assert reason == EscalationReason.REPEATED_CONTACT


def test_should_not_escalate_fresh(engine):
    should, _ = engine.should_auto_escalate(1, age_minutes=5, interactions_without_resolution=0)
    assert should is False


@pytest.mark.asyncio
async def test_history(engine):
    await engine.escalate(1, EscalationReason.SLA_BREACH)
    await engine.escalate(2, EscalationReason.SECURITY_ISSUE)

    all_history = engine.get_history()
    assert len(all_history) == 2

    ticket1_history = engine.get_history(ticket_id=1)
    assert len(ticket1_history) == 1


@pytest.mark.asyncio
async def test_stats(engine):
    await engine.escalate(1, EscalationReason.SLA_BREACH)
    await engine.escalate(2, EscalationReason.FINANCIAL_RISK)

    stats = engine.get_stats()
    assert stats["total_escalations"] == 2
    assert stats["by_level"]["L2"] == 2
    assert stats["auto"] == 2


@pytest.mark.asyncio
async def test_manual_escalation(engine):
    action = await engine.escalate(1, EscalationReason.MANUAL, notes="Customer requested", auto=False)
    assert action.auto is False
    stats = engine.get_stats()
    assert stats["manual"] == 1
