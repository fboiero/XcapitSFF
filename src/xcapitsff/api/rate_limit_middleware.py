"""FastAPI rate-limiting middleware."""

from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from xcapitsff.logging_config import get_logger

from .security import RateLimiter

logger = get_logger(__name__)

# Paths exempt from rate limiting
EXEMPT_PATHS: set[str] = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce per-client rate limits and expose standard rate-limit headers.

    The middleware identifies clients by their IP address (or the
    ``X-Forwarded-For`` header when behind a reverse proxy).

    Exempt endpoints (``/health``, ``/docs``, etc.) are never rate-limited.

    Response headers added on every non-exempt request:
    - ``X-RateLimit-Limit`` — maximum requests in the tightest window
    - ``X-RateLimit-Remaining`` — requests remaining
    - ``X-RateLimit-Reset`` — epoch timestamp when the window resets

    Returns **429 Too Many Requests** when the limit is exceeded.
    """

    def __init__(self, app, limiter: RateLimiter | None = None) -> None:  # noqa: ANN001
        super().__init__(app)
        self.limiter = limiter or RateLimiter()

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _client_identifier(request: Request) -> str:
        """Derive a stable identifier from the request (IP or forwarded IP)."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in the chain is the original client
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    @staticmethod
    def _is_exempt(path: str) -> bool:
        """Return True if the path should skip rate limiting."""
        return path in EXEMPT_PATHS

    # -- dispatch -----------------------------------------------------------

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        if self._is_exempt(path):
            return await call_next(request)

        identifier = self._client_identifier(request)
        allowed, info = self.limiter.check_rate_limit(identifier)

        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s on %s %s",
                identifier,
                request.method,
                path,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": "Rate limit exceeded. Please retry later.",
                    "retry_after": info["retry_after"],
                },
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(info["reset_at"])),
                    "Retry-After": str(int(info["retry_after"])),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(info["reset_at"]))
        return response
