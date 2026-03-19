"""Conversation manager for the conversational assistant.

Maintains conversation state, context accumulation, and orchestrates
intent recognition -> action execution -> response formatting.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .executor import ActionExecutor, ActionResult
from .intent import Intent, IntentRecognizer
from .visual import VisualComponent, action_card


@dataclass
class AssistantMessage:
    """A single message in the assistant conversation."""

    role: str  # "user" | "assistant" | "system"
    content: str
    visual: dict | None = None
    visual_components: list[dict] | None = None
    timestamp: str = ""
    suggestions: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


@dataclass
class AssistantConversation:
    """Full conversation state including accumulated context."""

    conversation_id: str
    tenant_id: str
    user_id: str
    messages: list[AssistantMessage] = field(default_factory=list)
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "visual": m.visual,
                    "visual_components": m.visual_components,
                    "timestamp": m.timestamp,
                    "suggestions": m.suggestions,
                }
                for m in self.messages
            ],
            "context": self.context,
        }


class AssistantManager:
    """Orchestrates conversations between the user and the assistant."""

    def __init__(self) -> None:
        self._recognizer = IntentRecognizer()
        self._executor = ActionExecutor()
        self._conversations: dict[str, AssistantConversation] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_conversation(self, tenant_id: str, user_id: str) -> AssistantConversation:
        """Create a new conversation and return it with a greeting."""
        conversation_id = str(uuid.uuid4())
        conversation = AssistantConversation(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        greeting = self.get_greeting_message()
        conversation.messages.append(greeting)
        conversation.context["last_action"] = "greeting"

        self._conversations[conversation_id] = conversation
        return conversation

    def process_message(self, conversation_id: str, user_text: str) -> AssistantMessage:
        """Process a user message and return the assistant response.

        Steps:
        1. Recognise intent from user text
        2. Execute the corresponding action
        3. Format response with visual components
        4. Add contextual suggestions
        5. Update conversation context
        """
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversacion no encontrada: {conversation_id}")

        # Record the user message
        user_msg = AssistantMessage(role="user", content=user_text)
        conversation.messages.append(user_msg)

        # 1. Recognise intent
        intent_match = self._recognizer.recognize(user_text)

        # 2. Execute action
        result: ActionResult = self._executor.execute(intent_match, conversation.context)

        # 3. Serialize visual components from the executor
        serialized_components: list[dict] | None = None
        if result.visual_components:
            serialized_components = [vc.to_dict() for vc in result.visual_components]

        # 4. Build legacy visual_data for backward compatibility
        visual_data: dict | None = None
        if result.result_data or serialized_components:
            visual_data = {
                "type": result.visual_type,
                "data": result.result_data,
            }

        # 5. Build assistant message with both legacy and rich visual data
        assistant_msg = AssistantMessage(
            role="assistant",
            content=result.message,
            visual=visual_data,
            visual_components=serialized_components,
            suggestions=result.next_suggestions,
        )

        # 6. Update context
        self._update_context(conversation, intent_match, result)

        conversation.messages.append(assistant_msg)
        return assistant_msg

    def get_conversation(self, conversation_id: str) -> AssistantConversation:
        """Retrieve a conversation by ID."""
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversacion no encontrada: {conversation_id}")
        return conversation

    def get_greeting_message(self) -> AssistantMessage:
        """Build a context-aware welcome message with rich visual components."""
        # Build quickstart action cards
        quickstart_cards = [
            action_card(
                "Ver Dashboard",
                "Revisa tus metricas y KPIs en tiempo real",
                "Abrir", "/api/v1/dashboard", icon="chart",
            ),
            action_card(
                "Crear un Lead",
                "Registra un nuevo prospecto en el pipeline",
                "Crear", "/api/v1/leads", icon="add_person",
            ),
            action_card(
                "Ver Tickets",
                "Consulta los tickets de soporte abiertos",
                "Ver", "/api/v1/tickets", icon="support",
            ),
            action_card(
                "Buscar",
                "Busca leads, tickets o clientes rapidamente",
                "Buscar", "/api/v1/search", icon="search",
            ),
        ]

        serialized_cards = [c.to_dict() for c in quickstart_cards]

        return AssistantMessage(
            role="assistant",
            content=(
                "Hola! Soy tu asistente de XcapitSFF. "
                "Puedo ayudarte a gestionar leads, tickets, campanas, "
                "ver metricas y mucho mas. Que necesitas?"
            ),
            visual={
                "type": "card",
                "data": {
                    "welcome": True,
                    "quick_actions": [
                        {"label": "Ver dashboard", "intent": "VIEW_DASHBOARD"},
                        {"label": "Crear un lead", "intent": "CREATE_LEAD"},
                        {"label": "Ver mis tickets", "intent": "LIST_TICKETS"},
                        {"label": "Buscar", "intent": "SEARCH"},
                    ],
                },
            },
            visual_components=serialized_cards,
            suggestions=[
                "Ver el dashboard",
                "Crear un nuevo lead",
                "Ver mis tickets",
                "Ayuda",
            ],
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_context(
        self,
        conversation: AssistantConversation,
        intent_match: "IntentMatch",  # noqa: F821
        result: ActionResult,
    ) -> None:
        """Update conversation context based on the action just taken."""
        ctx = conversation.context
        ctx["last_action"] = result.action_taken
        ctx["last_intent"] = intent_match.intent.value

        # Track entity IDs for follow-up actions
        data = result.result_data
        if "lead" in data:
            ctx["current_lead_id"] = data["lead"].get("id")
        if "ticket" in data:
            ctx["current_ticket_id"] = data["ticket"].get("id")
        if "customer" in data:
            ctx["current_customer_id"] = data["customer"].get("id")

        # Track IDs from intent params
        ids = intent_match.extracted_params.get("ids", [])
        if ids:
            ctx["last_mentioned_ids"] = ids

        # Track search queries
        if intent_match.extracted_params.get("search_query"):
            ctx["last_search_query"] = intent_match.extracted_params["search_query"]
