"""Motor de sesiones de descubrimiento para onboarding de clientes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DiscoveryPhase(str, Enum):
    """Fases del proceso de descubrimiento."""

    INTRO = "intro"
    BUSINESS_CONTEXT = "business_context"
    PROBLEM_DEFINITION = "problem_definition"
    USERS_AND_PERSONAS = "users_and_personas"
    CURRENT_WORKFLOW = "current_workflow"
    PAIN_POINTS = "pain_points"
    SUCCESS_CRITERIA = "success_criteria"
    TECHNICAL_CONTEXT = "technical_context"
    BUDGET_TIMELINE = "budget_timeline"
    SUMMARY = "summary"


class AnswerType(str, Enum):
    TEXT = "text"
    CHOICE = "choice"
    NUMBER = "number"
    LIST = "list"


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ---------------------------------------------------------------------------
# Orden de fases para navegación
# ---------------------------------------------------------------------------

PHASE_ORDER: list[DiscoveryPhase] = [
    DiscoveryPhase.INTRO,
    DiscoveryPhase.BUSINESS_CONTEXT,
    DiscoveryPhase.PROBLEM_DEFINITION,
    DiscoveryPhase.USERS_AND_PERSONAS,
    DiscoveryPhase.CURRENT_WORKFLOW,
    DiscoveryPhase.PAIN_POINTS,
    DiscoveryPhase.SUCCESS_CRITERIA,
    DiscoveryPhase.TECHNICAL_CONTEXT,
    DiscoveryPhase.BUDGET_TIMELINE,
    DiscoveryPhase.SUMMARY,
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DiscoveryQuestion:
    """Pregunta del banco de preguntas de descubrimiento."""

    question_id: str
    phase: DiscoveryPhase
    question_text: str
    follow_ups: list[str] = field(default_factory=list)
    required: bool = True
    answer_type: AnswerType = AnswerType.TEXT


@dataclass
class DiscoveryAnswer:
    """Respuesta a una pregunta de descubrimiento."""

    question_id: str
    phase: DiscoveryPhase
    answer: str
    notes: str = ""
    answered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiscoverySession:
    """Sesión de descubrimiento con un cliente."""

    session_id: str
    client_name: str
    client_email: str
    industry: str = ""
    current_phase: DiscoveryPhase = DiscoveryPhase.INTRO
    answers: list[DiscoveryAnswer] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    status: SessionStatus = SessionStatus.IN_PROGRESS


# ---------------------------------------------------------------------------
# Banco de preguntas (todas en español)
# ---------------------------------------------------------------------------

QUESTION_BANK: list[DiscoveryQuestion] = [
    # --- INTRO ---
    DiscoveryQuestion(
        question_id="intro_01",
        phase=DiscoveryPhase.INTRO,
        question_text="¿Cuál es el nombre de tu empresa/proyecto?",
        follow_ups=["¿Tienen un sitio web?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="intro_02",
        phase=DiscoveryPhase.INTRO,
        question_text="¿En qué industria operan?",
        follow_ups=["¿Tienen sub-verticales específicas?"],
        required=True,
        answer_type=AnswerType.CHOICE,
    ),
    DiscoveryQuestion(
        question_id="intro_03",
        phase=DiscoveryPhase.INTRO,
        question_text="¿Cuántos empleados tienen?",
        follow_ups=["¿Cuántos en el equipo de tecnología?"],
        required=False,
        answer_type=AnswerType.NUMBER,
    ),
    DiscoveryQuestion(
        question_id="intro_04",
        phase=DiscoveryPhase.INTRO,
        question_text="¿Cuál es tu rol en la empresa?",
        follow_ups=["¿Quién toma las decisiones técnicas?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    # --- BUSINESS_CONTEXT ---
    DiscoveryQuestion(
        question_id="biz_01",
        phase=DiscoveryPhase.BUSINESS_CONTEXT,
        question_text="¿Qué hace tu empresa? Describí el negocio en 2-3 oraciones.",
        follow_ups=["¿Cuál es su propuesta de valor diferencial?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="biz_02",
        phase=DiscoveryPhase.BUSINESS_CONTEXT,
        question_text="¿Quiénes son sus clientes principales?",
        follow_ups=["¿B2B o B2C?", "¿Cuál es el ticket promedio?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="biz_03",
        phase=DiscoveryPhase.BUSINESS_CONTEXT,
        question_text="¿En qué mercados operan? (LATAM, Iberia, Global)",
        follow_ups=["¿Planean expandirse a otros mercados?"],
        required=True,
        answer_type=AnswerType.CHOICE,
    ),
    DiscoveryQuestion(
        question_id="biz_04",
        phase=DiscoveryPhase.BUSINESS_CONTEXT,
        question_text="¿Cuál es su modelo de negocio? (SaaS, servicios, marketplace, etc.)",
        follow_ups=["¿Tienen ingresos recurrentes?"],
        required=True,
        answer_type=AnswerType.CHOICE,
    ),
    # --- PROBLEM_DEFINITION ---
    DiscoveryQuestion(
        question_id="prob_01",
        phase=DiscoveryPhase.PROBLEM_DEFINITION,
        question_text="¿Cuál es el principal problema que necesitan resolver?",
        follow_ups=["¿Hay problemas secundarios relacionados?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="prob_02",
        phase=DiscoveryPhase.PROBLEM_DEFINITION,
        question_text="¿Cómo están resolviendo este problema hoy?",
        follow_ups=["¿Es una solución temporal o permanente?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="prob_03",
        phase=DiscoveryPhase.PROBLEM_DEFINITION,
        question_text="¿Qué impacto tiene este problema en el negocio? (tiempo perdido, dinero, clientes)",
        follow_ups=["¿Pueden cuantificar el costo?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="prob_04",
        phase=DiscoveryPhase.PROBLEM_DEFINITION,
        question_text="¿Hace cuánto tienen este problema?",
        follow_ups=["¿Ha empeorado con el tiempo?"],
        required=False,
        answer_type=AnswerType.TEXT,
    ),
    # --- USERS_AND_PERSONAS ---
    DiscoveryQuestion(
        question_id="user_01",
        phase=DiscoveryPhase.USERS_AND_PERSONAS,
        question_text="¿Quiénes van a usar el sistema? Listá los tipos de usuario.",
        follow_ups=["¿Cuál es el usuario más importante?"],
        required=True,
        answer_type=AnswerType.LIST,
    ),
    DiscoveryQuestion(
        question_id="user_02",
        phase=DiscoveryPhase.USERS_AND_PERSONAS,
        question_text="¿Cuántos usuarios aproximadamente por tipo?",
        follow_ups=["¿Esperan crecimiento en el corto plazo?"],
        required=False,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="user_03",
        phase=DiscoveryPhase.USERS_AND_PERSONAS,
        question_text="¿Cuál es el nivel técnico de los usuarios? (básico, intermedio, avanzado)",
        follow_ups=["¿Necesitan capacitación?"],
        required=True,
        answer_type=AnswerType.CHOICE,
    ),
    # --- CURRENT_WORKFLOW ---
    DiscoveryQuestion(
        question_id="flow_01",
        phase=DiscoveryPhase.CURRENT_WORKFLOW,
        question_text="Describí paso a paso cómo funciona el proceso actual",
        follow_ups=["¿Cuánto tiempo toma cada paso?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="flow_02",
        phase=DiscoveryPhase.CURRENT_WORKFLOW,
        question_text="¿Qué herramientas/sistemas usan hoy? (Excel, CRM, email, etc.)",
        follow_ups=["¿Están satisfechos con esas herramientas?"],
        required=True,
        answer_type=AnswerType.LIST,
    ),
    DiscoveryQuestion(
        question_id="flow_03",
        phase=DiscoveryPhase.CURRENT_WORKFLOW,
        question_text="¿Qué parte del proceso es manual y debería automatizarse?",
        follow_ups=["¿Cuántas horas semanales consume la tarea manual?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="flow_04",
        phase=DiscoveryPhase.CURRENT_WORKFLOW,
        question_text="¿Hay integraciones necesarias con otros sistemas?",
        follow_ups=["¿Tienen documentación de las APIs?"],
        required=False,
        answer_type=AnswerType.LIST,
    ),
    # --- PAIN_POINTS ---
    DiscoveryQuestion(
        question_id="pain_01",
        phase=DiscoveryPhase.PAIN_POINTS,
        question_text="¿Cuáles son los 3 mayores dolores del proceso actual?",
        follow_ups=["¿Cuál es el más urgente?"],
        required=True,
        answer_type=AnswerType.LIST,
    ),
    DiscoveryQuestion(
        question_id="pain_02",
        phase=DiscoveryPhase.PAIN_POINTS,
        question_text="¿Qué es lo que más tiempo consume?",
        follow_ups=["¿Cuántas horas por semana?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="pain_03",
        phase=DiscoveryPhase.PAIN_POINTS,
        question_text="¿Dónde se pierden datos o se cometen errores?",
        follow_ups=["¿Con qué frecuencia ocurre?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    # --- SUCCESS_CRITERIA ---
    DiscoveryQuestion(
        question_id="success_01",
        phase=DiscoveryPhase.SUCCESS_CRITERIA,
        question_text="¿Cómo medirían el éxito del proyecto?",
        follow_ups=["¿Hay métricas cuantitativas?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="success_02",
        phase=DiscoveryPhase.SUCCESS_CRITERIA,
        question_text="¿Qué KPIs son importantes?",
        follow_ups=["¿Cuáles son los valores objetivo?"],
        required=True,
        answer_type=AnswerType.LIST,
    ),
    DiscoveryQuestion(
        question_id="success_03",
        phase=DiscoveryPhase.SUCCESS_CRITERIA,
        question_text="¿Qué debería pasar para que consideren el proyecto exitoso?",
        follow_ups=["¿En qué plazo?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    # --- TECHNICAL_CONTEXT ---
    DiscoveryQuestion(
        question_id="tech_01",
        phase=DiscoveryPhase.TECHNICAL_CONTEXT,
        question_text="¿Tienen equipo técnico interno?",
        follow_ups=["¿Cuántas personas?", "¿Qué tecnologías manejan?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="tech_02",
        phase=DiscoveryPhase.TECHNICAL_CONTEXT,
        question_text="¿Hay preferencias de tecnología o restricciones?",
        follow_ups=["¿Usan cloud? ¿Cuál?"],
        required=False,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="tech_03",
        phase=DiscoveryPhase.TECHNICAL_CONTEXT,
        question_text="¿Necesitan que funcione en mobile, web, o ambos?",
        follow_ups=["¿App nativa o web responsive?"],
        required=True,
        answer_type=AnswerType.CHOICE,
    ),
    DiscoveryQuestion(
        question_id="tech_04",
        phase=DiscoveryPhase.TECHNICAL_CONTEXT,
        question_text="¿Hay requisitos de seguridad o compliance específicos?",
        follow_ups=["¿GDPR?", "¿PCI-DSS?", "¿Datos sensibles de salud?"],
        required=False,
        answer_type=AnswerType.TEXT,
    ),
    # --- BUDGET_TIMELINE ---
    DiscoveryQuestion(
        question_id="budget_01",
        phase=DiscoveryPhase.BUDGET_TIMELINE,
        question_text="¿Cuál es el presupuesto estimado para este proyecto?",
        follow_ups=["¿Es flexible?", "¿Hay aprobación ya?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="budget_02",
        phase=DiscoveryPhase.BUDGET_TIMELINE,
        question_text="¿Cuándo necesitan tener la primera versión funcionando?",
        follow_ups=["¿Qué funcionalidades son prioritarias para esa fecha?"],
        required=True,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="budget_03",
        phase=DiscoveryPhase.BUDGET_TIMELINE,
        question_text="¿Hay alguna fecha límite crítica?",
        follow_ups=["¿Qué pasa si no se cumple?"],
        required=False,
        answer_type=AnswerType.TEXT,
    ),
    DiscoveryQuestion(
        question_id="budget_04",
        phase=DiscoveryPhase.BUDGET_TIMELINE,
        question_text="¿Prefieren un desarrollo completo o iterativo (MVP primero)?",
        follow_ups=["¿Tienen experiencia con metodologías ágiles?"],
        required=True,
        answer_type=AnswerType.CHOICE,
    ),
]


def _build_question_index() -> dict[str, DiscoveryQuestion]:
    """Índice de preguntas por question_id."""
    return {q.question_id: q for q in QUESTION_BANK}


QUESTION_INDEX: dict[str, DiscoveryQuestion] = _build_question_index()


def get_questions_for_phase(phase: DiscoveryPhase) -> list[DiscoveryQuestion]:
    """Devuelve todas las preguntas de una fase."""
    return [q for q in QUESTION_BANK if q.phase == phase]


def _get_answer_text(session: DiscoverySession, question_id: str) -> Optional[str]:
    """Obtiene el texto de respuesta para un question_id dado."""
    for a in session.answers:
        if a.question_id == question_id:
            return a.answer
    return None


# ---------------------------------------------------------------------------
# Motor de descubrimiento
# ---------------------------------------------------------------------------


class DiscoveryEngine:
    """Motor principal para gestionar sesiones de descubrimiento."""

    def __init__(self) -> None:
        self._sessions: dict[str, DiscoverySession] = {}

    # -- Ciclo de vida de sesión --

    def start_session(self, client_name: str, client_email: str) -> DiscoverySession:
        """Inicia una nueva sesión de descubrimiento."""
        session_id = uuid.uuid4().hex[:16]
        session = DiscoverySession(
            session_id=session_id,
            client_name=client_name,
            client_email=client_email,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> DiscoverySession:
        """Obtiene una sesión por su ID."""
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Sesión no encontrada: {session_id}")
        return session

    def list_sessions(self) -> list[DiscoverySession]:
        """Lista todas las sesiones."""
        return list(self._sessions.values())

    # -- Preguntas --

    def get_current_questions(self, session_id: str) -> list[DiscoveryQuestion]:
        """Devuelve las preguntas de la fase actual de la sesión."""
        session = self.get_session(session_id)
        return get_questions_for_phase(session.current_phase)

    # -- Respuestas --

    def answer_question(
        self, session_id: str, question_id: str, answer: str, notes: str = ""
    ) -> DiscoveryAnswer:
        """Registra una respuesta a una pregunta."""
        session = self.get_session(session_id)

        if session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("La sesión no está en progreso")

        if question_id not in QUESTION_INDEX:
            raise KeyError(f"Pregunta no encontrada: {question_id}")

        question = QUESTION_INDEX[question_id]
        if question.phase != session.current_phase:
            raise ValueError(
                f"La pregunta '{question_id}' pertenece a la fase "
                f"'{question.phase.value}', pero la sesión está en "
                f"'{session.current_phase.value}'"
            )

        # Basic answer quality validation
        answer_stripped = answer.strip()
        if not answer_stripped:
            raise ValueError("La respuesta no puede estar vacía")
        if len(answer_stripped) < 10:
            raise ValueError(
                f"La respuesta es demasiado corta ({len(answer_stripped)} caracteres). "
                "Por favor, proporcioná más detalle (mínimo 10 caracteres)."
            )

        # Si ya fue respondida, actualizar
        for existing in session.answers:
            if existing.question_id == question_id:
                existing.answer = answer
                existing.notes = notes
                existing.answered_at = datetime.now(timezone.utc)
                # Auto-populate industry from intro_02 answer
                if question_id == "intro_02":
                    session.industry = answer
                return existing

        discovery_answer = DiscoveryAnswer(
            question_id=question_id,
            phase=session.current_phase,
            answer=answer,
            notes=notes,
        )
        session.answers.append(discovery_answer)
        # Auto-populate industry from intro_02 answer
        if question_id == "intro_02":
            session.industry = answer
        return discovery_answer

    # -- Navegación de fases --

    def advance_phase(self, session_id: str) -> DiscoveryPhase:
        """Avanza a la siguiente fase de descubrimiento."""
        session = self.get_session(session_id)

        if session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("La sesión no está en progreso")

        current_idx = PHASE_ORDER.index(session.current_phase)
        if current_idx >= len(PHASE_ORDER) - 1:
            raise ValueError("Ya se encuentra en la última fase")

        # Verificar que las preguntas requeridas estén respondidas
        phase_questions = get_questions_for_phase(session.current_phase)
        answered_ids = {a.question_id for a in session.answers}
        required_unanswered = [
            q for q in phase_questions if q.required and q.question_id not in answered_ids
        ]
        if required_unanswered:
            missing = ", ".join(q.question_id for q in required_unanswered)
            raise ValueError(
                f"Faltan preguntas requeridas sin responder: {missing}"
            )

        next_phase = PHASE_ORDER[current_idx + 1]
        session.current_phase = next_phase
        return next_phase

    # -- Resumen y completitud --

    def get_session_summary(self, session_id: str) -> dict:
        """Devuelve un resumen de todas las respuestas organizadas por fase."""
        session = self.get_session(session_id)
        summary: dict[str, list[dict]] = {}

        for phase in DiscoveryPhase:
            phase_answers = [a for a in session.answers if a.phase == phase]
            if phase_answers:
                summary[phase.value] = []
                for ans in phase_answers:
                    q = QUESTION_INDEX.get(ans.question_id)
                    summary[phase.value].append(
                        {
                            "question_id": ans.question_id,
                            "question_text": q.question_text if q else "",
                            "answer": ans.answer,
                            "notes": ans.notes,
                            "answered_at": ans.answered_at.isoformat(),
                        }
                    )

        return {
            "session_id": session.session_id,
            "client_name": session.client_name,
            "client_email": session.client_email,
            "industry": session.industry,
            "status": session.status.value,
            "current_phase": session.current_phase.value,
            "completion_percentage": self.get_completion_percentage(session_id),
            "phases": summary,
        }

    def get_completion_percentage(self, session_id: str) -> float:
        """Calcula el porcentaje de completitud de la sesión."""
        session = self.get_session(session_id)
        total_required = sum(1 for q in QUESTION_BANK if q.required)
        if total_required == 0:
            return 100.0

        answered_ids = {a.question_id for a in session.answers}
        answered_required = sum(
            1 for q in QUESTION_BANK if q.required and q.question_id in answered_ids
        )
        return round((answered_required / total_required) * 100, 1)

    def complete_session(self, session_id: str) -> DiscoverySession:
        """Marca la sesión como completada."""
        session = self.get_session(session_id)

        if session.status != SessionStatus.IN_PROGRESS:
            raise ValueError("La sesión no está en progreso")

        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        return session
