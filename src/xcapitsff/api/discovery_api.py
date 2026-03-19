"""API endpoints para el sistema de Product Discovery y Requerimientos."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from xcapitsff.discovery.session import DiscoveryEngine
from xcapitsff.discovery.requirements import RequirementsGenerator
from xcapitsff.discovery.proposal import ProposalGenerator

router = APIRouter(prefix="/discovery", tags=["Discovery"])

# ---------------------------------------------------------------------------
# Estado compartido (en producción reemplazado por DB / DI)
# ---------------------------------------------------------------------------

_engine = DiscoveryEngine()
_req_generator = RequirementsGenerator()
_proposal_generator = ProposalGenerator()

# Cache de documentos generados
_requirements_cache: dict[str, object] = {}
_proposal_cache: dict[str, object] = {}


# ---------------------------------------------------------------------------
# Modelos de request / response
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    client_name: str
    client_email: EmailStr


class StartSessionResponse(BaseModel):
    session_id: str
    client_name: str
    client_email: str
    current_phase: str
    status: str


class SessionDetailResponse(BaseModel):
    session_id: str
    client_name: str
    client_email: str
    industry: str
    current_phase: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    answers_count: int
    completion_percentage: float


class SessionListResponse(BaseModel):
    sessions: list[SessionDetailResponse]
    total: int


class QuestionResponse(BaseModel):
    question_id: str
    phase: str
    question_text: str
    follow_ups: list[str]
    required: bool
    answer_type: str
    answered: bool
    current_answer: Optional[str] = None


class QuestionsListResponse(BaseModel):
    session_id: str
    current_phase: str
    questions: list[QuestionResponse]


class AnswerRequest(BaseModel):
    question_id: str
    answer: str
    notes: str = ""


class AnswerResponse(BaseModel):
    question_id: str
    phase: str
    answer: str
    notes: str
    answered_at: str


class AdvancePhaseResponse(BaseModel):
    session_id: str
    previous_phase: str
    current_phase: str


class SummaryResponse(BaseModel):
    session_id: str
    client_name: str
    client_email: str
    industry: str
    status: str
    current_phase: str
    completion_percentage: float
    phases: dict


class CompleteSessionResponse(BaseModel):
    session_id: str
    status: str
    completed_at: str


class GenerateRequirementsResponse(BaseModel):
    doc_id: str
    client_name: str
    session_id: str
    requirements_count: int
    user_stories_count: int
    non_functional_count: int
    constraints: list[str]
    assumptions: list[str]
    out_of_scope: list[str]
    effort_estimate: dict


class GenerateProposalResponse(BaseModel):
    proposal_id: str
    client_name: str
    executive_summary: str
    recommended_plan: str
    modules_included: list[str]
    timeline: str
    investment: dict
    phases_count: int


class MarkdownResponse(BaseModel):
    proposal_id: str
    markdown: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sessions", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """Inicia una nueva sesión de descubrimiento con un cliente."""
    session = _engine.start_session(request.client_name, request.client_email)
    return StartSessionResponse(
        session_id=session.session_id,
        client_name=session.client_name,
        client_email=session.client_email,
        current_phase=session.current_phase.value,
        status=session.status.value,
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    """Lista todas las sesiones de descubrimiento."""
    sessions = _engine.list_sessions()
    items = []
    for s in sessions:
        completion = _engine.get_completion_percentage(s.session_id)
        items.append(
            SessionDetailResponse(
                session_id=s.session_id,
                client_name=s.client_name,
                client_email=s.client_email,
                industry=s.industry,
                current_phase=s.current_phase.value,
                status=s.status.value,
                started_at=s.started_at.isoformat(),
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
                answers_count=len(s.answers),
                completion_percentage=completion,
            )
        )
    return SessionListResponse(sessions=items, total=len(items))


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """Obtiene el detalle de una sesión de descubrimiento."""
    try:
        s = _engine.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    completion = _engine.get_completion_percentage(session_id)
    return SessionDetailResponse(
        session_id=s.session_id,
        client_name=s.client_name,
        client_email=s.client_email,
        industry=s.industry,
        current_phase=s.current_phase.value,
        status=s.status.value,
        started_at=s.started_at.isoformat(),
        completed_at=s.completed_at.isoformat() if s.completed_at else None,
        answers_count=len(s.answers),
        completion_percentage=completion,
    )


@router.get("/sessions/{session_id}/questions", response_model=QuestionsListResponse)
async def get_current_questions(session_id: str):
    """Obtiene las preguntas de la fase actual de la sesión."""
    try:
        session = _engine.get_session(session_id)
        questions = _engine.get_current_questions(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    answered_ids = {a.question_id: a.answer for a in session.answers}

    items = []
    for q in questions:
        is_answered = q.question_id in answered_ids
        items.append(
            QuestionResponse(
                question_id=q.question_id,
                phase=q.phase.value,
                question_text=q.question_text,
                follow_ups=q.follow_ups,
                required=q.required,
                answer_type=q.answer_type.value,
                answered=is_answered,
                current_answer=answered_ids.get(q.question_id),
            )
        )

    return QuestionsListResponse(
        session_id=session_id,
        current_phase=session.current_phase.value,
        questions=items,
    )


@router.post("/sessions/{session_id}/answer", response_model=AnswerResponse)
async def answer_question(session_id: str, request: AnswerRequest):
    """Registra una respuesta a una pregunta de descubrimiento."""
    try:
        answer = _engine.answer_question(
            session_id, request.question_id, request.answer, request.notes
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AnswerResponse(
        question_id=answer.question_id,
        phase=answer.phase.value,
        answer=answer.answer,
        notes=answer.notes,
        answered_at=answer.answered_at.isoformat(),
    )


@router.post("/sessions/{session_id}/advance", response_model=AdvancePhaseResponse)
async def advance_phase(session_id: str):
    """Avanza a la siguiente fase de descubrimiento."""
    try:
        session = _engine.get_session(session_id)
        previous = session.current_phase
        new_phase = _engine.advance_phase(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AdvancePhaseResponse(
        session_id=session_id,
        previous_phase=previous.value,
        current_phase=new_phase.value,
    )


@router.post("/sessions/{session_id}/complete", response_model=CompleteSessionResponse)
async def complete_session(session_id: str):
    """Marca la sesión como completada."""
    try:
        session = _engine.complete_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CompleteSessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        completed_at=session.completed_at.isoformat() if session.completed_at else "",
    )


@router.get("/sessions/{session_id}/summary", response_model=SummaryResponse)
async def get_summary(session_id: str):
    """Obtiene el resumen completo de la sesión organizado por fases."""
    try:
        summary = _engine.get_session_summary(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    return SummaryResponse(**summary)


@router.post(
    "/sessions/{session_id}/generate-requirements",
    response_model=GenerateRequirementsResponse,
)
async def generate_requirements(session_id: str):
    """Genera un documento de requerimientos a partir de la sesión."""
    try:
        session = _engine.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    doc = _req_generator.generate_from_discovery(session)
    all_reqs = doc.requirements + doc.non_functional
    effort = _req_generator.estimate_effort(all_reqs)

    # Cachear para usar en propuesta
    _requirements_cache[session_id] = doc

    return GenerateRequirementsResponse(
        doc_id=doc.doc_id,
        client_name=doc.client_name,
        session_id=doc.session_id,
        requirements_count=len(doc.requirements),
        user_stories_count=len(doc.user_stories),
        non_functional_count=len(doc.non_functional),
        constraints=doc.constraints,
        assumptions=doc.assumptions,
        out_of_scope=doc.out_of_scope,
        effort_estimate=effort,
    )


@router.post(
    "/sessions/{session_id}/generate-proposal",
    response_model=GenerateProposalResponse,
)
async def generate_proposal(session_id: str):
    """Genera una propuesta comercial a partir de la sesión y requerimientos."""
    try:
        session = _engine.get_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Generar requerimientos si no están cacheados
    requirements = _requirements_cache.get(session_id)
    if requirements is None:
        requirements = _req_generator.generate_from_discovery(session)
        _requirements_cache[session_id] = requirements

    proposal = _proposal_generator.generate_proposal(session, requirements)
    _proposal_cache[session_id] = proposal

    return GenerateProposalResponse(
        proposal_id=proposal.proposal_id,
        client_name=proposal.client_name,
        executive_summary=proposal.executive_summary,
        recommended_plan=proposal.investment.get("plan", ""),
        modules_included=proposal.modules_included,
        timeline=proposal.timeline,
        investment=proposal.investment,
        phases_count=len(proposal.phases),
    )


@router.get(
    "/sessions/{session_id}/proposal/markdown",
    response_model=MarkdownResponse,
)
async def get_proposal_markdown(session_id: str):
    """Obtiene la propuesta renderizada como Markdown."""
    proposal = _proposal_cache.get(session_id)
    if proposal is None:
        raise HTTPException(
            status_code=404,
            detail="Propuesta no encontrada. Primero genere la propuesta con POST /generate-proposal",
        )

    md = _proposal_generator.to_markdown(proposal)
    return MarkdownResponse(
        proposal_id=proposal.proposal_id,
        markdown=md,
    )
