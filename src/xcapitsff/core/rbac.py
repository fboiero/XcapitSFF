"""Role-Based Access Control (RBAC) — manages roles, permissions, and authorization.

Each tenant has its own set of user-role assignments. Users can have a base role
plus optional custom permissions that extend their access beyond the role default.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# --- Enums ---


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"


class Permission(str, Enum):
    # Leads
    LEADS_VIEW = "leads.view"
    LEADS_CREATE = "leads.create"
    LEADS_EDIT = "leads.edit"
    LEADS_DELETE = "leads.delete"
    LEADS_IMPORT = "leads.import"
    LEADS_EXPORT = "leads.export"
    LEADS_ASSIGN = "leads.assign"

    # Tickets
    TICKETS_VIEW = "tickets.view"
    TICKETS_CREATE = "tickets.create"
    TICKETS_EDIT = "tickets.edit"
    TICKETS_DELETE = "tickets.delete"
    TICKETS_ASSIGN = "tickets.assign"
    TICKETS_ESCALATE = "tickets.escalate"

    # Customers
    CUSTOMERS_VIEW = "customers.view"
    CUSTOMERS_CREATE = "customers.create"
    CUSTOMERS_EDIT = "customers.edit"
    CUSTOMERS_DELETE = "customers.delete"

    # Analytics
    ANALYTICS_VIEW = "analytics.view"
    ANALYTICS_EXPORT = "analytics.export"

    # Campaigns
    CAMPAIGNS_VIEW = "campaigns.view"
    CAMPAIGNS_CREATE = "campaigns.create"
    CAMPAIGNS_EDIT = "campaigns.edit"
    CAMPAIGNS_DELETE = "campaigns.delete"
    CAMPAIGNS_LAUNCH = "campaigns.launch"

    # Settings
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"

    # Team
    TEAM_INVITE = "team.invite"
    TEAM_MANAGE = "team.manage"
    TEAM_REMOVE = "team.remove"

    # Billing
    BILLING_VIEW = "billing.view"
    BILLING_MANAGE = "billing.manage"

    # API Keys
    API_KEYS_VIEW = "api_keys.view"
    API_KEYS_CREATE = "api_keys.create"
    API_KEYS_DELETE = "api_keys.delete"

    # Agents
    AGENTS_VIEW = "agents.view"
    AGENTS_CONFIGURE = "agents.configure"
    AGENTS_RUN = "agents.run"


# --- Role → Permission mapping ---

_ALL_PERMISSIONS = set(Permission)

_VIEW_PERMISSIONS = {p for p in Permission if p.value.endswith(".view")}

_MANAGER_PERMISSIONS = (
    # Leads — full access
    {
        Permission.LEADS_VIEW,
        Permission.LEADS_CREATE,
        Permission.LEADS_EDIT,
        Permission.LEADS_DELETE,
        Permission.LEADS_IMPORT,
        Permission.LEADS_EXPORT,
        Permission.LEADS_ASSIGN,
    }
    # Tickets — full access
    | {
        Permission.TICKETS_VIEW,
        Permission.TICKETS_CREATE,
        Permission.TICKETS_EDIT,
        Permission.TICKETS_DELETE,
        Permission.TICKETS_ASSIGN,
        Permission.TICKETS_ESCALATE,
    }
    # Customers — full access
    | {
        Permission.CUSTOMERS_VIEW,
        Permission.CUSTOMERS_CREATE,
        Permission.CUSTOMERS_EDIT,
        Permission.CUSTOMERS_DELETE,
    }
    # Campaigns — full access
    | {
        Permission.CAMPAIGNS_VIEW,
        Permission.CAMPAIGNS_CREATE,
        Permission.CAMPAIGNS_EDIT,
        Permission.CAMPAIGNS_DELETE,
        Permission.CAMPAIGNS_LAUNCH,
    }
    # Analytics — full access
    | {
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
    }
    # Agents — view + run
    | {
        Permission.AGENTS_VIEW,
        Permission.AGENTS_RUN,
    }
    # Team — invite only
    | {Permission.TEAM_INVITE}
    # Settings — view only
    | {Permission.SETTINGS_VIEW}
)

_AGENT_PERMISSIONS = {
    # Leads — view, create, edit
    Permission.LEADS_VIEW,
    Permission.LEADS_CREATE,
    Permission.LEADS_EDIT,
    # Tickets — view, create, edit
    Permission.TICKETS_VIEW,
    Permission.TICKETS_CREATE,
    Permission.TICKETS_EDIT,
    # Customers — view, create, edit
    Permission.CUSTOMERS_VIEW,
    Permission.CUSTOMERS_CREATE,
    Permission.CUSTOMERS_EDIT,
    # Analytics — view only
    Permission.ANALYTICS_VIEW,
    # Agents — view + run
    Permission.AGENTS_VIEW,
    Permission.AGENTS_RUN,
}

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.OWNER: _ALL_PERMISSIONS,
    Role.ADMIN: _ALL_PERMISSIONS - {Permission.BILLING_MANAGE},
    Role.MANAGER: _MANAGER_PERMISSIONS,
    Role.AGENT: _AGENT_PERMISSIONS,
    Role.VIEWER: _VIEW_PERMISSIONS,
}


# --- Data classes ---


@dataclass
class UserRole:
    user_id: str
    tenant_id: str
    role: Role
    custom_permissions: set[Permission] = field(default_factory=set)
    assigned_at: datetime = field(default_factory=datetime.now)
    assigned_by: str = "system"


# --- RBAC Manager ---


class RBACManager:
    """In-memory RBAC manager with multi-tenant isolation.

    Storage key: (tenant_id, user_id) → UserRole
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], UserRole] = {}

    def assign_role(
        self,
        tenant_id: str,
        user_id: str,
        role: Role,
        assigned_by: str = "system",
    ) -> UserRole:
        """Assign or update a user's role in a tenant."""
        key = (tenant_id, user_id)
        existing = self._store.get(key)
        custom = existing.custom_permissions if existing else set()

        user_role = UserRole(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            custom_permissions=custom,
            assigned_by=assigned_by,
        )
        self._store[key] = user_role
        logger.info(
            "Role assigned: user=%s tenant=%s role=%s by=%s",
            user_id,
            tenant_id,
            role.value,
            assigned_by,
        )
        return user_role

    def get_role(self, tenant_id: str, user_id: str) -> Role:
        """Get a user's role. Defaults to VIEWER if not assigned."""
        key = (tenant_id, user_id)
        entry = self._store.get(key)
        return entry.role if entry else Role.VIEWER

    def get_user_role(self, tenant_id: str, user_id: str) -> UserRole:
        """Get the full UserRole record. Creates a default VIEWER if missing."""
        key = (tenant_id, user_id)
        entry = self._store.get(key)
        if entry is None:
            entry = UserRole(
                user_id=user_id,
                tenant_id=tenant_id,
                role=Role.VIEWER,
            )
        return entry

    def check_permission(
        self, tenant_id: str, user_id: str, permission: Permission
    ) -> bool:
        """Check if a user has a specific permission (role-based + custom)."""
        user_role = self.get_user_role(tenant_id, user_id)
        role_perms = ROLE_PERMISSIONS.get(user_role.role, set())
        return permission in role_perms or permission in user_role.custom_permissions

    def get_user_permissions(self, tenant_id: str, user_id: str) -> set[Permission]:
        """Get the full effective permission set for a user."""
        user_role = self.get_user_role(tenant_id, user_id)
        role_perms = ROLE_PERMISSIONS.get(user_role.role, set())
        return role_perms | user_role.custom_permissions

    def list_users_with_role(self, tenant_id: str, role: Role) -> list[UserRole]:
        """List all users in a tenant that have a specific role."""
        return [
            ur
            for (tid, _), ur in self._store.items()
            if tid == tenant_id and ur.role == role
        ]

    def list_tenant_users(self, tenant_id: str) -> list[UserRole]:
        """List all users with assigned roles in a tenant."""
        return [
            ur for (tid, _), ur in self._store.items() if tid == tenant_id
        ]

    def add_custom_permission(
        self, tenant_id: str, user_id: str, permission: Permission
    ) -> None:
        """Grant an extra permission to a user beyond their role defaults."""
        key = (tenant_id, user_id)
        entry = self._store.get(key)
        if entry is None:
            entry = UserRole(
                user_id=user_id,
                tenant_id=tenant_id,
                role=Role.VIEWER,
            )
            self._store[key] = entry
        entry.custom_permissions.add(permission)
        logger.info(
            "Custom permission added: user=%s tenant=%s perm=%s",
            user_id,
            tenant_id,
            permission.value,
        )

    def remove_custom_permission(
        self, tenant_id: str, user_id: str, permission: Permission
    ) -> None:
        """Remove a custom permission from a user."""
        key = (tenant_id, user_id)
        entry = self._store.get(key)
        if entry is not None:
            entry.custom_permissions.discard(permission)
            logger.info(
                "Custom permission removed: user=%s tenant=%s perm=%s",
                user_id,
                tenant_id,
                permission.value,
            )


# Module-level singleton
rbac_manager = RBACManager()
