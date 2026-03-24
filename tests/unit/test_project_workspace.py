"""Tests for project_workspace module — 22+ tests covering workspace lifecycle."""

from datetime import datetime

import pytest

from xcapitsff.core.project_workspace import (
    PhaseGate,
    ProjectPhase,
    ProjectStatus,
    Workspace,
    WorkspaceManager,
)


@pytest.fixture
def manager():
    return WorkspaceManager()


@pytest.fixture
def workspace(manager):
    return manager.create("tenant-1", "Project Alpha", "Acme Corp")


# --- Creation ---


class TestWorkspaceCreation:
    def test_create_workspace_basic(self, manager):
        ws = manager.create("t1", "My Project", "Client A")
        assert ws.id.startswith("WS-")
        assert ws.tenant_id == "t1"
        assert ws.name == "My Project"
        assert ws.client_name == "Client A"
        assert ws.status == ProjectStatus.DRAFT
        assert ws.current_phase == ProjectPhase.DISCOVERY

    def test_create_workspace_with_description_and_config(self, manager):
        ws = manager.create(
            "t1", "Proj", "Client", description="desc", config={"key": "val"}
        )
        assert ws.description == "desc"
        assert ws.config == {"key": "val"}

    def test_create_workspace_default_gates(self, workspace):
        gates = workspace.phase_gates
        assert len(gates) == 8
        # DISCOVERY gate does not require approval
        discovery_gate = gates[0]
        assert discovery_gate.phase == ProjectPhase.DISCOVERY
        assert discovery_gate.requires_approval is False
        # SPECIFICATION gate requires approval with artifacts
        spec_gate = gates[1]
        assert spec_gate.phase == ProjectPhase.SPECIFICATION
        assert spec_gate.requires_approval is True
        assert "spec" in spec_gate.artifacts_required
        assert "prd" in spec_gate.artifacts_required

    def test_create_workspace_timestamps(self, workspace):
        assert isinstance(workspace.created_at, datetime)
        assert isinstance(workspace.updated_at, datetime)

    def test_create_workspace_empty_lists(self, workspace):
        assert workspace.phases_completed == []
        assert workspace.requirements == []
        assert workspace.tags == []


# --- Phase Advancement ---


class TestPhaseAdvancement:
    def test_advance_from_discovery(self, manager, workspace):
        # DISCOVERY gate does NOT require approval
        result = manager.advance_phase(workspace.id)
        assert result is not None
        assert result.current_phase == ProjectPhase.SPECIFICATION
        assert ProjectPhase.DISCOVERY in result.phases_completed

    def test_advance_blocked_without_approval(self, manager, workspace):
        # Advance past DISCOVERY (no approval needed)
        manager.advance_phase(workspace.id)
        # Now at SPECIFICATION, which requires approval
        result = manager.advance_phase(workspace.id)
        assert result is None  # blocked
        assert workspace.current_phase == ProjectPhase.SPECIFICATION

    def test_advance_after_approval(self, manager, workspace):
        manager.advance_phase(workspace.id)  # DISCOVERY → SPECIFICATION
        # Approve the SPECIFICATION gate
        gate = manager.get_current_gate(workspace.id)
        gate.approved_by = "admin"
        gate.approved_at = datetime.now()
        result = manager.advance_phase(workspace.id)
        assert result is not None
        assert result.current_phase == ProjectPhase.PLANNING

    def test_advance_full_sequence(self, manager, workspace):
        phases = list(ProjectPhase)
        for i in range(len(phases) - 1):
            gate = manager.get_current_gate(workspace.id)
            if gate and gate.requires_approval:
                gate.approved_by = "admin"
                gate.approved_at = datetime.now()
            result = manager.advance_phase(workspace.id)
            assert result is not None
            assert result.current_phase == phases[i + 1]
        # At MAINTENANCE, cannot advance further
        result = manager.advance_phase(workspace.id)
        assert result is None

    def test_advance_nonexistent_workspace(self, manager):
        result = manager.advance_phase("WS-9999")
        assert result is None

    def test_phases_completed_accumulates(self, manager, workspace):
        manager.advance_phase(workspace.id)  # DISCOVERY → SPECIFICATION
        assert len(workspace.phases_completed) == 1
        gate = manager.get_current_gate(workspace.id)
        gate.approved_by = "admin"
        gate.approved_at = datetime.now()
        manager.advance_phase(workspace.id)  # SPECIFICATION → PLANNING
        assert len(workspace.phases_completed) == 2


# --- Gate Validation ---


class TestGateValidation:
    def test_get_current_gate_discovery(self, manager, workspace):
        gate = manager.get_current_gate(workspace.id)
        assert gate is not None
        assert gate.phase == ProjectPhase.DISCOVERY
        assert gate.requires_approval is False

    def test_get_current_gate_nonexistent(self, manager):
        gate = manager.get_current_gate("WS-0000")
        assert gate is None

    def test_get_phase_status(self, manager, workspace):
        status = manager.get_phase_status(workspace.id)
        assert status["current_phase"] == "discovery"
        assert status["next_phase"] == "specification"
        assert status["phases_completed"] == 0
        assert status["gate"]["requires_approval"] is False

    def test_get_phase_status_nonexistent(self, manager):
        status = manager.get_phase_status("WS-0000")
        assert status == {}


# --- Requirements ---


class TestRequirements:
    def test_add_requirement(self, manager, workspace):
        result = manager.add_requirement(workspace.id, "Must support SSO")
        assert result is True
        reqs = manager.get_requirements(workspace.id)
        assert "Must support SSO" in reqs

    def test_add_multiple_requirements(self, manager, workspace):
        manager.add_requirement(workspace.id, "Req 1")
        manager.add_requirement(workspace.id, "Req 2")
        reqs = manager.get_requirements(workspace.id)
        assert len(reqs) == 2

    def test_get_requirements_nonexistent(self, manager):
        reqs = manager.get_requirements("WS-0000")
        assert reqs == []

    def test_add_requirement_nonexistent(self, manager):
        result = manager.add_requirement("WS-0000", "req")
        assert result is False


# --- Status Transitions ---


class TestStatusTransitions:
    def test_activate(self, manager, workspace):
        assert manager.activate(workspace.id) is True
        assert workspace.status == ProjectStatus.ACTIVE

    def test_put_on_hold(self, manager, workspace):
        assert manager.put_on_hold(workspace.id) is True
        assert workspace.status == ProjectStatus.ON_HOLD

    def test_complete(self, manager, workspace):
        assert manager.complete(workspace.id) is True
        assert workspace.status == ProjectStatus.COMPLETED

    def test_archive(self, manager, workspace):
        assert manager.archive(workspace.id) is True
        assert workspace.status == ProjectStatus.ARCHIVED

    def test_status_transition_nonexistent(self, manager):
        assert manager.activate("WS-0000") is False
        assert manager.put_on_hold("WS-0000") is False
        assert manager.complete("WS-0000") is False
        assert manager.archive("WS-0000") is False


# --- List / Filter ---


class TestListFilter:
    def test_list_all(self, manager):
        manager.create("t1", "P1", "C1")
        manager.create("t2", "P2", "C2")
        assert len(manager.list_workspaces()) == 2

    def test_list_by_tenant(self, manager):
        manager.create("t1", "P1", "C1")
        manager.create("t2", "P2", "C2")
        result = manager.list_workspaces(tenant_id="t1")
        assert len(result) == 1
        assert result[0].tenant_id == "t1"

    def test_list_by_status(self, manager):
        ws = manager.create("t1", "P1", "C1")
        manager.create("t1", "P2", "C2")
        manager.activate(ws.id)
        result = manager.list_workspaces(status=ProjectStatus.ACTIVE)
        assert len(result) == 1


# --- Update ---


class TestUpdate:
    def test_update_workspace(self, manager, workspace):
        result = manager.update_workspace(workspace.id, name="New Name", description="new desc")
        assert result is not None
        assert result.name == "New Name"
        assert result.description == "new desc"

    def test_update_nonexistent(self, manager):
        result = manager.update_workspace("WS-0000", name="X")
        assert result is None

    def test_update_does_not_change_id(self, manager, workspace):
        original_id = workspace.id
        manager.update_workspace(workspace.id, id="WS-HACK")
        assert workspace.id == original_id


# --- Stats ---


class TestStats:
    def test_stats_empty(self, manager):
        stats = manager.get_stats()
        assert stats["total"] == 0
        assert stats["by_status"] == {}
        assert stats["by_phase"] == {}

    def test_stats_with_workspaces(self, manager):
        ws1 = manager.create("t1", "P1", "C1")
        manager.create("t1", "P2", "C2")
        manager.activate(ws1.id)
        stats = manager.get_stats()
        assert stats["total"] == 2
        assert stats["by_status"]["active"] == 1
        assert stats["by_status"]["draft"] == 1
        assert stats["by_phase"]["discovery"] == 2


# --- Get Workspace ---


class TestGetWorkspace:
    def test_get_workspace(self, manager, workspace):
        result = manager.get_workspace(workspace.id)
        assert result is workspace

    def test_get_workspace_nonexistent(self, manager):
        result = manager.get_workspace("WS-0000")
        assert result is None
