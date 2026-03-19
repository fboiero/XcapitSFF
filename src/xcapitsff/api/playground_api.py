"""API endpoints for Agent Playground and Workspace Health Score."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from xcapitsff.core.database import get_db
from xcapitsff.selfservice.health_score import HealthScoreCalculator
from xcapitsff.selfservice.playground import PlaygroundManager

router = APIRouter(tags=["Playground & Health"])

# Singletons
_playground = PlaygroundManager()
_health_calculator = HealthScoreCalculator()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    agent_role: str


class StartSessionResponse(BaseModel):
    session_id: str
    agent_role: str
    started_at: str


class SendMessageRequest(BaseModel):
    message: str


class SendMessageResponse(BaseModel):
    session_id: str
    response: str


class MessageEntry(BaseModel):
    role: str
    content: str


class SessionDetailResponse(BaseModel):
    session_id: str
    agent_role: str
    messages: list[MessageEntry]
    started_at: str
    last_active: str


class SamplePrompt(BaseModel):
    label: str
    prompt: str


class SamplePromptsResponse(BaseModel):
    agent_role: str
    samples: list[SamplePrompt]


class HealthCheckResponse(BaseModel):
    category: str
    name: str
    score: int
    status: str
    recommendation: str
    weight: float


class WorkspaceHealthResponse(BaseModel):
    overall_score: int
    grade: str
    checks: list[HealthCheckResponse]
    recommendations: list[str]
    last_checked: str


# ---------------------------------------------------------------------------
# Playground endpoints
# ---------------------------------------------------------------------------


@router.post("/playground/start", response_model=StartSessionResponse)
async def start_playground_session(body: StartSessionRequest):
    """Start a new playground session for a given agent role."""
    session = _playground.start_session(body.agent_role)
    return StartSessionResponse(
        session_id=session.session_id,
        agent_role=session.agent_role,
        started_at=session.started_at.isoformat(),
    )


@router.post(
    "/playground/{session_id}/message",
    response_model=SendMessageResponse,
)
async def send_playground_message(session_id: str, body: SendMessageRequest):
    """Send a message to an agent in the playground and get the response."""
    try:
        response = await _playground.send_message(session_id, body.message)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    return SendMessageResponse(
        session_id=session_id,
        response=response,
    )


@router.get(
    "/playground/{session_id}",
    response_model=SessionDetailResponse,
)
async def get_playground_session(session_id: str):
    """Get a playground session with its full message history."""
    try:
        session = _playground.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        session_id=session.session_id,
        agent_role=session.agent_role,
        messages=[
            MessageEntry(role=role, content=content)
            for role, content in session.messages
        ],
        started_at=session.started_at.isoformat(),
        last_active=session.last_active.isoformat(),
    )


@router.get(
    "/playground/samples/{agent_role}",
    response_model=SamplePromptsResponse,
)
async def get_sample_prompts(agent_role: str):
    """Get pre-built sample prompts for a given agent role."""
    samples = PlaygroundManager.get_sample_prompts(agent_role)
    return SamplePromptsResponse(
        agent_role=agent_role,
        samples=[SamplePrompt(**s) for s in samples],
    )


# ---------------------------------------------------------------------------
# Health Score endpoints
# ---------------------------------------------------------------------------


@router.get("/health-score", response_model=WorkspaceHealthResponse)
async def get_health_score(db: AsyncSession = Depends(get_db)):
    """Calculate and return the workspace health score."""
    health = await _health_calculator.calculate_health(db)
    return WorkspaceHealthResponse(
        overall_score=health.overall_score,
        grade=health.grade,
        checks=[
            HealthCheckResponse(
                category=ch.category.value,
                name=ch.name,
                score=ch.score,
                status=ch.status,
                recommendation=ch.recommendation,
                weight=ch.weight,
            )
            for ch in health.checks
        ],
        recommendations=health.recommendations,
        last_checked=health.last_checked.isoformat(),
    )


@router.get("/health-score/checks", response_model=list[HealthCheckResponse])
async def get_health_checks(db: AsyncSession = Depends(get_db)):
    """Return detailed health checks breakdown."""
    health = await _health_calculator.calculate_health(db)
    return [
        HealthCheckResponse(
            category=ch.category.value,
            name=ch.name,
            score=ch.score,
            status=ch.status,
            recommendation=ch.recommendation,
            weight=ch.weight,
        )
        for ch in health.checks
    ]


@router.get("/health-score/recommendations", response_model=list[str])
async def get_health_recommendations(db: AsyncSession = Depends(get_db)):
    """Return actionable recommendations based on workspace health."""
    health = await _health_calculator.calculate_health(db)
    return _health_calculator.get_recommendations(health)
