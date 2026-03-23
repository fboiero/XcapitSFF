"""API security utilities — rate limiting, API key auth, and security headers."""

import os
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from xcapitsff.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Rate Limiter (in-memory, sliding window)
# ---------------------------------------------------------------------------


@dataclass
class RateLimitConfig:
    """Configuration for a single rate-limit window."""

    requests: int
    window_seconds: int


class RateLimiter:
    """In-memory sliding-window rate limiter.

    Tracks request timestamps per identifier (IP or API key) and enforces
    configurable limits per minute and per hour.

    Args:
        requests_per_minute: Maximum requests allowed in a 60-second window.
        requests_per_hour: Maximum requests allowed in a 3600-second window.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ) -> None:
        self.limits: list[RateLimitConfig] = [
            RateLimitConfig(requests=requests_per_minute, window_seconds=60),
            RateLimitConfig(requests=requests_per_hour, window_seconds=3600),
        ]
        # identifier -> list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    # -- internal helpers ---------------------------------------------------

    def _prune(self, identifier: str, now: float) -> None:
        """Remove timestamps older than the largest window."""
        max_window = max(lim.window_seconds for lim in self.limits)
        cutoff = now - max_window
        self._requests[identifier] = [
            ts for ts in self._requests[identifier] if ts > cutoff
        ]

    def _count_in_window(self, identifier: str, now: float, window_seconds: int) -> int:
        """Count requests within *window_seconds* of *now*."""
        cutoff = now - window_seconds
        return sum(1 for ts in self._requests[identifier] if ts > cutoff)

    # -- public API ---------------------------------------------------------

    def check_rate_limit(self, identifier: str) -> tuple[bool, dict]:
        """Check whether *identifier* is within its rate limit.

        Returns:
            A ``(allowed, info)`` tuple where *info* contains:
            - ``remaining``: requests left in the tightest window
            - ``limit``: the limit of the tightest window
            - ``reset_at``: epoch timestamp when the tightest window resets
            - ``retry_after``: seconds until the next request is allowed (0 if allowed)
        """
        now = time.time()
        self._prune(identifier, now)

        # Check each configured limit and find the most restrictive one
        tightest_remaining: int | None = None
        tightest_limit: int = 0
        tightest_reset_at: float = 0.0
        allowed = True

        for limit_cfg in self.limits:
            count = self._count_in_window(identifier, now, limit_cfg.window_seconds)
            remaining = max(0, limit_cfg.requests - count)

            # The window resets relative to the oldest request in the window
            window_cutoff = now - limit_cfg.window_seconds
            timestamps_in_window = [
                ts for ts in self._requests[identifier] if ts > window_cutoff
            ]
            if timestamps_in_window:
                reset_at = timestamps_in_window[0] + limit_cfg.window_seconds
            else:
                reset_at = now + limit_cfg.window_seconds

            if remaining == 0:
                allowed = False

            if tightest_remaining is None or remaining < tightest_remaining:
                tightest_remaining = remaining
                tightest_limit = limit_cfg.requests
                tightest_reset_at = reset_at

        if tightest_remaining is None:
            tightest_remaining = 0

        retry_after = max(0.0, tightest_reset_at - now) if not allowed else 0.0

        info = {
            "remaining": tightest_remaining,
            "limit": tightest_limit,
            "reset_at": tightest_reset_at,
            "retry_after": round(retry_after, 2),
        }

        if allowed:
            self._requests[identifier].append(now)

        return allowed, info

    def reset(self, identifier: str | None = None) -> None:
        """Clear tracked requests for one or all identifiers."""
        if identifier is None:
            self._requests.clear()
        else:
            self._requests.pop(identifier, None)


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------


class APIKeyAuth:
    """Simple API key validator.

    Keys are loaded from *keys* mapping or from the ``API_KEYS`` environment
    variable (comma-separated ``key:client_name`` pairs).

    Example env var::

        API_KEYS=abc123:frontend,xyz789:mobile_app
    """

    def __init__(self, keys: dict[str, str] | None = None) -> None:
        self._keys: dict[str, str] = {}

        if keys:
            self._keys.update(keys)

        # Merge keys from environment variable
        env_keys = os.environ.get("API_KEYS", "")
        if env_keys:
            for pair in env_keys.split(","):
                pair = pair.strip()
                if ":" in pair:
                    key, client_name = pair.split(":", maxsplit=1)
                    self._keys[key.strip()] = client_name.strip()

    def validate_key(self, key: str) -> tuple[bool, str]:
        """Validate an API key.

        Returns:
            A ``(valid, client_name)`` tuple.  *client_name* is an empty
            string when the key is invalid.
        """
        if not key:
            return False, ""
        client_name = self._keys.get(key, "")
        if client_name:
            return True, client_name
        return False, ""

    @property
    def registered_key_count(self) -> int:
        """Number of registered API keys."""
        return len(self._keys)


# ---------------------------------------------------------------------------
# Security Headers Middleware
# ---------------------------------------------------------------------------


class SecurityHeaders(BaseHTTPMiddleware):
    """Add standard security headers to every response.

    Headers added:
    - ``X-Content-Type-Options: nosniff``
    - ``X-Frame-Options: DENY``
    - ``X-XSS-Protection: 1; mode=block``
    - ``Strict-Transport-Security: max-age=31536000; includeSubDomains``
    - ``Content-Security-Policy: default-src 'self'``
    """

    SECURITY_HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        ),
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header, value in self.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
