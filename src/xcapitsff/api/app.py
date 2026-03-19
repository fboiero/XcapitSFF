"""FastAPI application — entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from xcapitsff.config import settings
from xcapitsff.core.database import async_session, init_db
from xcapitsff.logging_config import get_logger, setup_logging

from .ab_testing_api import router as ab_testing_router
from .agent_runner_api import router as agent_runner_router
from .auth_api import router as auth_router
from .billing_api import router as billing_router
from .onboarding_api import router as onboarding_router
from .tenant_api import router as tenant_router
from .agents_api import router as agents_router
from .discovery_api import router as discovery_router
from .automation_api import router as automation_router
from .analytics import router as analytics_router
from .audit_api import router as audit_router
from .batch_api import router as batch_router
from .campaigns_api import router as campaigns_router
from .contracts_api import router as contracts_router
from .crm_api import router as crm_router
from .custom_fields_api import fields_router as custom_fields_router
from .custom_fields_api import tags_router as tags_router
from .customer360_api import router as customer360_router
from .customers import router as customers_router
from .dashboard import router as dashboard_router
from .data_quality_api import router as data_quality_router
from .enrichment_api import router as enrichment_router
from .export_api import router as export_router
from .kanban_api import router as kanban_router
from .meetings_api import router as meetings_router
from .knowledge import router as knowledge_router
from .leaderboard_api import router as leaderboard_router
from .lifecycle_api import router as lifecycle_router
from .leads import router as leads_router
from .metrics_api import router as metrics_router
from .middleware import ErrorHandlerMiddleware, LoggingMiddleware, RequestIDMiddleware
from .security import SecurityHeaders
from .notifications_api import router as notifications_router
from .outreach_api import router as outreach_router
from .predictions_api import router as predictions_router
from .project_api import router as project_router
from .public_api import router as public_router
from .quickstart_api import router as quickstart_router
from .reports_api import router as reports_router
from .scheduler_api import router as scheduler_router
from .search_api import router as search_router
from .sequences_api import (
    enrollments_router as sequences_enrollments_router,
    leads_sequences_router,
    router as sequences_router,
)
from .system import router as system_router
from .templates_api import router as templates_router
from .tickets import router as tickets_router
from .inbox_api import router as inbox_router
from .webhooks import router as webhooks_router
from .playground_api import router as playground_router
from .wizard_api import router as wizard_router
from .web import router as web_router
from .assistant_api import router as assistant_router
from .workflow_api import router as workflow_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(level=settings.log_level, environment=settings.environment)
    logger.info("Starting XcapitSFF (env=%s)", settings.environment)
    await init_db()
    logger.info("Database initialised")
    from xcapitsff.core.notifications import setup_notifications
    setup_notifications()
    logger.info("Notification system active")
    from xcapitsff.core.events import event_bus
    from xcapitsff.core.metrics import setup_metrics_event_handlers
    setup_metrics_event_handlers(event_bus)
    logger.info("Metrics event handlers active")
    from xcapitsff.core.activity import activity_feed, setup_activity_feed
    setup_activity_feed(event_bus, activity_feed)
    logger.info("Activity feed active")
    yield
    logger.info("Shutting down XcapitSFF")


app = FastAPI(
    title="XcapitSFF",
    description="Xcapit Software Factory — AI-powered Development, Sales & Support",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Middleware (order matters: outermost is added last) ---
# ErrorHandler wraps everything, then logging, then request-id is innermost.
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeaders)

# --- Routers ---
app.include_router(leads_router, prefix="/api/v1")
app.include_router(tickets_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(customer360_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(data_quality_router, prefix="/api/v1")
app.include_router(outreach_router, prefix="/api/v1")
app.include_router(export_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(lifecycle_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(batch_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(leaderboard_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(agent_runner_router, prefix="/api/v1")
app.include_router(automation_router, prefix="/api/v1")
app.include_router(enrichment_router, prefix="/api/v1")
app.include_router(sequences_router, prefix="/api/v1")
app.include_router(sequences_enrollments_router, prefix="/api/v1")
app.include_router(leads_sequences_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(ab_testing_router, prefix="/api/v1")
app.include_router(crm_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(onboarding_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(discovery_router, prefix="/api/v1")
app.include_router(project_router, prefix="/api/v1")
app.include_router(contracts_router, prefix="/api/v1")
app.include_router(kanban_router, prefix="/api/v1")
app.include_router(meetings_router, prefix="/api/v1")
app.include_router(public_router, prefix="/api/v1")
app.include_router(quickstart_router, prefix="/api/v1")
app.include_router(playground_router, prefix="/api/v1")
app.include_router(wizard_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(custom_fields_router, prefix="/api/v1")
app.include_router(tags_router, prefix="/api/v1")
app.include_router(inbox_router, prefix="/api/v1")
app.include_router(assistant_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")

# --- Web Dashboard (served at root, no /api/v1 prefix) ---
app.include_router(web_router)


# --- Health endpoints ---


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "factory": "XcapitSFF"}


@app.get("/api/v1/health")
async def health_with_db():
    """Extended health check that verifies database connectivity."""
    db_ok = False
    db_error = None

    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as exc:
        db_error = str(exc)
        logger.error("Health check DB failure: %s", db_error)

    status = "ok" if db_ok else "degraded"
    result: dict = {
        "status": status,
        "version": "0.1.0",
        "factory": "XcapitSFF",
        "checks": {
            "database": "ok" if db_ok else "error",
        },
    }

    if db_error:
        result["checks"]["database_error"] = db_error

    status_code = 200 if db_ok else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(content=result, status_code=status_code)
