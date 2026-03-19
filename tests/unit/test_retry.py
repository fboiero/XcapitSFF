"""Tests for retry, circuit breaker, and dead letter queue."""

import pytest

from xcapitsff.core.retry import (
    CircuitBreaker,
    CircuitState,
    DeadLetterQueue,
    RetryConfig,
    retry_async,
)


# --- Dead Letter Queue ---


def test_dlq_add():
    dlq = DeadLetterQueue()
    entry = dlq.add("import_leads", {"file": "test.csv"}, "Connection refused", 3)
    assert entry.entry_id.startswith("DLQ-")
    assert entry.operation == "import_leads"
    assert not entry.resolved


def test_dlq_resolve():
    dlq = DeadLetterQueue()
    entry = dlq.add("op", {}, "err", 1)
    assert dlq.resolve(entry.entry_id) is True
    assert len(dlq.get_pending()) == 0


def test_dlq_stats():
    dlq = DeadLetterQueue()
    dlq.add("a", {}, "e1", 1)
    dlq.add("b", {}, "e2", 2)
    entry = dlq.add("c", {}, "e3", 3)
    dlq.resolve(entry.entry_id)
    stats = dlq.get_stats()
    assert stats["total"] == 3
    assert stats["pending"] == 2
    assert stats["resolved"] == 1


# --- Circuit Breaker ---


def test_circuit_starts_closed():
    cb = CircuitBreaker("test")
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_circuit_opens_after_failures():
    cb = CircuitBreaker("test", failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False


def test_circuit_half_open_after_timeout():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    # With recovery_timeout=0, should immediately go half-open
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_closes_on_success():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.0)
    cb.record_failure()
    cb.record_failure()
    cb.can_execute()  # transitions to HALF_OPEN
    cb.record_success()
    assert cb.state == CircuitState.CLOSED


def test_circuit_status():
    cb = CircuitBreaker("test_service")
    cb.record_success()
    cb.record_success()
    status = cb.get_status()
    assert status["name"] == "test_service"
    assert status["state"] == "closed"
    assert status["successes"] == 2


# --- Retry ---


@pytest.mark.asyncio
async def test_retry_succeeds_first_try():
    call_count = 0

    async def success():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await retry_async(success, config=RetryConfig(max_retries=3, base_delay=0.01))
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    call_count = 0

    async def fail_then_succeed():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("fail")
        return "ok"

    result = await retry_async(
        fail_then_succeed,
        config=RetryConfig(max_retries=5, base_delay=0.01),
    )
    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted_raises():
    async def always_fail():
        raise ConnectionError("always fails")

    with pytest.raises(ConnectionError):
        await retry_async(
            always_fail,
            config=RetryConfig(max_retries=2, base_delay=0.01),
        )


@pytest.mark.asyncio
async def test_retry_adds_to_dlq():
    dlq = DeadLetterQueue()

    async def always_fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await retry_async(
            always_fail,
            config=RetryConfig(max_retries=1, base_delay=0.01),
            operation_name="test_op",
            dlq=dlq,
        )

    pending = dlq.get_pending()
    assert len(pending) == 1
    assert pending[0].operation == "test_op"
