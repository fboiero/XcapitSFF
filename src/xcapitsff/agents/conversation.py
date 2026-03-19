"""Conversation memory — persistent conversation context for agents.

Tracks conversation history per agent per context (lead_id, ticket_id, etc.)
so agents can maintain context across multiple interactions.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class Conversation:
    conversation_id: str
    agent_name: str
    context_type: str  # "lead", "ticket", "customer", "general"
    context_id: str | int | None = None
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    summary: str = ""

    def add_message(self, role: str, content: str, metadata: dict | None = None) -> Message:
        msg = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(msg)
        self.last_active = datetime.now()
        return msg

    def get_messages_for_api(self, max_messages: int = 20) -> list[dict]:
        """Get messages formatted for Anthropic API."""
        recent = self.messages[-max_messages:]
        return [
            {"role": m.role if m.role != "system" else "user", "content": m.content}
            for m in recent
            if m.role in ("user", "assistant")
        ]

    @property
    def message_count(self) -> int:
        return len(self.messages)

    @property
    def duration_minutes(self) -> float:
        if not self.messages:
            return 0
        first = self.messages[0].timestamp
        last = self.messages[-1].timestamp
        return (last - first).total_seconds() / 60


class ConversationMemory:
    """Manages conversation history for all agents."""

    def __init__(self, persist_dir: str | None = None):
        self._conversations: dict[str, Conversation] = {}
        self._persist_dir = Path(persist_dir) if persist_dir else None
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"conv-{self._counter:06d}"

    def create(
        self,
        agent_name: str,
        context_type: str,
        context_id: str | int | None = None,
        system_prompt: str | None = None,
    ) -> Conversation:
        """Create a new conversation for an agent."""
        conv = Conversation(
            conversation_id=self._next_id(),
            agent_name=agent_name,
            context_type=context_type,
            context_id=context_id,
        )
        if system_prompt:
            conv.add_message("system", system_prompt)
        self._conversations[conv.conversation_id] = conv
        logger.info(f"Conversation created: {conv.conversation_id} for {agent_name}")
        return conv

    def get(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    def find_by_context(
        self, agent_name: str, context_type: str, context_id: str | int | None = None
    ) -> Conversation | None:
        """Find an existing conversation for an agent+context."""
        for conv in self._conversations.values():
            if (
                conv.agent_name == agent_name
                and conv.context_type == context_type
                and conv.context_id == context_id
            ):
                return conv
        return None

    def get_or_create(
        self,
        agent_name: str,
        context_type: str,
        context_id: str | int | None = None,
        system_prompt: str | None = None,
    ) -> Conversation:
        """Find existing or create new conversation."""
        existing = self.find_by_context(agent_name, context_type, context_id)
        if existing:
            return existing
        return self.create(agent_name, context_type, context_id, system_prompt)

    def list_conversations(
        self,
        agent_name: str | None = None,
        context_type: str | None = None,
        limit: int = 50,
    ) -> list[Conversation]:
        convs = list(self._conversations.values())
        if agent_name:
            convs = [c for c in convs if c.agent_name == agent_name]
        if context_type:
            convs = [c for c in convs if c.context_type == context_type]
        return sorted(convs, key=lambda c: c.last_active, reverse=True)[:limit]

    def get_stats(self) -> dict:
        total = len(self._conversations)
        by_agent: dict[str, int] = {}
        total_messages = 0
        for conv in self._conversations.values():
            by_agent[conv.agent_name] = by_agent.get(conv.agent_name, 0) + 1
            total_messages += conv.message_count
        return {
            "total_conversations": total,
            "total_messages": total_messages,
            "by_agent": by_agent,
        }

    def save_to_disk(self) -> None:
        """Persist conversations to disk."""
        if not self._persist_dir:
            return
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        for conv in self._conversations.values():
            path = self._persist_dir / f"{conv.conversation_id}.json"
            data = {
                "conversation_id": conv.conversation_id,
                "agent_name": conv.agent_name,
                "context_type": conv.context_type,
                "context_id": conv.context_id,
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in conv.messages
                ],
                "created_at": conv.created_at.isoformat(),
                "summary": conv.summary,
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def load_from_disk(self) -> int:
        """Load conversations from disk. Returns count loaded."""
        if not self._persist_dir or not self._persist_dir.exists():
            return 0
        count = 0
        for path in self._persist_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                conv = Conversation(
                    conversation_id=data["conversation_id"],
                    agent_name=data["agent_name"],
                    context_type=data["context_type"],
                    context_id=data.get("context_id"),
                    summary=data.get("summary", ""),
                )
                for msg_data in data.get("messages", []):
                    conv.messages.append(Message(
                        role=msg_data["role"],
                        content=msg_data["content"],
                    ))
                self._conversations[conv.conversation_id] = conv
                count += 1
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load conversation from {path}: {e}")
        return count


# Singleton
conversation_memory = ConversationMemory()
