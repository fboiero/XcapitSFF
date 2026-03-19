"""Agent Dispatcher — smart routing between Argentor (remote) and local agents.

When Argentor is available and enabled, dispatches to it for production-grade
agent execution (14 LLM backends, circuit breaker, compliance audit).
When Argentor is unavailable, falls back to local execution or dry-run.

This is the single entry point all business modules should use for AI tasks.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

from xcapitsff.agents.argentor_client import AgentResponse, argentor_client
from xcapitsff.agents.runner import AgentRunner, AgentRunResult, agent_runner
from xcapitsff.config import settings
from xcapitsff.core.audit import AuditAction, audit_log

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    """Unified result from either Argentor or local agent."""
    content: str
    agent_name: str
    action: str
    backend: str  # "argentor" | "local" | "dry_run"
    success: bool
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: float = 0
    session_id: str | None = None
    error: str | None = None
    compliance_flags: list[str] = field(default_factory=list)


class AgentDispatcher:
    """Routes agent tasks to the best available backend."""

    def __init__(self):
        self._stats = {
            "argentor_calls": 0,
            "local_calls": 0,
            "dry_run_calls": 0,
            "errors": 0,
        }

    async def dispatch(
        self,
        agent_role: str,
        context: str,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int = 2048,
    ) -> DispatchResult:
        """Dispatch an agent task to the best available backend.

        Priority: Argentor (if enabled + available) → Local runner → Dry run
        """
        # Try Argentor first
        if settings.argentor_enabled:
            argentor_result = await self._try_argentor(
                agent_role, context, system_prompt, session_id, max_tokens
            )
            if argentor_result:
                return argentor_result

        # Fall back to local
        return self._run_local(agent_role, context)

    async def _try_argentor(
        self,
        agent_role: str,
        context: str,
        system_prompt: str | None,
        session_id: str | None,
        max_tokens: int,
    ) -> DispatchResult | None:
        """Try to execute via Argentor. Returns None if unavailable."""
        if not await argentor_client.is_available():
            logger.debug("Argentor unavailable, falling back to local")
            return None

        prompt = system_prompt or self._default_prompt(agent_role)
        message = f"Action: {agent_role}\n\nContext:\n{context}"

        try:
            response = await argentor_client.chat(
                message=message,
                session_id=session_id,
                system_prompt=prompt,
            )

            if response.error == "argentor_unavailable":
                return None

            self._stats["argentor_calls"] += 1

            audit_log.record(
                AuditAction.ASSIGN,
                entity_type="agent_dispatch",
                entity_id=agent_role,
                actor="dispatcher",
                metadata={
                    "backend": "argentor",
                    "tokens": response.tokens_input + response.tokens_output,
                    "model": response.model_used,
                },
            )

            return DispatchResult(
                content=response.content,
                agent_name=agent_role,
                action=agent_role,
                backend="argentor",
                success=response.success,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                duration_ms=response.duration_ms,
                session_id=response.session_id,
                error=response.error if not response.success else None,
                compliance_flags=response.compliance_flags,
            )

        except Exception as e:
            logger.warning(f"Argentor dispatch failed: {e}, falling back to local")
            self._stats["errors"] += 1
            return None

    def _run_local(self, agent_role: str, context: str) -> DispatchResult:
        """Execute via local agent runner (dry-run if no API key)."""
        self._stats["local_calls"] += 1

        result = agent_runner.run_agent(
            agent_name=agent_role,
            action=agent_role,
            context=context,
            context_type="dispatch",
        )

        backend = "local" if settings.anthropic_api_key else "dry_run"
        if backend == "dry_run":
            self._stats["dry_run_calls"] += 1

        return DispatchResult(
            content=result.response,
            agent_name=result.agent_name,
            action=result.action,
            backend=backend,
            success=result.success,
            tokens_input=result.tokens_used.get("input_tokens", 0),
            tokens_output=result.tokens_used.get("output_tokens", 0),
            session_id=result.conversation_id,
            error=result.error,
        )

    def _default_prompt(self, agent_role: str) -> str:
        """Default system prompts for each agent role."""
        prompts = {
            "sales_qualifier": (
                "Sos el agente de calificación de ventas de Xcapit. "
                "Evaluás leads usando ICP scoring (Region, C-Level, Afinidad, Score). "
                "Clasificás como hot (>=70), warm (>=45), cool (>=25), cold (<25). "
                "Para cada lead, respondé con: score, clasificación, acción recomendada. "
                "Sé conciso."
            ),
            "outreach_composer": (
                "Sos el agente de outreach de Xcapit (fintech: inversión automatizada, "
                "activos digitales, DeFi). Componés mensajes personalizados por canal "
                "(email/linkedin/whatsapp), región (LATAM/Iberia), y perfil del lead. "
                "Incluí mensaje principal + variante A/B + siguiente paso."
            ),
            "support_responder": (
                "Sos el agente de soporte de Xcapit. Resolvés tickets empáticamente. "
                "Si no tenés certeza, decilo. Si es tema de fondos, NO dar instrucciones "
                "sin verificación. Español LATAM. Respondé con: respuesta al cliente + "
                "notas internas + si hay que escalar."
            ),
            "ticket_router": (
                "Clasificás tickets por categoría (billing/technical/account/crypto/general) "
                "y prioridad (urgent/high/medium/low). Respondé SOLO con JSON: "
                '{"category": "...", "priority": "...", "confidence": 0.0-1.0}'
            ),
        }
        return prompts.get(agent_role, f"Sos un agente especializado en {agent_role}.")

    # === Convenience methods for business modules ===

    async def qualify_lead(self, lead_data: dict) -> DispatchResult:
        context = "\n".join([
            f"Lead to qualify:",
            f"  Company: {lead_data.get('company_name', 'N/A')}",
            f"  Contact: {lead_data.get('contact_name', 'N/A')}",
            f"  Region: {lead_data.get('region', 'N/A')}",
            f"  C-Level: {lead_data.get('c_level', False)}",
            f"  Score ICP: {lead_data.get('score_icp', 'N/A')}",
            f"  Afinidad: {lead_data.get('afinidad', 'N/A')}",
        ])
        return await self.dispatch("sales_qualifier", context)

    async def draft_outreach(self, lead_data: dict, channel: str = "email") -> DispatchResult:
        context = "\n".join([
            f"Draft {channel} outreach for:",
            f"  Company: {lead_data.get('company_name', 'N/A')}",
            f"  Contact: {lead_data.get('contact_name', 'N/A')}",
            f"  Region: {lead_data.get('region', 'N/A')}",
            f"  C-Level: {lead_data.get('c_level', False)}",
            f"  Score: {lead_data.get('score_icp', 'N/A')}",
            f"  Afinidad: {lead_data.get('afinidad', 'N/A')}",
        ])
        return await self.dispatch("outreach_composer", context)

    async def handle_ticket(self, ticket_data: dict) -> DispatchResult:
        context = "\n".join([
            f"Ticket to respond:",
            f"  Subject: {ticket_data.get('subject', 'N/A')}",
            f"  Description: {ticket_data.get('description', 'N/A')}",
            f"  Category: {ticket_data.get('category', 'N/A')}",
            f"  Priority: {ticket_data.get('priority', 'N/A')}",
            f"  Customer: {ticket_data.get('customer_name', 'N/A')}",
        ])
        return await self.dispatch("support_responder", context)

    async def classify_ticket(self, subject: str, description: str) -> DispatchResult:
        context = f"Classify this ticket:\nSubject: {subject}\nDescription: {description}"
        return await self.dispatch("ticket_router", context)

    def get_stats(self) -> dict:
        return {
            **self._stats,
            "argentor_status": argentor_client.get_status(),
            "total_dispatches": sum(
                self._stats[k] for k in ["argentor_calls", "local_calls", "dry_run_calls"]
            ),
        }


# Singleton
dispatcher = AgentDispatcher()
