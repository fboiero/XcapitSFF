"""Retry and error recovery — resilient execution for critical operations.

Provides retry with exponential backoff, dead letter queue for failed
operations, and circuit breaker pattern for external dependencies.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"  # normal operation
    OPEN = "open"  # failing, reject calls
    HALF_OPEN = "half_open"  # testing if recovered


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_errors: tuple = (Exception,)


@dataclass
class DeadLetterEntry:
    entry_id: str
    operation: str
    payload: dict
    error: str
    retries_exhausted: int
    failed_at: datetime = field(default_factory=datetime.now)
    resolved: bool = False


class DeadLetterQueue:
    """Stores failed operations for manual review or retry."""

    def __init__(self):
        self._entries: list[DeadLetterEntry] = []
        self._counter = 0

    def add(self, operation: str, payload: dict, error: str, retries: int) -> DeadLetterEntry:
        self._counter += 1
        entry = DeadLetterEntry(
            entry_id=f"DLQ-{self._counter:06d}",
            operation=operation,
            payload=payload,
            error=error,
            retries_exhausted=retries,
        )
        self._entries.append(entry)
        logger.warning(f"Dead letter: {entry.entry_id} — {operation}: {error}")
        return entry

    def get_pending(self) -> list[DeadLetterEntry]:
        return [e for e in self._entries if not e.resolved]

    def resolve(self, entry_id: str) -> bool:
        for e in self._entries:
            if e.entry_id == entry_id:
                e.resolved = True
                return True
        return False

    def get_stats(self) -> dict:
        pending = len([e for e in self._entries if not e.resolved])
        resolved = len([e for e in self._entries if e.resolved])
        return {"total": len(self._entries), "pending": pending, "resolved": resolved}


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure: float = 0
        self._success_count = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self._last_failure >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN — allow one attempt
        return True

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self._failure_count = 0
        self._success_count += 1

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure = time.time()
        if self._failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' OPEN after {self._failure_count} failures")

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self._failure_count,
            "successes": self._success_count,
            "threshold": self.failure_threshold,
        }


async def retry_async(
    func: Callable[..., Coroutine],
    *args: Any,
    config: RetryConfig | None = None,
    operation_name: str = "unknown",
    dlq: DeadLetterQueue | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry and exponential backoff."""
    cfg = config or RetryConfig()

    last_error = None
    for attempt in range(cfg.max_retries + 1):
        try:
            result = await func(*args, **kwargs)
            return result
        except cfg.retryable_errors as e:
            last_error = e
            if attempt < cfg.max_retries:
                delay = min(
                    cfg.base_delay * (cfg.exponential_base ** attempt),
                    cfg.max_delay,
                )
                logger.warning(
                    f"Retry {attempt + 1}/{cfg.max_retries} for {operation_name}: {e}. "
                    f"Waiting {delay:.1f}s"
                )
                await asyncio.sleep(delay)

    # All retries exhausted
    if dlq:
        dlq.add(
            operation=operation_name,
            payload={"args": str(args)[:200], "kwargs": str(kwargs)[:200]},
            error=str(last_error),
            retries=cfg.max_retries,
        )

    raise last_error


# Singletons
dead_letter_queue = DeadLetterQueue()
