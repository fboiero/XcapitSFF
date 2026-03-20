"""API endpoints for email verification, password reset, and invitations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xcapitsff.core.auth import hash_password
from xcapitsff.core.email_verification import (
    EmailVerificationManager,
    InvitationManager,
    InvitationStatus,
    PasswordResetManager,
    email_verification_manager,
    invitation_manager,
    password_reset_manager,
)

router = APIRouter(tags=["Verification & Invitations"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    user_id: str


class ForgotPasswordRequest(BaseModel):
    email: str
    tenant_id: str = ""
    user_id: str = ""


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class CreateInvitationRequest(BaseModel):
    tenant_id: str
    inviter_id: str
    email: str
    role: str = "member"


class AcceptInvitationRequest(BaseModel):
    pass  # token comes from path


class VerificationResponse(BaseModel):
    detail: str
    token: str | None = None
    email: str | None = None


class InvitationResponse(BaseModel):
    id: str
    token: str
    tenant_id: str
    inviter_id: str
    email: str
    role: str
    status: str
    created_at: str
    expires_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _invitation_response(inv) -> InvitationResponse:
    return InvitationResponse(
        id=inv.id,
        token=inv.token,
        tenant_id=inv.tenant_id,
        inviter_id=inv.inviter_id,
        email=inv.email,
        role=inv.role,
        status=inv.status.value if hasattr(inv.status, "value") else inv.status,
        created_at=inv.created_at.isoformat(),
        expires_at=inv.expires_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Email Verification endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/verify-email", response_model=VerificationResponse)
async def api_verify_email(
    data: VerifyEmailRequest,
    _vm: EmailVerificationManager = Depends(lambda: email_verification_manager),
):
    """Verify an email address with the provided token."""
    vt = _vm.verify_token(data.token)
    if vt is None:
        raise HTTPException(status_code=400, detail="Invalid, expired, or already used token")
    return VerificationResponse(
        detail="Email verified successfully",
        email=vt.email,
    )


@router.post("/auth/resend-verification", response_model=VerificationResponse)
async def api_resend_verification(
    data: ResendVerificationRequest,
    _vm: EmailVerificationManager = Depends(lambda: email_verification_manager),
):
    """Resend the verification email for a user."""
    vt = _vm.resend_verification(data.user_id)
    if vt is None:
        raise HTTPException(status_code=404, detail="No existing verification found for this user")
    return VerificationResponse(
        detail="Verification email resent",
        token=vt.token,
        email=vt.email,
    )


# ---------------------------------------------------------------------------
# Password Reset endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/forgot-password", response_model=VerificationResponse)
async def api_forgot_password(
    data: ForgotPasswordRequest,
    _pm: PasswordResetManager = Depends(lambda: password_reset_manager),
):
    """Request a password reset token."""
    vt = _pm.request_reset(
        email=data.email,
        tenant_id=data.tenant_id,
        user_id=data.user_id,
    )
    return VerificationResponse(
        detail="Password reset token created",
        token=vt.token,
        email=vt.email,
    )


@router.post("/auth/reset-password", response_model=VerificationResponse)
async def api_reset_password(
    data: ResetPasswordRequest,
    _pm: PasswordResetManager = Depends(lambda: password_reset_manager),
):
    """Complete a password reset using the token and new password."""
    ok = _pm.complete_reset(data.token, hash_password(data.new_password))
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid, expired, or already used reset token")
    return VerificationResponse(detail="Password reset successfully")


# ---------------------------------------------------------------------------
# Invitation endpoints
# ---------------------------------------------------------------------------

@router.post("/invitations", response_model=InvitationResponse, status_code=201)
async def api_create_invitation(
    data: CreateInvitationRequest,
    _im: InvitationManager = Depends(lambda: invitation_manager),
):
    """Create a new team invitation."""
    try:
        inv = _im.create_invitation(
            tenant_id=data.tenant_id,
            inviter_id=data.inviter_id,
            email=data.email,
            role=data.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return _invitation_response(inv)


@router.get("/invitations", response_model=list[InvitationResponse])
async def api_list_invitations(
    tenant_id: str,
    _im: InvitationManager = Depends(lambda: invitation_manager),
):
    """List all pending invitations for a tenant."""
    invitations = _im.list_pending(tenant_id)
    return [_invitation_response(inv) for inv in invitations]


@router.post("/invitations/{token}/accept", response_model=InvitationResponse)
async def api_accept_invitation(
    token: str,
    _im: InvitationManager = Depends(lambda: invitation_manager),
):
    """Accept an invitation by its token."""
    inv = _im.accept_invitation(token)
    if inv is None:
        raise HTTPException(status_code=400, detail="Invalid, expired, or already used invitation")
    return _invitation_response(inv)


@router.delete("/invitations/{invitation_id}", status_code=200)
async def api_revoke_invitation(
    invitation_id: str,
    _im: InvitationManager = Depends(lambda: invitation_manager),
):
    """Revoke a pending invitation."""
    ok = _im.revoke_invitation(invitation_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Invitation not found or not pending")
    return {"detail": "Invitation revoked"}
