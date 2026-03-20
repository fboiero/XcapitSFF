"""Tests for rate limiting — token bucket and sliding window algorithms."""

import time
import threading

import pytest

from xcapitsff.core.rate_limiter import (
    DEFAULT_WINDOW_SECONDS,
    PLAN_LIMITS,
    RateLimitResult,
    RatePlan,
    SlidingWindowLimiter,
    TokenBucket,
    TokenBucketLimiter,
    get_default_limiter,
    rate_limit,
    set_default_limiter,
)


# ---------------------------------------------------------------------------
# TokenBucket unit tests
# ---------------------------------------------------------------------------


class TestTokenBucket:
    """Low-level token bucket behaviour."""

    def test_initial_capacity(self):
        bucket = TokenBucket(capacity=10, rate=1.0)
        assert bucket.tokens == pytest.approx(10, abs=1)

    def test_consume_reduces_tokens(self):
        bucket = TokenBucket(capacity=10, rate=1.0)
        result = bucket.consume(1)
        assert result.allowed is True
        assert result.remaining <= 10

    def test_consume_all_tokens(self):
        bucket = TokenBucket(capacity=5, rate=0.0001)  # very slow refill
        for _ in range(5):
            result = bucket.consume(1)
            assert result.allowed is True
        result = bucket.consume(1)
        assert result.allowed is False
        assert result.remaining == 0

    def test_retry_after_positive_when_blocked(self):
        bucket = TokenBucket(capacity=1, rate=0.0001)
        bucket.consume(1)
        result = bucket.consume(1)
        assert result.allowed is False
        assert result.retry_after > 0

    def test_refill_restores_tokens(self):
        bucket = TokenBucket(capacity=10, rate=10_000.0)  # fast refill
        bucket.consume(5)
        time.sleep(0.01)
        assert bucket.tokens >= 5


# ---------------------------------------------------------------------------
# TokenBucketLimiter (per-tenant)
# ---------------------------------------------------------------------------


class TestTokenBucketLimiter:
    """Per-tenant rate limiting with configurable plans."""

    def setup_method(self):
        self.limiter = TokenBucketLimiter(window_seconds=60)

    def test_default_plan_is_free(self):
        result = self.limiter.check("tenant_new")
        assert result.allowed is True
        # Should have created a FREE bucket (100 req/min)

    def test_free_plan_limit(self):
        """FREE plan allows 100 requests per window."""
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 5}, window_seconds=60
        )
        for i in range(5):
            r = lim.check("t1")
            assert r.allowed is True, f"Request {i+1} should be allowed"
        r = lim.check("t1")
        assert r.allowed is False

    def test_pro_plan_higher_limit(self):
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 2, RatePlan.PRO: 10}, window_seconds=60
        )
        lim.set_tenant_plan("t1", RatePlan.PRO)
        for i in range(10):
            r = lim.check("t1")
            assert r.allowed is True, f"Request {i+1} should be allowed"
        r = lim.check("t1")
        assert r.allowed is False

    def test_enterprise_plan_high_limit(self):
        lim = TokenBucketLimiter(
            plan_limits={
                RatePlan.FREE: 2,
                RatePlan.PRO: 5,
                RatePlan.ENTERPRISE: 100,
            },
            window_seconds=60,
        )
        lim.set_tenant_plan("t1", RatePlan.ENTERPRISE)
        for _ in range(100):
            r = lim.check("t1")
            assert r.allowed is True

    def test_different_tenants_independent(self):
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 3}, window_seconds=60
        )
        for _ in range(3):
            lim.check("t1")
        assert lim.check("t1").allowed is False
        # t2 should still be ok
        assert lim.check("t2").allowed is True

    def test_set_tenant_plan_resets_bucket(self):
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 2, RatePlan.PRO: 10}, window_seconds=60
        )
        lim.check("t1")
        lim.check("t1")
        assert lim.check("t1").allowed is False

        lim.set_tenant_plan("t1", RatePlan.PRO)
        assert lim.check("t1").allowed is True

    def test_status_does_not_consume(self):
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 3}, window_seconds=60
        )
        s1 = lim.status("t1")
        s2 = lim.status("t1")
        assert s1.remaining == s2.remaining

    def test_reset_allows_new_requests(self):
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 2}, window_seconds=60
        )
        lim.check("t1")
        lim.check("t1")
        assert lim.check("t1").allowed is False
        lim.reset("t1")
        assert lim.check("t1").allowed is True

    def test_concurrent_access(self):
        """Multiple threads should not corrupt internal state."""
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 200}, window_seconds=60
        )
        results: list[RateLimitResult] = []
        lock = threading.Lock()

        def do_requests():
            for _ in range(50):
                r = lim.check("t1")
                with lock:
                    results.append(r)

        threads = [threading.Thread(target=do_requests) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 200
        allowed = sum(1 for r in results if r.allowed)
        denied = sum(1 for r in results if not r.allowed)
        assert allowed + denied == 200
        assert allowed == 200  # all should be allowed (200 capacity)


# ---------------------------------------------------------------------------
# SlidingWindowLimiter
# ---------------------------------------------------------------------------


class TestSlidingWindowLimiter:
    """Sliding window counter limiter."""

    def test_allows_within_limit(self):
        lim = SlidingWindowLimiter(
            plan_limits={RatePlan.FREE: 5}, window_seconds=60
        )
        for _ in range(5):
            r = lim.check("t1")
            assert r.allowed is True

    def test_blocks_when_exhausted(self):
        lim = SlidingWindowLimiter(
            plan_limits={RatePlan.FREE: 3}, window_seconds=60
        )
        for _ in range(3):
            lim.check("t1")
        r = lim.check("t1")
        assert r.allowed is False
        assert r.remaining == 0
        assert r.retry_after > 0

    def test_window_reset(self):
        """After the window expires, requests are allowed again."""
        lim = SlidingWindowLimiter(
            plan_limits={RatePlan.FREE: 2}, window_seconds=0.05
        )
        lim.check("t1")
        lim.check("t1")
        assert lim.check("t1").allowed is False
        time.sleep(0.06)
        assert lim.check("t1").allowed is True

    def test_status_returns_remaining(self):
        lim = SlidingWindowLimiter(
            plan_limits={RatePlan.FREE: 10}, window_seconds=60
        )
        lim.check("t1")
        lim.check("t1")
        s = lim.status("t1")
        assert s.remaining == 8

    def test_different_plans(self):
        lim = SlidingWindowLimiter(
            plan_limits={RatePlan.FREE: 2, RatePlan.PRO: 100},
            window_seconds=60,
        )
        lim.set_tenant_plan("t1", RatePlan.PRO)
        for _ in range(50):
            assert lim.check("t1").allowed is True

    def test_reset_clears_counter(self):
        lim = SlidingWindowLimiter(
            plan_limits={RatePlan.FREE: 2}, window_seconds=60
        )
        lim.check("t1")
        lim.check("t1")
        assert lim.check("t1").allowed is False
        lim.reset("t1")
        assert lim.check("t1").allowed is True


# ---------------------------------------------------------------------------
# RateLimitResult dataclass
# ---------------------------------------------------------------------------


class TestRateLimitResult:
    """RateLimitResult is a frozen dataclass."""

    def test_fields(self):
        r = RateLimitResult(allowed=True, remaining=99, reset_at=1.0, retry_after=0.0)
        assert r.allowed is True
        assert r.remaining == 99
        assert r.reset_at == 1.0
        assert r.retry_after == 0.0

    def test_immutable(self):
        r = RateLimitResult(allowed=True, remaining=0, reset_at=0.0, retry_after=0.0)
        with pytest.raises(AttributeError):
            r.allowed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Plan limits constants
# ---------------------------------------------------------------------------


class TestPlanLimits:
    def test_free_plan_100(self):
        assert PLAN_LIMITS[RatePlan.FREE] == 100

    def test_pro_plan_1000(self):
        assert PLAN_LIMITS[RatePlan.PRO] == 1_000

    def test_enterprise_plan_10000(self):
        assert PLAN_LIMITS[RatePlan.ENTERPRISE] == 10_000


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


class TestRateLimitDecorator:
    """Test the @rate_limit decorator."""

    def test_sync_function_allowed(self):
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 10}, window_seconds=60
        )

        @rate_limit(limiter=lim)
        def my_func(tenant_id: str = "t1"):
            return {"ok": True}

        result = my_func(tenant_id="t1")
        assert result == {"ok": True}

    def test_sync_function_blocked(self):
        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 1}, window_seconds=60
        )

        @rate_limit(limiter=lim)
        def my_func(tenant_id: str = "t1"):
            return {"ok": True}

        assert my_func(tenant_id="t1") == {"ok": True}
        result = my_func(tenant_id="t1")
        assert result["error"] == "rate_limit_exceeded"
        assert result["retry_after"] > 0

    def test_async_function_allowed(self):
        import asyncio

        lim = TokenBucketLimiter(
            plan_limits={RatePlan.FREE: 10}, window_seconds=60
        )

        @rate_limit(limiter=lim)
        async def my_func(tenant_id: str = "t1"):
            return {"ok": True}

        result = asyncio.run(my_func(tenant_id="t1"))
        assert result == {"ok": True}
