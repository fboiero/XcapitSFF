"""Agent Runner — executes agent tasks using Anthropic API with conversation memory.

This is the bridge between the Orchestrator (which creates tasks) and
the actual AI agent execution (via Anthropic API).
"""

import logging
from dataclasses import dataclass

from xcapitsff.agents.base import BaseAgent
from xcapitsff.agents.conversation import Conversation, ConversationMemory, conversation_memory
from xcapitsff.agents.sales import create_outreach_composer, create_sales_qualifier
from xcapitsff.agents.support import create_support_responder, create_ticket_router
from xcapitsff.config import settings
from xcapitsff.core.audit import AuditAction, audit_log

logger = logging.getLogger(__name__)


@dataclass
class AgentRunResult:
    agent_name: str
    action: str
    response: str
    conversation_id: str
    tokens_used: dict
    success: bool
    error: str | None = None


# Agent factory — maps agent names to creation functions
AGENT_FACTORIES: dict[str, callable] = {
    "sales_qualifier": create_sales_qualifier,
    "outreach_composer": create_outreach_composer,
    "support_responder": create_support_responder,
    "ticket_router": create_ticket_router,
}


def _get_or_create_agent(agent_name: str) -> BaseAgent | None:
    """Get an agent instance by name."""
    factory = AGENT_FACTORIES.get(agent_name)
    if not factory:
        logger.warning(f"Unknown agent: {agent_name}")
        return None
    return factory()


class AgentRunner:
    """Executes agent tasks with conversation memory and audit logging."""

    def __init__(self, memory: ConversationMemory | None = None):
        self.memory = memory or conversation_memory
        self._dry_run = not bool(settings.anthropic_api_key)

    def run_agent(
        self,
        agent_name: str,
        action: str,
        context: str,
        context_type: str = "general",
        context_id: str | int | None = None,
    ) -> AgentRunResult:
        """Run an agent with the given context.

        In dry_run mode (no API key), returns a mock response.
        In production, calls the Anthropic API.
        """
        # Get or create conversation
        conv = self.memory.get_or_create(
            agent_name=agent_name,
            context_type=context_type,
            context_id=context_id,
        )

        # Build the user message
        user_message = f"Action: {action}\n\nContext:\n{context}"
        conv.add_message("user", user_message)

        if self._dry_run:
            # Mock response when no API key
            response_text = (
                f"[DRY RUN] Agent '{agent_name}' would process action '{action}' "
                f"with context type '{context_type}' (id={context_id}). "
                f"Configure ANTHROPIC_API_KEY to enable real agent execution."
            )
            conv.add_message("assistant", response_text)
            audit_log.record(
                AuditAction.ASSIGN,
                entity_type=context_type,
                entity_id=context_id or "n/a",
                actor=agent_name,
                metadata={"action": action, "mode": "dry_run"},
            )
            return AgentRunResult(
                agent_name=agent_name,
                action=action,
                response=response_text,
                conversation_id=conv.conversation_id,
                tokens_used={"input_tokens": 0, "output_tokens": 0},
                success=True,
            )

        # Real execution
        agent = _get_or_create_agent(agent_name)
        if not agent:
            error = f"Agent '{agent_name}' not found"
            return AgentRunResult(
                agent_name=agent_name,
                action=action,
                response="",
                conversation_id=conv.conversation_id,
                tokens_used={},
                success=False,
                error=error,
            )

        try:
            # Load conversation history into agent
            agent.conversation = []
            for msg in conv.messages:
                if msg.role in ("user", "assistant"):
                    from xcapitsff.agents.base import AgentMessage
                    agent.conversation.append(AgentMessage(role=msg.role, content=msg.content))

            result = agent.run(user_message)
            conv.add_message("assistant", result.response)

            audit_log.record(
                AuditAction.ASSIGN,
                entity_type=context_type,
                entity_id=context_id or "n/a",
                actor=agent_name,
                metadata={"action": action, "tokens": result.usage},
            )

            return AgentRunResult(
                agent_name=agent_name,
                action=action,
                response=result.response,
                conversation_id=conv.conversation_id,
                tokens_used=result.usage,
                success=True,
            )

        except Exception as e:
            error = str(e)
            logger.error(f"Agent {agent_name} failed: {error}")
            return AgentRunResult(
                agent_name=agent_name,
                action=action,
                response="",
                conversation_id=conv.conversation_id,
                tokens_used={},
                success=False,
                error=error,
            )

    def qualify_lead(self, lead_data: dict) -> AgentRunResult:
        """Convenience method: run sales qualifier on a lead."""
        context = (
            f"Lead to qualify:\n"
            f"  Company: {lead_data.get('company_name', 'N/A')}\n"
            f"  Contact: {lead_data.get('contact_name', 'N/A')}\n"
            f"  Region: {lead_data.get('region', 'N/A')}\n"
            f"  C-Level: {lead_data.get('c_level', False)}\n"
            f"  Score ICP: {lead_data.get('score_icp', 'N/A')}\n"
            f"  Afinidad: {lead_data.get('afinidad', 'N/A')}\n"
        )
        return self.run_agent(
            "sales_qualifier", "qualify_lead", context,
            context_type="lead", context_id=lead_data.get("id"),
        )

    def draft_outreach(self, lead_data: dict, channel: str = "email") -> AgentRunResult:
        """Convenience method: draft outreach for a lead."""
        context = (
            f"Draft {channel} outreach for:\n"
            f"  Company: {lead_data.get('company_name', 'N/A')}\n"
            f"  Contact: {lead_data.get('contact_name', 'N/A')}\n"
            f"  Region: {lead_data.get('region', 'N/A')}\n"
            f"  C-Level: {lead_data.get('c_level', False)}\n"
            f"  Score: {lead_data.get('score_icp', 'N/A')}\n"
            f"  Afinidad: {lead_data.get('afinidad', 'N/A')}\n"
        )
        return self.run_agent(
            "outreach_composer", "draft_outreach", context,
            context_type="lead", context_id=lead_data.get("id"),
        )

    def handle_ticket(self, ticket_data: dict) -> AgentRunResult:
        """Convenience method: generate response for a ticket."""
        context = (
            f"Ticket to respond:\n"
            f"  Subject: {ticket_data.get('subject', 'N/A')}\n"
            f"  Description: {ticket_data.get('description', 'N/A')}\n"
            f"  Category: {ticket_data.get('category', 'N/A')}\n"
            f"  Priority: {ticket_data.get('priority', 'N/A')}\n"
            f"  Customer: {ticket_data.get('customer_name', 'N/A')}\n"
        )
        return self.run_agent(
            "support_responder", "handle_ticket", context,
            context_type="ticket", context_id=ticket_data.get("id"),
        )


# Singleton
agent_runner = AgentRunner()
