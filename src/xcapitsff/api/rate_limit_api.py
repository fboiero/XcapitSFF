"""API endpoints for rate limiting status."""

from fastapi import APIRouter, Query

from xcapitsff.core.rate_limiter import get_default_limiter

router = APIRouter(prefix="/rate-limit", tags=["Rate Limiting"])


@router.get("/status")
async def get_rate_limit_status(tenant_id: str = Query(default="anonymous")):
    """Return the current rate limit status for the caller/tenant."""
    limiter = get_default_limiter()
    result = limiter.status(tenant_id)
    return {
        "tenant_id": tenant_id,
        "allowed": result.allowed,
        "remaining": result.remaining,
        "reset_at": result.reset_at,
        "retry_after": result.retry_after,
    }
