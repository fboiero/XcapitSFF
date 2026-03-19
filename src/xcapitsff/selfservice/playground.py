"""Agent Playground — test agents before activating them in production.

Provides a sandbox environment where users can interact with AI agents
(sales_qualifier, outreach_composer, support_responder, ticket_router)
using sample prompts or free-form messages, without affecting real data.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from xcapitsff.agents.dispatcher import AgentDispatcher, DispatchResult

logger = logging.getLogger(__name__)


@dataclass
class PlaygroundSession:
    """A playground conversation session with an agent."""

    session_id: str
    agent_role: str
    messages: list[tuple[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Sample prompts per agent role
# ---------------------------------------------------------------------------

_SAMPLE_PROMPTS: dict[str, list[dict]] = {
    "sales_qualifier": [
        {
            "label": "Calificar lead fintech LATAM",
            "prompt": (
                "Calific\u00e1 este lead: empresa de fintech en LATAM, "
                "CEO, score 75, afinidad HIGH"
            ),
        },
        {
            "label": "Lead bajo de Iberia",
            "prompt": (
                "Tengo un lead de Iberia, no es C-level, score 40, "
                "afinidad MEDIUM. \u00bfVale la pena contactar?"
            ),
        },
    ],
    "outreach_composer": [
        {
            "label": "Email primer contacto CEO",
            "prompt": (
                "Redact\u00e1 un email de primer contacto para un CEO "
                "de una fintech en Buenos Aires"
            ),
        },
        {
            "label": "LinkedIn CTO pagos M\u00e9xico",
            "prompt": (
                "Necesito un mensaje de LinkedIn para un CTO de una "
                "empresa de pagos en M\u00e9xico"
            ),
        },
    ],
    "support_responder": [
        {
            "label": "Cuenta bloqueada",
            "prompt": (
                "Un cliente dice que no puede hacer login. Su cuenta "
                "est\u00e1 bloqueada despu\u00e9s de 3 intentos."
            ),
        },
        {
            "label": "Dep\u00f3sito pendiente 48h",
            "prompt": (
                "Cliente reporta que su transacci\u00f3n de dep\u00f3sito "
                "lleva 48 horas pendiente."
            ),
        },
    ],
    "ticket_router": [
        {
            "label": "Urgencia cuenta robada",
            "prompt": (
                "Clasifica: 'URGENTE no puedo acceder a mis fondos, "
                "\u00a1me robaron la cuenta!'"
            ),
        },
        {
            "label": "Cambio de plan",
            "prompt": (
                "Clasifica: 'Quiero cambiar mi plan de suscripci\u00f3n "
                "al plan Pro'"
            ),
        },
    ],
}


class PlaygroundManager:
    """Manages playground sessions for testing agents interactively."""

    def __init__(self, dispatcher: AgentDispatcher | None = None):
        self._dispatcher = dispatcher or AgentDispatcher()
        self._sessions: dict[str, PlaygroundSession] = {}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(self, agent_role: str) -> PlaygroundSession:
        """Create a new playground session for the given agent role."""
        session_id = str(uuid.uuid4())
        session = PlaygroundSession(
            session_id=session_id,
            agent_role=agent_role,
        )
        self._sessions[session_id] = session
        logger.info(
            "Playground session %s started for role=%s",
            session_id,
            agent_role,
        )
        return session

    async def send_message(self, session_id: str, user_message: str) -> str:
        """Send a user message to the agent and return the response.

        Uses the dispatcher in dry-run / local / Argentor mode depending
        on configuration.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session {session_id} not found")

        session.messages.append(("user", user_message))
        session.last_active = datetime.utcnow()

        # Build conversation context from history
        history_lines = []
        for role, content in session.messages:
            prefix = "User" if role == "user" else "Agent"
            history_lines.append(f"{prefix}: {content}")
        context = "\n".join(history_lines)

        result: DispatchResult = await self._dispatcher.dispatch(
            agent_role=session.agent_role,
            context=context,
            session_id=session_id,
        )

        response_text = result.content
        session.messages.append(("agent", response_text))
        session.last_active = datetime.utcnow()

        logger.debug(
            "Playground %s: message processed via %s",
            session_id,
            result.backend,
        )
        return response_text

    def get_session(self, session_id: str) -> PlaygroundSession:
        """Return a session by ID or raise KeyError."""
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session {session_id} not found")
        return session

    def list_sessions(self) -> list[PlaygroundSession]:
        """Return all active playground sessions."""
        return list(self._sessions.values())

    # ------------------------------------------------------------------
    # Sample prompts
    # ------------------------------------------------------------------

    @staticmethod
    def get_sample_prompts(agent_role: str) -> list[dict]:
        """Return pre-built sample prompts for the given agent role."""
        return _SAMPLE_PROMPTS.get(agent_role, [])
