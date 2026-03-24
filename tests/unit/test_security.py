"""Tests for API security: rate limiting, API key auth, and security headers."""

import os
import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from xcapitsff.api.rate_limit_middleware import RateLimitMiddleware
from xcapitsff.api.security import APIKeyAuth, RateLimiter, SecurityHeaders


# ===================================================================
# Rate Limiter
# ===================================================================


class TestRateLimiterWithinLimit:
    """Requests that stay within the configured window."""

    def test_single_request_allowed(self):
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)
        allowed, info = limiter.check_rate_limit("client-1")
        assert allowed is True
        assert info["remaining"] >= 9  # may be 9 or 10 depending on count timing
        assert info["limit"] == 10

    def test_multiple_requests_within_limit(self):
        limiter = RateLimiter(requests_per_minute=5, requests_per_hour=100)
        for i in range(5):
            allowed, info = limiter.check_rate_limit("client-1")
            assert allowed is True
        # After 5 requests, remaining should be low (0 or 1 depending on timing)
        assert info["remaining"] <= 1

    def test_info_contains_reset_at(self):
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)
        _, info = limiter.check_rate_limit("client-1")
        assert "reset_at" in info
        assert info["reset_at"] > time.time()


class TestRateLimiterExceeded:
    """Requests that exceed the configured window."""

    def test_minute_limit_exceeded(self):
        limiter = RateLimiter(requests_per_minute=3, requests_per_hour=1000)
        for _ in range(3):
            allowed, _ = limiter.check_rate_limit("client-1")
            assert allowed is True

        allowed, info = limiter.check_rate_limit("client-1")
        assert allowed is False
        assert info["remaining"] == 0
        assert info["retry_after"] > 0

    def test_hour_limit_exceeded(self):
        limiter = RateLimiter(requests_per_minute=100, requests_per_hour=5)
        for _ in range(5):
            allowed, _ = limiter.check_rate_limit("client-1")
            assert allowed is True

        allowed, info = limiter.check_rate_limit("client-1")
        assert allowed is False
        assert info["remaining"] == 0

    def test_exceeded_does_not_record_request(self):
        """When rate-limited, the rejected request should NOT be recorded."""
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=100)
        limiter.check_rate_limit("c1")
        limiter.check_rate_limit("c1")

        # 3rd is rejected
        allowed, _ = limiter.check_rate_limit("c1")
        assert allowed is False

        # Internal count should still be 2
        assert len(limiter._requests["c1"]) == 2


class TestRateLimiterWindowReset:
    """Sliding window expiration."""

    def test_window_resets_after_expiry(self):
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=1000)

        limiter.check_rate_limit("c1")
        limiter.check_rate_limit("c1")

        # Simulate time passing beyond the 60-second window
        now = time.time()
        limiter._requests["c1"] = [now - 61, now - 61]

        allowed, info = limiter.check_rate_limit("c1")
        assert allowed is True
        assert info["remaining"] >= 1


class TestRateLimiterMultipleIdentifiers:
    """Independent tracking per identifier."""

    def test_separate_identifiers_are_independent(self):
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=100)

        limiter.check_rate_limit("alice")
        limiter.check_rate_limit("alice")
        allowed_alice, _ = limiter.check_rate_limit("alice")
        assert allowed_alice is False

        # Bob should still be fine
        allowed_bob, info = limiter.check_rate_limit("bob")
        assert allowed_bob is True
        assert info["remaining"] >= 1

    def test_reset_single_identifier(self):
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=100)
        limiter.check_rate_limit("alice")
        limiter.check_rate_limit("alice")

        limiter.reset("alice")
        allowed, info = limiter.check_rate_limit("alice")
        assert allowed is True
        assert info["remaining"] >= 1

    def test_reset_all(self):
        limiter = RateLimiter(requests_per_minute=1, requests_per_hour=100)
        limiter.check_rate_limit("alice")
        limiter.check_rate_limit("bob")

        limiter.reset()

        allowed_alice, _ = limiter.check_rate_limit("alice")
        allowed_bob, _ = limiter.check_rate_limit("bob")
        assert allowed_alice is True
        assert allowed_bob is True


# ===================================================================
# API Key Authentication
# ===================================================================


class TestAPIKeyAuthValid:
    """Valid key scenarios."""

    def test_valid_key_returns_client_name(self):
        auth = APIKeyAuth(keys={"secret-123": "frontend"})
        valid, name = auth.validate_key("secret-123")
        assert valid is True
        assert name == "frontend"

    def test_multiple_keys(self):
        auth = APIKeyAuth(keys={"k1": "app1", "k2": "app2"})
        v1, n1 = auth.validate_key("k1")
        v2, n2 = auth.validate_key("k2")
        assert v1 and n1 == "app1"
        assert v2 and n2 == "app2"

    def test_keys_from_env_var(self):
        with patch.dict(os.environ, {"API_KEYS": "envkey1:web,envkey2:mobile"}):
            auth = APIKeyAuth()
            valid, name = auth.validate_key("envkey1")
            assert valid is True
            assert name == "web"
            assert auth.registered_key_count == 2

    def test_env_keys_merged_with_init_keys(self):
        with patch.dict(os.environ, {"API_KEYS": "envkey:env_client"}):
            auth = APIKeyAuth(keys={"initkey": "init_client"})
            v1, n1 = auth.validate_key("initkey")
            v2, n2 = auth.validate_key("envkey")
            assert v1 and n1 == "init_client"
            assert v2 and n2 == "env_client"


class TestAPIKeyAuthInvalid:
    """Invalid / missing key scenarios."""

    def test_invalid_key(self):
        auth = APIKeyAuth(keys={"real-key": "client"})
        valid, name = auth.validate_key("wrong-key")
        assert valid is False
        assert name == ""

    def test_empty_key(self):
        auth = APIKeyAuth(keys={"real-key": "client"})
        valid, name = auth.validate_key("")
        assert valid is False
        assert name == ""

    def test_no_keys_registered(self):
        with patch.dict(os.environ, {}, clear=True):
            # Remove API_KEYS if present
            os.environ.pop("API_KEYS", None)
            auth = APIKeyAuth()
            valid, name = auth.validate_key("anything")
            assert valid is False
            assert auth.registered_key_count == 0


# ===================================================================
# Security Headers Middleware
# ===================================================================


def _make_app_with_security_headers() -> FastAPI:
    """Create a minimal FastAPI app with SecurityHeaders middleware."""
    app = FastAPI()
    app.add_middleware(SecurityHeaders)

    @app.get("/test")
    async def _test_route():
        return {"ok": True}

    return app


class TestSecurityHeaders:
    """SecurityHeaders middleware injects the correct headers."""

    def test_all_security_headers_present(self):
        app = _make_app_with_security_headers()
        client = TestClient(app)
        response = client.get("/test")

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    def test_security_headers_on_error_route(self):
        """Headers should appear even when the route returns an error status."""
        app = FastAPI()
        app.add_middleware(SecurityHeaders)

        @app.get("/fail")
        async def _fail():
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=400, content={"error": "bad"})

        client = TestClient(app)
        response = client.get("/fail")
        assert response.status_code == 400
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"


# ===================================================================
# Rate Limit Middleware (integration-style)
# ===================================================================


def _make_app_with_rate_limit(limiter: RateLimiter | None = None) -> FastAPI:
    """Create a minimal FastAPI app with RateLimitMiddleware."""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, limiter=limiter)

    @app.get("/api/v1/data")
    async def _data():
        return {"data": "value"}

    @app.get("/health")
    async def _health():
        return {"status": "ok"}

    return app


class TestRateLimitMiddleware:
    """Integration tests for the rate-limit middleware."""

    def test_rate_limit_headers_present(self):
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)
        app = _make_app_with_rate_limit(limiter)
        client = TestClient(app)

        response = client.get("/api/v1/data")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_returns_429_when_exceeded(self):
        limiter = RateLimiter(requests_per_minute=2, requests_per_hour=100)
        app = _make_app_with_rate_limit(limiter)
        client = TestClient(app)

        client.get("/api/v1/data")
        client.get("/api/v1/data")
        response = client.get("/api/v1/data")

        assert response.status_code == 429
        body = response.json()
        assert body["error"] == "Too Many Requests"
        assert "Retry-After" in response.headers

    def test_health_endpoint_exempt(self):
        limiter = RateLimiter(requests_per_minute=1, requests_per_hour=1)
        app = _make_app_with_rate_limit(limiter)
        client = TestClient(app)

        # Exhaust the limit on a normal route
        client.get("/api/v1/data")

        # Health should still work
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200

    def test_health_has_no_rate_limit_headers(self):
        limiter = RateLimiter(requests_per_minute=10, requests_per_hour=100)
        app = _make_app_with_rate_limit(limiter)
        client = TestClient(app)

        response = client.get("/health")
        assert "X-RateLimit-Limit" not in response.headers
