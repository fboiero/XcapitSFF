"""Rate limiting — token bucket and sliding window algorithms.

Provides in-memory, per-tenant rate limiting with configurable plans.
No external dependencies (Redis, etc.) required.
"""

from __future__ import annotations

import functools
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Plan tiers and their request-per-minute limits
# ---------------------------------------------------------------------------


class RatePlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_LIMITS: dict[RatePlan, int] = {
    RatePlan.FREE: 100,
    RatePlan.PRO: 1_000,
    RatePlan.ENTERPRISE: 10_000,
}

DEFAULT_WINDOW_SECONDS = 60


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate-limit check."""

    allowed: bool
    remaining: int
    reset_at: float  # Unix timestamp when the window/bucket resets
    retry_after: float  # Seconds until next request is allowed (0 if allowed)


# ---------------------------------------------------------------------------
# Token Bucket
# ---------------------------------------------------------------------------


class TokenBucket:
    """Classic token bucket algorithm.

    Tokens refill at *rate* tokens per second up to *capacity*.
    Thread-safe via a lock per bucket.
    """

    def __init__(self, capacity: int, rate: float) -> None:
        self.capacity = capacity
        self.rate = rate  # tokens per second
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> RateLimitResult:
        with self._lock:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                remaining = int(self._tokens)
                reset_at = time.time() + (self.capacity - self._tokens) / self.rate
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_at=reset_at,
                    retry_after=0.0,
                )
            else:
                deficit = tokens - self._tokens
                retry_after = deficit / self.rate
                reset_at = time.time() + retry_after
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                )

    @property
    def tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens


# ---------------------------------------------------------------------------
# Token Bucket Rate Limiter (per-tenant)
# ---------------------------------------------------------------------------


class TokenBucketLimiter:
    """Manages one :class:`TokenBucket` per tenant.

    Parameters
    ----------
    plan_limits : dict mapping RatePlan → requests per minute
    window_seconds : bucket refill window in seconds (default 60)
    """

    def __init__(
        self,
        plan_limits: dict[RatePlan, int] | None = None,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._plan_limits = plan_limits or PLAN_LIMITS
        self._window = window_seconds
        self._buckets: dict[str, TokenBucket] = {}
        self._tenant_plans: dict[str, RatePlan] = {}
        self._lock = threading.Lock()

    def set_tenant_plan(self, tenant_id: str, plan: RatePlan) -> None:
        with self._lock:
            self._tenant_plans[tenant_id] = plan
            # Reset bucket if plan changes
            self._buckets.pop(tenant_id, None)

    def _get_bucket(self, tenant_id: str) -> TokenBucket:
        with self._lock:
            if tenant_id not in self._buckets:
                plan = self._tenant_plans.get(tenant_id, RatePlan.FREE)
                capacity = self._plan_limits[plan]
                rate = capacity / self._window  # tokens per second
                self._buckets[tenant_id] = TokenBucket(capacity=capacity, rate=rate)
            return self._buckets[tenant_id]

    def check(self, tenant_id: str, tokens: int = 1) -> RateLimitResult:
        bucket = self._get_bucket(tenant_id)
        return bucket.consume(tokens)

    def status(self, tenant_id: str) -> RateLimitResult:
        """Return current status *without* consuming a token."""
        bucket = self._get_bucket(tenant_id)
        remaining = int(bucket.tokens)
        plan = self._tenant_plans.get(tenant_id, RatePlan.FREE)
        capacity = self._plan_limits[plan]
        reset_at = time.time() + self._window
        return RateLimitResult(
            allowed=remaining > 0,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=0.0 if remaining > 0 else self._window,
        )

    def reset(self, tenant_id: str) -> None:
        """Remove a tenant's bucket so it gets re-created on next check."""
        with self._lock:
            self._buckets.pop(tenant_id, None)


# ---------------------------------------------------------------------------
# Sliding Window Counter
# ---------------------------------------------------------------------------


@dataclass
class _WindowEntry:
    count: int = 0
    window_start: float = 0.0


class SlidingWindowLimiter:
    """Fixed-window counter with sliding semantics.

    Simpler than token bucket — counts requests in fixed windows of
    *window_seconds* and rejects when the count exceeds the limit.
    """

    def __init__(
        self,
        plan_limits: dict[RatePlan, int] | None = None,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self._plan_limits = plan_limits or PLAN_LIMITS
        self._window = window_seconds
        self._counters: dict[str, _WindowEntry] = {}
        self._tenant_plans: dict[str, RatePlan] = {}
        self._lock = threading.Lock()

    def set_tenant_plan(self, tenant_id: str, plan: RatePlan) -> None:
        with self._lock:
            self._tenant_plans[tenant_id] = plan
            self._counters.pop(tenant_id, None)

    def _get_entry(self, tenant_id: str) -> _WindowEntry:
        now = time.monotonic()
        entry = self._counters.get(tenant_id)
        if entry is None or (now - entry.window_start) >= self._window:
            entry = _WindowEntry(count=0, window_start=now)
            self._counters[tenant_id] = entry
        return entry

    def check(self, tenant_id: str, tokens: int = 1) -> RateLimitResult:
        with self._lock:
            entry = self._get_entry(tenant_id)
            plan = self._tenant_plans.get(tenant_id, RatePlan.FREE)
            limit = self._plan_limits[plan]
            elapsed = time.monotonic() - entry.window_start
            reset_at = time.time() + (self._window - elapsed)

            if entry.count + tokens <= limit:
                entry.count += tokens
                remaining = limit - entry.count
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_at=reset_at,
                    retry_after=0.0,
                )
            else:
                retry_after = self._window - elapsed
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=max(retry_after, 0.0),
                )

    def status(self, tenant_id: str) -> RateLimitResult:
        """Return current window status without consuming a token."""
        with self._lock:
            entry = self._get_entry(tenant_id)
            plan = self._tenant_plans.get(tenant_id, RatePlan.FREE)
            limit = self._plan_limits[plan]
            remaining = max(limit - entry.count, 0)
            elapsed = time.monotonic() - entry.window_start
            reset_at = time.time() + (self._window - elapsed)
            return RateLimitResult(
                allowed=remaining > 0,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=0.0 if remaining > 0 else (self._window - elapsed),
            )

    def reset(self, tenant_id: str) -> None:
        with self._lock:
            self._counters.pop(tenant_id, None)


# ---------------------------------------------------------------------------
# Shared default limiter instance
# ---------------------------------------------------------------------------

_default_limiter: TokenBucketLimiter | None = None
_default_lock = threading.Lock()


def get_default_limiter() -> TokenBucketLimiter:
    """Return (and lazily create) the global default rate limiter."""
    global _default_limiter
    if _default_limiter is None:
        with _default_lock:
            if _default_limiter is None:
                _default_limiter = TokenBucketLimiter()
    return _default_limiter


def set_default_limiter(limiter: TokenBucketLimiter) -> None:
    """Replace the global default rate limiter (useful for testing)."""
    global _default_limiter
    _default_limiter = limiter


# ---------------------------------------------------------------------------
# Decorator for easy endpoint rate limiting
# ---------------------------------------------------------------------------


def rate_limit(
    tenant_id_param: str = "tenant_id",
    limiter: TokenBucketLimiter | None = None,
) -> Callable:
    """Decorator that enforces rate limiting on a function.

    The decorated function must accept a keyword argument whose name
    matches *tenant_id_param* (default ``"tenant_id"``).

    Returns a :class:`RateLimitResult` with ``allowed=False`` when the
    limit is exceeded, instead of calling the wrapped function.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _limiter = limiter or get_default_limiter()
            tid = kwargs.get(tenant_id_param, "anonymous")
            result = _limiter.check(str(tid))
            if not result.allowed:
                return {
                    "error": "rate_limit_exceeded",
                    "retry_after": result.retry_after,
                    "reset_at": result.reset_at,
                }
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            _limiter = limiter or get_default_limiter()
            tid = kwargs.get(tenant_id_param, "anonymous")
            result = _limiter.check(str(tid))
            if not result.allowed:
                return {
                    "error": "rate_limit_exceeded",
                    "retry_after": result.retry_after,
                    "reset_at": result.reset_at,
                }
            return await fn(*args, **kwargs)

        import inspect

        if inspect.iscoroutinefunction(fn):
            return async_wrapper
        return wrapper

    return decorator
