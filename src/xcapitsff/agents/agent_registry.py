"""Agent Registry — manages agent profiles, capabilities, and selection.

Central registry for all agents in the orchestration layer. Tracks agent
status, capabilities, performance metrics, and provides intelligent agent
selection based on capability matching, tier preference, and load balancing.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    """Capabilities that agents can provide."""

    QUALIFY = "qualify"
    PLAN = "plan"
    SPEC = "spec"
    IMPLEMENT = "implement"
    REVIEW = "review"
    TEST = "test"
    DOCUMENT = "document"
    OUTREACH = "outreach"
    SUPPORT = "support"
    CLASSIFY = "classify"
    ANALYZE = "analyze"
    PROPOSE = "propose"
    DISCOVER = "discover"
    SECURITY = "security"


class ModelTier(str, Enum):
    """Model tiers ordered by capability and cost."""

    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


class AgentStatus(str, Enum):
    """Runtime status of an agent."""

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class AgentProfile:
    """Complete profile for a registered agent."""

    id: str
    name: str
    role: str
    description: str
    capabilities: list[AgentCapability]
    model_tier: ModelTier
    system_prompt: str
    tools: list[str]
    status: AgentStatus = AgentStatus.AVAILABLE
    current_task_id: str | None = None
    tasks_completed: int = 0
    avg_response_seconds: float = 0.0
    cost_per_1k_tokens: float = 0.0
    total_tokens_used: int = 0
    last_active: datetime | None = None
    registered_at: datetime = field(default_factory=datetime.now)


class AgentRegistry:
    """Central registry for agent profiles and selection."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentProfile] = {}
        self._setup_default_agents()

    def register(self, profile: AgentProfile) -> AgentProfile:
        """Register an agent profile. Overwrites if id already exists."""
        self._agents[profile.id] = profile
        logger.info(f"Agent registered: {profile.id} ({profile.name})")
        return profile

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry. Returns True if found."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent unregistered: {agent_id}")
            return True
        return False

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Retrieve an agent profile by id."""
        return self._agents.get(agent_id)

    def get_available(self, capability: AgentCapability) -> list[AgentProfile]:
        """Return agents that are AVAILABLE and have the given capability."""
        return [
            agent
            for agent in self._agents.values()
            if agent.status == AgentStatus.AVAILABLE
            and capability in agent.capabilities
        ]

    def get_by_role(self, role: str) -> AgentProfile | None:
        """Return the first agent matching the given role."""
        for agent in self._agents.values():
            if agent.role == role:
                return agent
        return None

    def list_agents(self, status: AgentStatus | None = None) -> list[AgentProfile]:
        """List all agents, optionally filtered by status."""
        if status is None:
            return list(self._agents.values())
        return [a for a in self._agents.values() if a.status == status]

    def update_status(
        self, agent_id: str, status: AgentStatus, task_id: str | None = None
    ) -> bool:
        """Update an agent's status and optionally its current task id."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        agent.status = status
        agent.current_task_id = task_id
        return True

    def mark_busy(self, agent_id: str, task_id: str) -> bool:
        """Mark an agent as busy with a specific task."""
        return self.update_status(agent_id, AgentStatus.BUSY, task_id=task_id)

    def mark_available(self, agent_id: str) -> bool:
        """Mark an agent as available (clears current task)."""
        return self.update_status(agent_id, AgentStatus.AVAILABLE, task_id=None)

    def record_completion(
        self, agent_id: str, duration_seconds: float, tokens_used: int
    ) -> None:
        """Record a completed task for an agent, updating metrics."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return

        # Running average for response time
        prev_total = agent.avg_response_seconds * agent.tasks_completed
        agent.tasks_completed += 1
        agent.avg_response_seconds = (
            (prev_total + duration_seconds) / agent.tasks_completed
        )
        agent.total_tokens_used += tokens_used
        agent.last_active = datetime.now()

    def select_best_agent(
        self,
        capability: AgentCapability,
        prefer_tier: ModelTier | None = None,
    ) -> AgentProfile | None:
        """Select the best available agent for a capability.

        Selection strategy:
        1. Filter to available agents with the required capability.
        2. If prefer_tier is set, prefer agents in that tier.
        3. Among candidates, pick the one with fewest tasks_completed (least loaded).
        """
        candidates = self.get_available(capability)
        if not candidates:
            return None

        if prefer_tier is not None:
            tier_candidates = [c for c in candidates if c.model_tier == prefer_tier]
            if tier_candidates:
                candidates = tier_candidates

        # Pick least loaded agent
        return min(candidates, key=lambda a: a.tasks_completed)

    def get_pool_stats(self) -> dict:
        """Return aggregate statistics for the agent pool."""
        agents = list(self._agents.values())

        by_tier: dict[str, int] = {}
        for agent in agents:
            tier = agent.model_tier.value
            by_tier[tier] = by_tier.get(tier, 0) + 1

        by_capability: dict[str, int] = {}
        for agent in agents:
            for cap in agent.capabilities:
                by_capability[cap.value] = by_capability.get(cap.value, 0) + 1

        total_tokens = sum(a.total_tokens_used for a in agents)

        return {
            "total": len(agents),
            "available": sum(1 for a in agents if a.status == AgentStatus.AVAILABLE),
            "busy": sum(1 for a in agents if a.status == AgentStatus.BUSY),
            "offline": sum(1 for a in agents if a.status == AgentStatus.OFFLINE),
            "by_tier": by_tier,
            "by_capability": by_capability,
            "total_tokens": total_tokens,
        }

    def get_agent_stats(self, agent_id: str) -> dict | None:
        """Return performance stats for a single agent."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return None
        return {
            "id": agent.id,
            "name": agent.name,
            "status": agent.status.value,
            "model_tier": agent.model_tier.value,
            "tasks_completed": agent.tasks_completed,
            "avg_response_seconds": agent.avg_response_seconds,
            "total_tokens_used": agent.total_tokens_used,
            "cost_per_1k_tokens": agent.cost_per_1k_tokens,
            "last_active": agent.last_active.isoformat() if agent.last_active else None,
        }

    # ------------------------------------------------------------------
    # Default agent definitions
    # ------------------------------------------------------------------

    def _setup_default_agents(self) -> None:
        """Pre-register the 15 default agents."""
        defaults: list[dict] = [
            {
                "id": "product_manager",
                "name": "Product Manager",
                "role": "product_manager",
                "description": "Descubre necesidades de producto y analiza oportunidades de negocio.",
                "capabilities": [AgentCapability.DISCOVER, AgentCapability.ANALYZE],
                "model_tier": ModelTier.OPUS,
                "system_prompt": (
                    "Sos el Product Manager del equipo. Tu rol es descubrir "
                    "necesidades del producto y analizar oportunidades de negocio."
                ),
                "tools": ["search", "analytics"],
                "cost_per_1k_tokens": 0.015,
            },
            {
                "id": "business_analyst",
                "name": "Business Analyst",
                "role": "business_analyst",
                "description": "Analiza requerimientos de negocio y genera especificaciones.",
                "capabilities": [
                    AgentCapability.ANALYZE,
                    AgentCapability.SPEC,
                    AgentCapability.PROPOSE,
                ],
                "model_tier": ModelTier.OPUS,
                "system_prompt": (
                    "Sos el Business Analyst. Analizás requerimientos de negocio "
                    "y generás especificaciones claras y propuestas accionables."
                ),
                "tools": ["search", "documents"],
                "cost_per_1k_tokens": 0.015,
            },
            {
                "id": "planner",
                "name": "Planner",
                "role": "planner",
                "description": "Planifica tareas, estima esfuerzos y define prioridades.",
                "capabilities": [AgentCapability.PLAN, AgentCapability.ANALYZE],
                "model_tier": ModelTier.OPUS,
                "system_prompt": (
                    "Sos el Planner del equipo. Planificás tareas, estimás "
                    "esfuerzos y definís prioridades para el equipo de desarrollo."
                ),
                "tools": ["tasks", "calendar"],
                "cost_per_1k_tokens": 0.015,
            },
            {
                "id": "spec_writer",
                "name": "Spec Writer",
                "role": "spec_writer",
                "description": "Escribe especificaciones técnicas y documentación detallada.",
                "capabilities": [AgentCapability.SPEC, AgentCapability.DOCUMENT],
                "model_tier": ModelTier.OPUS,
                "system_prompt": (
                    "Sos el Spec Writer. Escribís especificaciones técnicas "
                    "detalladas y documentación clara para el equipo."
                ),
                "tools": ["documents", "templates"],
                "cost_per_1k_tokens": 0.015,
            },
            {
                "id": "proposal_writer",
                "name": "Proposal Writer",
                "role": "proposal_writer",
                "description": "Redacta propuestas de solución y documentos de decisión.",
                "capabilities": [AgentCapability.PROPOSE, AgentCapability.DOCUMENT],
                "model_tier": ModelTier.OPUS,
                "system_prompt": (
                    "Sos el Proposal Writer. Redactás propuestas de solución "
                    "y documentos de decisión técnica para el equipo."
                ),
                "tools": ["documents", "templates"],
                "cost_per_1k_tokens": 0.015,
            },
            {
                "id": "security_reviewer",
                "name": "Security Reviewer",
                "role": "security_reviewer",
                "description": "Revisa código y arquitectura en busca de vulnerabilidades.",
                "capabilities": [AgentCapability.SECURITY, AgentCapability.REVIEW],
                "model_tier": ModelTier.OPUS,
                "system_prompt": (
                    "Sos el Security Reviewer. Revisás código y arquitectura "
                    "en busca de vulnerabilidades y problemas de seguridad."
                ),
                "tools": ["code_search", "security_scanner"],
                "cost_per_1k_tokens": 0.015,
            },
            {
                "id": "implementer",
                "name": "Implementer",
                "role": "implementer",
                "description": "Implementa código siguiendo las especificaciones definidas.",
                "capabilities": [AgentCapability.IMPLEMENT],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Implementer. Implementás código limpio y eficiente "
                    "siguiendo las especificaciones y estándares del equipo."
                ),
                "tools": ["code_editor", "terminal"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "code_reviewer",
                "name": "Code Reviewer",
                "role": "code_reviewer",
                "description": "Revisa código para calidad, legibilidad y buenas prácticas.",
                "capabilities": [AgentCapability.REVIEW],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Code Reviewer. Revisás código enfocándote en calidad, "
                    "legibilidad y buenas prácticas de desarrollo."
                ),
                "tools": ["code_search", "linter"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "test_runner",
                "name": "Test Runner",
                "role": "test_runner",
                "description": "Escribe y ejecuta tests unitarios e integrales.",
                "capabilities": [AgentCapability.TEST],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Test Runner. Escribís y ejecutás tests unitarios "
                    "e integrales para asegurar la calidad del código."
                ),
                "tools": ["test_framework", "terminal"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "doc_updater",
                "name": "Doc Updater",
                "role": "doc_updater",
                "description": "Actualiza documentación técnica y de usuario.",
                "capabilities": [AgentCapability.DOCUMENT],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Doc Updater. Actualizás la documentación técnica "
                    "y de usuario manteniéndola clara y al día."
                ),
                "tools": ["documents", "templates"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "sales_qualifier",
                "name": "Sales Qualifier",
                "role": "sales_qualifier",
                "description": "Califica leads y analiza potencial de conversión.",
                "capabilities": [AgentCapability.QUALIFY, AgentCapability.ANALYZE],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Sales Qualifier. Calificás leads evaluando su "
                    "potencial de conversión y ajuste al perfil ideal de cliente."
                ),
                "tools": ["crm", "scoring"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "outreach_composer",
                "name": "Outreach Composer",
                "role": "outreach_composer",
                "description": "Compone mensajes de outreach personalizados.",
                "capabilities": [AgentCapability.OUTREACH],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Outreach Composer. Componés mensajes de outreach "
                    "personalizados y efectivos para cada etapa del funnel."
                ),
                "tools": ["templates", "crm"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "support_responder",
                "name": "Support Responder",
                "role": "support_responder",
                "description": "Genera respuestas de soporte técnico al cliente.",
                "capabilities": [AgentCapability.SUPPORT],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Support Responder. Generás respuestas de soporte "
                    "técnico claras y empáticas para resolver problemas del cliente."
                ),
                "tools": ["knowledge_base", "tickets"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "ticket_router",
                "name": "Ticket Router",
                "role": "ticket_router",
                "description": "Clasifica y enruta tickets al equipo correcto.",
                "capabilities": [AgentCapability.CLASSIFY],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Ticket Router. Clasificás tickets según su tipo "
                    "y urgencia, y los enrutás al equipo más adecuado."
                ),
                "tools": ["tickets", "routing"],
                "cost_per_1k_tokens": 0.003,
            },
            {
                "id": "analytics_reporter",
                "name": "Analytics Reporter",
                "role": "analytics_reporter",
                "description": "Genera reportes analíticos de ventas y soporte.",
                "capabilities": [AgentCapability.ANALYZE],
                "model_tier": ModelTier.SONNET,
                "system_prompt": (
                    "Sos el Analytics Reporter. Generás reportes analíticos "
                    "claros sobre métricas de ventas, soporte y rendimiento."
                ),
                "tools": ["analytics", "reports"],
                "cost_per_1k_tokens": 0.003,
            },
        ]

        for d in defaults:
            self.register(
                AgentProfile(
                    id=d["id"],
                    name=d["name"],
                    role=d["role"],
                    description=d["description"],
                    capabilities=d["capabilities"],
                    model_tier=d["model_tier"],
                    system_prompt=d["system_prompt"],
                    tools=d["tools"],
                    cost_per_1k_tokens=d["cost_per_1k_tokens"],
                )
            )


# Module-level singleton
agent_registry = AgentRegistry()
