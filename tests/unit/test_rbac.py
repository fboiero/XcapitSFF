"""Tests for the RBAC system — roles, permissions, and multi-tenant isolation."""

import pytest

from xcapitsff.core.rbac import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    RBACManager,
    UserRole,
)


@pytest.fixture
def manager():
    """Fresh RBACManager for each test."""
    return RBACManager()


# --- Role assignment ---


class TestRoleAssignment:
    def test_assign_role(self, manager: RBACManager):
        ur = manager.assign_role("t1", "u1", Role.ADMIN)
        assert ur.role == Role.ADMIN
        assert ur.user_id == "u1"
        assert ur.tenant_id == "t1"

    def test_assign_role_updates_existing(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.AGENT)
        ur = manager.assign_role("t1", "u1", Role.MANAGER)
        assert ur.role == Role.MANAGER

    def test_assign_role_preserves_custom_permissions(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.AGENT)
        manager.add_custom_permission("t1", "u1", Permission.BILLING_VIEW)
        ur = manager.assign_role("t1", "u1", Role.MANAGER)
        assert Permission.BILLING_VIEW in ur.custom_permissions

    def test_assign_role_records_assigned_by(self, manager: RBACManager):
        ur = manager.assign_role("t1", "u1", Role.ADMIN, assigned_by="admin_user")
        assert ur.assigned_by == "admin_user"

    def test_get_role_returns_assigned_role(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.MANAGER)
        assert manager.get_role("t1", "u1") == Role.MANAGER

    def test_get_role_defaults_to_viewer(self, manager: RBACManager):
        assert manager.get_role("t1", "unknown_user") == Role.VIEWER


# --- Default role permissions ---


class TestRolePermissions:
    def test_owner_has_all_permissions(self):
        owner_perms = ROLE_PERMISSIONS[Role.OWNER]
        for perm in Permission:
            assert perm in owner_perms, f"OWNER missing {perm.value}"

    def test_admin_has_all_except_billing_manage(self):
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.BILLING_MANAGE not in admin_perms
        # Verify admin has everything else
        for perm in Permission:
            if perm != Permission.BILLING_MANAGE:
                assert perm in admin_perms, f"ADMIN missing {perm.value}"

    def test_viewer_can_only_view(self):
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        for perm in viewer_perms:
            assert perm.value.endswith(".view"), f"VIEWER has non-view perm: {perm.value}"

    def test_viewer_has_all_view_permissions(self):
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        for perm in Permission:
            if perm.value.endswith(".view"):
                assert perm in viewer_perms, f"VIEWER missing {perm.value}"

    def test_agent_cannot_delete(self):
        agent_perms = ROLE_PERMISSIONS[Role.AGENT]
        delete_perms = [p for p in Permission if "delete" in p.value]
        for perm in delete_perms:
            assert perm not in agent_perms, f"AGENT should not have {perm.value}"

    def test_agent_can_create(self):
        agent_perms = ROLE_PERMISSIONS[Role.AGENT]
        assert Permission.LEADS_CREATE in agent_perms
        assert Permission.TICKETS_CREATE in agent_perms
        assert Permission.CUSTOMERS_CREATE in agent_perms

    def test_agent_can_edit(self):
        agent_perms = ROLE_PERMISSIONS[Role.AGENT]
        assert Permission.LEADS_EDIT in agent_perms
        assert Permission.TICKETS_EDIT in agent_perms
        assert Permission.CUSTOMERS_EDIT in agent_perms

    def test_agent_cannot_assign(self):
        agent_perms = ROLE_PERMISSIONS[Role.AGENT]
        assert Permission.LEADS_ASSIGN not in agent_perms
        assert Permission.TICKETS_ASSIGN not in agent_perms

    def test_manager_has_team_invite(self):
        manager_perms = ROLE_PERMISSIONS[Role.MANAGER]
        assert Permission.TEAM_INVITE in manager_perms

    def test_manager_cannot_manage_team(self):
        manager_perms = ROLE_PERMISSIONS[Role.MANAGER]
        assert Permission.TEAM_MANAGE not in manager_perms
        assert Permission.TEAM_REMOVE not in manager_perms

    def test_manager_has_full_leads(self):
        manager_perms = ROLE_PERMISSIONS[Role.MANAGER]
        lead_perms = [p for p in Permission if p.value.startswith("leads.")]
        for perm in lead_perms:
            assert perm in manager_perms, f"MANAGER missing {perm.value}"

    def test_manager_has_full_campaigns(self):
        manager_perms = ROLE_PERMISSIONS[Role.MANAGER]
        campaign_perms = [p for p in Permission if p.value.startswith("campaigns.")]
        for perm in campaign_perms:
            assert perm in manager_perms, f"MANAGER missing {perm.value}"

    def test_all_permissions_count(self):
        """Verify we have 35+ permissions defined."""
        assert len(Permission) >= 35


# --- Permission checks ---


class TestPermissionCheck:
    def test_check_permission_for_assigned_role(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.ADMIN)
        assert manager.check_permission("t1", "u1", Permission.LEADS_VIEW) is True

    def test_check_permission_denied(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.VIEWER)
        assert manager.check_permission("t1", "u1", Permission.LEADS_DELETE) is False

    def test_check_permission_unknown_user_defaults_viewer(self, manager: RBACManager):
        # Unknown user defaults to VIEWER — can view but not edit
        assert manager.check_permission("t1", "nobody", Permission.LEADS_VIEW) is True
        assert manager.check_permission("t1", "nobody", Permission.LEADS_EDIT) is False

    def test_get_user_permissions_returns_set(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.AGENT)
        perms = manager.get_user_permissions("t1", "u1")
        assert isinstance(perms, set)
        assert Permission.LEADS_VIEW in perms
        assert Permission.LEADS_CREATE in perms
        assert Permission.LEADS_DELETE not in perms


# --- Custom permissions ---


class TestCustomPermissions:
    def test_add_custom_permission(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.VIEWER)
        manager.add_custom_permission("t1", "u1", Permission.LEADS_EDIT)
        assert manager.check_permission("t1", "u1", Permission.LEADS_EDIT) is True

    def test_custom_permission_in_effective_set(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.VIEWER)
        manager.add_custom_permission("t1", "u1", Permission.CAMPAIGNS_LAUNCH)
        perms = manager.get_user_permissions("t1", "u1")
        assert Permission.CAMPAIGNS_LAUNCH in perms

    def test_remove_custom_permission(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.VIEWER)
        manager.add_custom_permission("t1", "u1", Permission.LEADS_EDIT)
        manager.remove_custom_permission("t1", "u1", Permission.LEADS_EDIT)
        assert manager.check_permission("t1", "u1", Permission.LEADS_EDIT) is False

    def test_remove_nonexistent_custom_permission_is_safe(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.AGENT)
        # Should not raise
        manager.remove_custom_permission("t1", "u1", Permission.BILLING_MANAGE)

    def test_add_custom_permission_to_unassigned_user(self, manager: RBACManager):
        # Should create a VIEWER entry and add the custom perm
        manager.add_custom_permission("t1", "new_user", Permission.SETTINGS_EDIT)
        assert manager.check_permission("t1", "new_user", Permission.SETTINGS_EDIT) is True
        assert manager.get_role("t1", "new_user") == Role.VIEWER


# --- List users ---


class TestListUsers:
    def test_list_users_with_role(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.AGENT)
        manager.assign_role("t1", "u2", Role.AGENT)
        manager.assign_role("t1", "u3", Role.MANAGER)
        agents = manager.list_users_with_role("t1", Role.AGENT)
        assert len(agents) == 2
        user_ids = {ur.user_id for ur in agents}
        assert user_ids == {"u1", "u2"}

    def test_list_users_with_role_empty(self, manager: RBACManager):
        result = manager.list_users_with_role("t1", Role.OWNER)
        assert result == []

    def test_list_tenant_users(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.ADMIN)
        manager.assign_role("t1", "u2", Role.AGENT)
        users = manager.list_tenant_users("t1")
        assert len(users) == 2


# --- Multi-tenant isolation ---


class TestMultiTenantIsolation:
    def test_same_user_different_tenants(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.ADMIN)
        manager.assign_role("t2", "u1", Role.VIEWER)
        assert manager.get_role("t1", "u1") == Role.ADMIN
        assert manager.get_role("t2", "u1") == Role.VIEWER

    def test_permissions_isolated_across_tenants(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.ADMIN)
        manager.assign_role("t2", "u1", Role.VIEWER)
        assert manager.check_permission("t1", "u1", Permission.LEADS_DELETE) is True
        assert manager.check_permission("t2", "u1", Permission.LEADS_DELETE) is False

    def test_custom_permissions_isolated_across_tenants(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.VIEWER)
        manager.assign_role("t2", "u1", Role.VIEWER)
        manager.add_custom_permission("t1", "u1", Permission.BILLING_MANAGE)
        assert manager.check_permission("t1", "u1", Permission.BILLING_MANAGE) is True
        assert manager.check_permission("t2", "u1", Permission.BILLING_MANAGE) is False

    def test_list_users_isolated_across_tenants(self, manager: RBACManager):
        manager.assign_role("t1", "u1", Role.AGENT)
        manager.assign_role("t2", "u2", Role.AGENT)
        t1_agents = manager.list_users_with_role("t1", Role.AGENT)
        t2_agents = manager.list_users_with_role("t2", Role.AGENT)
        assert len(t1_agents) == 1
        assert t1_agents[0].user_id == "u1"
        assert len(t2_agents) == 1
        assert t2_agents[0].user_id == "u2"


# --- UserRole dataclass ---


class TestUserRole:
    def test_user_role_defaults(self):
        ur = UserRole(user_id="u1", tenant_id="t1", role=Role.AGENT)
        assert ur.custom_permissions == set()
        assert ur.assigned_by == "system"
        assert ur.assigned_at is not None

    def test_user_role_with_custom_perms(self):
        ur = UserRole(
            user_id="u1",
            tenant_id="t1",
            role=Role.VIEWER,
            custom_permissions={Permission.LEADS_EDIT, Permission.LEADS_DELETE},
        )
        assert len(ur.custom_permissions) == 2
