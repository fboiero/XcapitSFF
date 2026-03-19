"""API endpoints for the conversational assistant."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from xcapitsff.assistant.conversation import AssistantManager

router = APIRouter(prefix="/assistant", tags=["Assistant"])

# Shared manager instance (per-process, in-memory conversations).
_manager = AssistantManager()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class StartConversationRequest(BaseModel):
    tenant_id: str
    user_id: str


class SendMessageRequest(BaseModel):
    conversation_id: str
    text: str


class SuggestionsRequest(BaseModel):
    conversation_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/start")
async def start_conversation(req: StartConversationRequest):
    """Iniciar una nueva conversacion con el asistente."""
    conversation = _manager.start_conversation(req.tenant_id, req.user_id)
    return conversation.to_dict()


@router.post("/message")
async def send_message(req: SendMessageRequest):
    """Enviar un mensaje al asistente y recibir respuesta con datos visuales."""
    try:
        msg = _manager.process_message(req.conversation_id, req.text)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {
        "role": msg.role,
        "content": msg.content,
        "visual": msg.visual,
        "timestamp": msg.timestamp,
        "suggestions": msg.suggestions,
    }


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Obtener el historial completo de una conversacion."""
    try:
        conversation = _manager.get_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return conversation.to_dict()


@router.get("/suggestions")
async def get_suggestions(conversation_id: str | None = None):
    """Sugerencias contextuales de acciones disponibles."""
    if conversation_id:
        try:
            conversation = _manager.get_conversation(conversation_id)
            # Return last suggestions from the most recent assistant message.
            for msg in reversed(conversation.messages):
                if msg.role == "assistant" and msg.suggestions:
                    return {
                        "conversation_id": conversation_id,
                        "suggestions": msg.suggestions,
                    }
        except ValueError:
            pass

    # Default suggestions when there is no active conversation context.
    return {
        "conversation_id": conversation_id,
        "suggestions": [
            "Ver el dashboard",
            "Crear un nuevo lead",
            "Ver mis tickets",
            "Buscar un cliente",
            "Ayuda",
        ],
    }
