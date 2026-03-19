"""API endpoints for authentication."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr

from xcapitsff.core.auth import (
    AuthManager,
    UserRole,
    auth_manager,
    decode_access_token,
)
from xcapitsff.core.tenancy import (
    TenantManager,
    set_current_tenant,
    tenant_manager,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    plan: str = "free"


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    tenant_id: str
    role: str
    is_active: bool
    created_at: str
    last_login: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def _user_response(user) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        email=user.email,
        name=user.name,
        tenant_id=user.tenant_id,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
    )


def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    _auth: AuthManager = Depends(lambda: auth_manager),
) -> dict:
    """Extract and validate the JWT from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[7:]
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = _auth.get_user(payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Set tenant context for downstream code
    set_current_tenant(user.tenant_id)

    return {
        "user_id": user.user_id,
        "tenant_id": user.tenant_id,
        "role": user.role.value,
        "email": user.email,
        "user": user,
    }


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that enforces admin role."""
    if current_user["role"] != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=201)
async def api_register(
    data: RegisterRequest,
    _tm: TenantManager = Depends(lambda: tenant_manager),
    _auth: AuthManager = Depends(lambda: auth_manager),
):
    """Register a new user. Creates a tenant when this is the first user."""
    # Create a new tenant for the user
    try:
        tenant = _tm.create_tenant(
            name=f"{data.name}'s Organization",
            owner_email=data.email,
            plan=data.plan,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Register the user as admin of the new tenant
    try:
        user = _auth.register(
            email=data.email,
            password=data.password,
            name=data.name,
            tenant_id=tenant.tenant_id,
            role=UserRole.ADMIN,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    # Increment user usage
    _tm.increment_usage(tenant.tenant_id, "users")

    # Generate token
    result = _auth.login(data.email, data.password)
    if result is None:
        raise HTTPException(status_code=500, detail="Registration succeeded but login failed")

    logged_user, token = result
    return TokenResponse(
        access_token=token,
        user=_user_response(logged_user),
    )


@router.post("/login", response_model=TokenResponse)
async def api_login(
    data: LoginRequest,
    _auth: AuthManager = Depends(lambda: auth_manager),
):
    result = _auth.login(data.email, data.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user, token = result
    return TokenResponse(
        access_token=token,
        user=_user_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def api_me(current_user: dict = Depends(get_current_user)):
    return _user_response(current_user["user"])


@router.post("/change-password")
async def api_change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    _auth: AuthManager = Depends(lambda: auth_manager),
):
    ok = _auth.change_password(
        user_id=current_user["user_id"],
        old_password=data.old_password,
        new_password=data.new_password,
    )
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid current password")
    return {"detail": "Password changed"}


@router.get("/users", response_model=list[UserResponse])
async def api_list_users(
    current_user: dict = Depends(require_admin),
    _auth: AuthManager = Depends(lambda: auth_manager),
):
    """List all users in the current tenant (admin only)."""
    users = _auth.get_users_by_tenant(current_user["tenant_id"])
    return [_user_response(u) for u in users]
