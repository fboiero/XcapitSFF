"""Project Workspace — manages project lifecycle phases and gates.

Provides workspace creation, phase advancement with gate validation,
requirements tracking, and status management for the agent orchestration layer.
"""

import logging
import random
import string
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ProjectPhase(str, Enum):
    DISCOVERY = "discovery"
    SPECIFICATION = "specification"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    MAINTENANCE = "maintenance"


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


# Ordered list for phase advancement
_PHASE_ORDER = list(ProjectPhase)


def _generate_id(prefix: str) -> str:
    digits = "".join(random.choices(string.digits, k=4))
    return f"{prefix}-{digits}"


@dataclass
class PhaseGate:
    phase: ProjectPhase
    requires_approval: bool = True
    approved_by: str | None = None
    approved_at: datetime | None = None
    artifacts_required: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Workspace:
    id: str
    tenant_id: str
    name: str
    client_name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    current_phase: ProjectPhase = ProjectPhase.DISCOVERY
    phases_completed: list[ProjectPhase] = field(default_factory=list)
    phase_gates: list[PhaseGate] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


def _default_phase_gates() -> list[PhaseGate]:
    """Create the default set of phase gates for a new workspace."""
    return [
        PhaseGate(phase=ProjectPhase.DISCOVERY, requires_approval=False),
        PhaseGate(
            phase=ProjectPhase.SPECIFICATION,
            requires_approval=True,
            artifacts_required=["spec", "prd"],
        ),
        PhaseGate(
            phase=ProjectPhase.PLANNING,
            requires_approval=True,
            artifacts_required=["proposal"],
        ),
        PhaseGate(phase=ProjectPhase.IMPLEMENTATION, requires_approval=False),
        PhaseGate(phase=ProjectPhase.TESTING, requires_approval=False),
        PhaseGate(
            phase=ProjectPhase.REVIEW,
            requires_approval=True,
            artifacts_required=["code", "test", "review"],
        ),
        PhaseGate(
            phase=ProjectPhase.DEPLOYMENT,
            requires_approval=True,
            artifacts_required=["document"],
        ),
        PhaseGate(phase=ProjectPhase.MAINTENANCE, requires_approval=False),
    ]


class WorkspaceManager:
    """Manages project workspaces, phase transitions, and gate validation."""

    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}

    def create(
        self,
        tenant_id: str,
        name: str,
        client_name: str,
        description: str = "",
        config: dict[str, Any] | None = None,
    ) -> Workspace:
        ws = Workspace(
            id=_generate_id("WS"),
            tenant_id=tenant_id,
            name=name,
            client_name=client_name,
            description=description,
            config=config or {},
            phase_gates=_default_phase_gates(),
        )
        self._workspaces[ws.id] = ws
        logger.info(f"Workspace created: {ws.id} ({ws.name})")
        return ws

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self._workspaces.get(workspace_id)

    def list_workspaces(
        self,
        tenant_id: str | None = None,
        status: ProjectStatus | None = None,
    ) -> list[Workspace]:
        result = list(self._workspaces.values())
        if tenant_id is not None:
            result = [w for w in result if w.tenant_id == tenant_id]
        if status is not None:
            result = [w for w in result if w.status == status]
        return result

    def update_workspace(self, workspace_id: str, **kwargs: Any) -> Workspace | None:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return None
        for key, value in kwargs.items():
            if hasattr(ws, key) and key not in ("id", "created_at"):
                setattr(ws, key, value)
        ws.updated_at = datetime.now()
        return ws

    def advance_phase(self, workspace_id: str) -> Workspace | None:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return None

        current_idx = _PHASE_ORDER.index(ws.current_phase)
        if current_idx >= len(_PHASE_ORDER) - 1:
            logger.warning(f"Workspace {workspace_id} already at final phase")
            return None

        gate = self.get_current_gate(workspace_id)
        if gate and gate.requires_approval and gate.approved_by is None:
            logger.warning(
                f"Workspace {workspace_id}: gate for {ws.current_phase.value} "
                "requires approval before advancing"
            )
            return None

        ws.phases_completed.append(ws.current_phase)
        ws.current_phase = _PHASE_ORDER[current_idx + 1]
        ws.updated_at = datetime.now()
        logger.info(f"Workspace {workspace_id} advanced to {ws.current_phase.value}")
        return ws

    def get_phase_status(self, workspace_id: str) -> dict[str, Any]:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return {}

        current_idx = _PHASE_ORDER.index(ws.current_phase)
        next_phase = (
            _PHASE_ORDER[current_idx + 1].value
            if current_idx < len(_PHASE_ORDER) - 1
            else None
        )
        gate = self.get_current_gate(workspace_id)

        return {
            "current_phase": ws.current_phase.value,
            "gate": {
                "requires_approval": gate.requires_approval if gate else False,
                "approved_by": gate.approved_by if gate else None,
                "artifacts_required": gate.artifacts_required if gate else [],
            },
            "next_phase": next_phase,
            "phases_completed": len(ws.phases_completed),
        }

    def get_current_gate(self, workspace_id: str) -> PhaseGate | None:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return None
        for gate in ws.phase_gates:
            if gate.phase == ws.current_phase:
                return gate
        return None

    def add_requirement(self, workspace_id: str, requirement: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.requirements.append(requirement)
        ws.updated_at = datetime.now()
        return True

    def get_requirements(self, workspace_id: str) -> list[str]:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return []
        return list(ws.requirements)

    def activate(self, workspace_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.status = ProjectStatus.ACTIVE
        ws.updated_at = datetime.now()
        return True

    def put_on_hold(self, workspace_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.status = ProjectStatus.ON_HOLD
        ws.updated_at = datetime.now()
        return True

    def complete(self, workspace_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.status = ProjectStatus.COMPLETED
        ws.updated_at = datetime.now()
        return True

    def archive(self, workspace_id: str) -> bool:
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            return False
        ws.status = ProjectStatus.ARCHIVED
        ws.updated_at = datetime.now()
        return True

    def get_stats(self) -> dict[str, Any]:
        workspaces = list(self._workspaces.values())
        total = len(workspaces)
        by_status: dict[str, int] = {}
        by_phase: dict[str, int] = {}
        for ws in workspaces:
            by_status[ws.status.value] = by_status.get(ws.status.value, 0) + 1
            by_phase[ws.current_phase.value] = (
                by_phase.get(ws.current_phase.value, 0) + 1
            )
        return {
            "total": total,
            "by_status": by_status,
            "by_phase": by_phase,
        }


# Module-level singleton
workspace_manager = WorkspaceManager()
