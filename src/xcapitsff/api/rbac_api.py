"""API endpoints for Role-Based Access Control (RBAC)."""

from fastapi import APIRouter, HTTPException, Query

from xcapitsff.core.rbac import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
    rbac_manager,
)

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


@router.get("/")
async def list_roles():
    """List all roles with their default permissions."""
    return {
        "roles": [
            {
                "role": role.value,
                "permissions": sorted(p.value for p in perms),
                "count": len(perms),
            }
            for role, perms in ROLE_PERMISSIONS.items()
        ]
    }


@router.get("/users")
async def list_users(
    tenant_id: str = Query(default="default", description="Tenant identifier"),
):
    """List all users and their roles for a tenant."""
    users = rbac_manager.list_tenant_users(tenant_id)
    return {
        "tenant_id": tenant_id,
        "count": len(users),
        "users": [
            {
                "user_id": ur.user_id,
                "role": ur.role.value,
                "custom_permissions": sorted(p.value for p in ur.custom_permissions),
                "assigned_at": ur.assigned_at.isoformat(),
                "assigned_by": ur.assigned_by,
            }
            for ur in users
        ],
    }


@router.put("/users/{user_id}")
async def assign_role(
    user_id: str,
    role: str = Query(description="Role to assign"),
    tenant_id: str = Query(default="default", description="Tenant identifier"),
    assigned_by: str = Query(default="system", description="Who is assigning the role"),
):
    """Assign or change a user's role."""
    try:
        role_enum = Role(role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {role}. Valid roles: {[r.value for r in Role]}",
        )

    user_role = rbac_manager.assign_role(tenant_id, user_id, role_enum, assigned_by)
    return {
        "user_id": user_role.user_id,
        "tenant_id": user_role.tenant_id,
        "role": user_role.role.value,
        "assigned_at": user_role.assigned_at.isoformat(),
        "assigned_by": user_role.assigned_by,
    }


@router.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: str,
    tenant_id: str = Query(default="default", description="Tenant identifier"),
):
    """Get a user's effective permissions (role defaults + custom)."""
    role = rbac_manager.get_role(tenant_id, user_id)
    permissions = rbac_manager.get_user_permissions(tenant_id, user_id)
    user_role = rbac_manager.get_user_role(tenant_id, user_id)

    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role.value,
        "permissions": sorted(p.value for p in permissions),
        "custom_permissions": sorted(p.value for p in user_role.custom_permissions),
        "total": len(permissions),
    }


@router.post("/users/{user_id}/permissions")
async def add_custom_permission(
    user_id: str,
    permission: str = Query(description="Permission to grant"),
    tenant_id: str = Query(default="default", description="Tenant identifier"),
):
    """Add a custom permission to a user beyond their role defaults."""
    try:
        perm_enum = Permission(permission)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission: {permission}. Valid permissions: {[p.value for p in Permission]}",
        )

    rbac_manager.add_custom_permission(tenant_id, user_id, perm_enum)
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "permission": permission,
        "status": "granted",
    }


@router.delete("/users/{user_id}/permissions/{permission}")
async def remove_custom_permission(
    user_id: str,
    permission: str,
    tenant_id: str = Query(default="default", description="Tenant identifier"),
):
    """Remove a custom permission from a user."""
    try:
        perm_enum = Permission(permission)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission: {permission}.",
        )

    rbac_manager.remove_custom_permission(tenant_id, user_id, perm_enum)
    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "permission": permission,
        "status": "removed",
    }


@router.get("/check")
async def check_permission(
    permission: str = Query(description="Permission to check"),
    user_id: str = Query(default="current_user", description="User to check"),
    tenant_id: str = Query(default="default", description="Tenant identifier"),
):
    """Check if a user has a specific permission."""
    try:
        perm_enum = Permission(permission)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permission: {permission}.",
        )

    has_permission = rbac_manager.check_permission(tenant_id, user_id, perm_enum)
    role = rbac_manager.get_role(tenant_id, user_id)

    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "permission": permission,
        "allowed": has_permission,
        "role": role.value,
    }
