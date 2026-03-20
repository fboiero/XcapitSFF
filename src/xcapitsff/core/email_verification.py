"""Email verification, password reset, and invitation management."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VerificationPurpose(str, Enum):
    SIGNUP = "signup"
    PASSWORD_RESET = "password_reset"
    EMAIL_CHANGE = "email_change"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


# ---------------------------------------------------------------------------
# Default TTLs
# ---------------------------------------------------------------------------

_PURPOSE_TTL: dict[VerificationPurpose, timedelta] = {
    VerificationPurpose.SIGNUP: timedelta(hours=24),
    VerificationPurpose.PASSWORD_RESET: timedelta(hours=1),
    VerificationPurpose.EMAIL_CHANGE: timedelta(hours=24),
}

_INVITATION_TTL = timedelta(days=7)


# ---------------------------------------------------------------------------
# VerificationToken dataclass
# ---------------------------------------------------------------------------

@dataclass
class VerificationToken:
    token: str
    email: str
    tenant_id: str
    user_id: str
    purpose: VerificationPurpose
    created_at: datetime
    expires_at: datetime
    verified_at: datetime | None = None
    used: bool = False


# ---------------------------------------------------------------------------
# Invitation dataclass
# ---------------------------------------------------------------------------

@dataclass
class Invitation:
    id: str
    token: str
    tenant_id: str
    inviter_id: str
    email: str
    role: str
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime


# ---------------------------------------------------------------------------
# EmailVerificationManager
# ---------------------------------------------------------------------------

class EmailVerificationManager:
    """In-memory email verification token store."""

    def __init__(self) -> None:
        self._tokens: dict[str, VerificationToken] = {}  # token_str -> VerificationToken
        self._user_tokens: dict[str, list[str]] = {}  # user_id -> [token_str, ...]
        self._verified_users: set[str] = set()  # user_ids that completed verification

    def create_token(
        self,
        email: str,
        tenant_id: str,
        user_id: str,
        purpose: str | VerificationPurpose = VerificationPurpose.SIGNUP,
    ) -> VerificationToken:
        """Create a new verification token and store it."""
        if isinstance(purpose, str):
            purpose = VerificationPurpose(purpose)

        now = datetime.now(timezone.utc)
        ttl = _PURPOSE_TTL.get(purpose, timedelta(hours=24))

        vt = VerificationToken(
            token=uuid.uuid4().hex,
            email=email,
            tenant_id=tenant_id,
            user_id=user_id,
            purpose=purpose,
            created_at=now,
            expires_at=now + ttl,
        )

        self._tokens[vt.token] = vt
        self._user_tokens.setdefault(user_id, []).append(vt.token)
        return vt

    def verify_token(self, token_str: str) -> VerificationToken | None:
        """Verify a token: check existence, expiry, and used flag. Marks as used on success."""
        vt = self._tokens.get(token_str)
        if vt is None:
            return None

        if vt.used:
            return None

        now = datetime.now(timezone.utc)
        if now > vt.expires_at:
            return None

        vt.used = True
        vt.verified_at = now
        self._verified_users.add(vt.user_id)
        return vt

    def is_email_verified(self, user_id: str) -> bool:
        """Check if a user has completed email verification."""
        return user_id in self._verified_users

    def resend_verification(self, user_id: str) -> VerificationToken | None:
        """Invalidate existing tokens for this user and create a fresh one.

        Returns ``None`` if no previous token exists (we need email/tenant from prior token).
        """
        existing_tokens = self._user_tokens.get(user_id, [])
        if not existing_tokens:
            return None

        # Use the most recent token to get email/tenant
        last_token = self._tokens[existing_tokens[-1]]
        email = last_token.email
        tenant_id = last_token.tenant_id

        # Invalidate all existing tokens for this user
        for t_str in existing_tokens:
            t = self._tokens.get(t_str)
            if t is not None:
                t.used = True

        return self.create_token(email, tenant_id, user_id, VerificationPurpose.SIGNUP)

    def cleanup_expired(self) -> int:
        """Remove expired tokens from storage. Returns count of removed tokens."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            k for k, v in self._tokens.items()
            if now > v.expires_at
        ]
        for k in expired_keys:
            vt = self._tokens.pop(k)
            user_list = self._user_tokens.get(vt.user_id, [])
            if k in user_list:
                user_list.remove(k)
        return len(expired_keys)

    def get_pending_verifications(self, tenant_id: str) -> list[VerificationToken]:
        """Return all non-used, non-expired tokens for a given tenant."""
        now = datetime.now(timezone.utc)
        return [
            vt for vt in self._tokens.values()
            if vt.tenant_id == tenant_id
            and not vt.used
            and now <= vt.expires_at
        ]


# ---------------------------------------------------------------------------
# PasswordResetManager
# ---------------------------------------------------------------------------

class PasswordResetManager:
    """In-memory password reset flow built on top of EmailVerificationManager."""

    def __init__(self, verification_manager: EmailVerificationManager | None = None) -> None:
        self._vm = verification_manager or EmailVerificationManager()
        self._completed_resets: dict[str, str] = {}  # token -> new_password_hash

    def request_reset(self, email: str, tenant_id: str = "", user_id: str = "") -> VerificationToken:
        """Create a password-reset token for the given email."""
        return self._vm.create_token(
            email=email,
            tenant_id=tenant_id,
            user_id=user_id,
            purpose=VerificationPurpose.PASSWORD_RESET,
        )

    def validate_reset_token(self, token_str: str) -> str | None:
        """Validate a reset token without consuming it. Returns email or None."""
        vt = self._vm._tokens.get(token_str)
        if vt is None:
            return None
        if vt.used:
            return None
        now = datetime.now(timezone.utc)
        if now > vt.expires_at:
            return None
        if vt.purpose != VerificationPurpose.PASSWORD_RESET:
            return None
        return vt.email

    def complete_reset(self, token_str: str, new_password_hash: str) -> bool:
        """Consume the reset token and store the new password hash. Returns success."""
        vt = self._vm._tokens.get(token_str)
        if vt is None:
            return False
        if vt.used:
            return False
        now = datetime.now(timezone.utc)
        if now > vt.expires_at:
            return False
        if vt.purpose != VerificationPurpose.PASSWORD_RESET:
            return False

        vt.used = True
        vt.verified_at = now
        self._completed_resets[token_str] = new_password_hash
        return True


# ---------------------------------------------------------------------------
# InvitationManager
# ---------------------------------------------------------------------------

class InvitationManager:
    """In-memory invitation store for tenant team invitations."""

    def __init__(self) -> None:
        self._invitations: dict[str, Invitation] = {}  # invitation_id -> Invitation
        self._token_index: dict[str, str] = {}  # token -> invitation_id

    def create_invitation(
        self,
        tenant_id: str,
        inviter_id: str,
        email: str,
        role: str = "member",
    ) -> Invitation:
        """Create a new invitation. Raises ValueError if a pending invite for the same email exists."""
        # Check for existing pending invitation for same tenant+email
        for inv in self._invitations.values():
            if (
                inv.tenant_id == tenant_id
                and inv.email == email
                and inv.status == InvitationStatus.PENDING
            ):
                now = datetime.now(timezone.utc)
                if now <= inv.expires_at:
                    raise ValueError(f"Pending invitation already exists for {email}")

        now = datetime.now(timezone.utc)
        invitation = Invitation(
            id=str(uuid.uuid4()),
            token=uuid.uuid4().hex,
            tenant_id=tenant_id,
            inviter_id=inviter_id,
            email=email,
            role=role,
            status=InvitationStatus.PENDING,
            created_at=now,
            expires_at=now + _INVITATION_TTL,
        )
        self._invitations[invitation.id] = invitation
        self._token_index[invitation.token] = invitation.id
        return invitation

    def accept_invitation(self, token: str) -> Invitation | None:
        """Accept an invitation by token. Returns the invitation or None."""
        inv_id = self._token_index.get(token)
        if inv_id is None:
            return None

        inv = self._invitations.get(inv_id)
        if inv is None:
            return None

        if inv.status != InvitationStatus.PENDING:
            return None

        now = datetime.now(timezone.utc)
        if now > inv.expires_at:
            inv.status = InvitationStatus.EXPIRED
            return None

        inv.status = InvitationStatus.ACCEPTED
        return inv

    def list_pending(self, tenant_id: str) -> list[Invitation]:
        """List all pending (non-expired) invitations for a tenant."""
        now = datetime.now(timezone.utc)
        results: list[Invitation] = []
        for inv in self._invitations.values():
            if inv.tenant_id != tenant_id:
                continue
            if inv.status != InvitationStatus.PENDING:
                continue
            if now > inv.expires_at:
                inv.status = InvitationStatus.EXPIRED
                continue
            results.append(inv)
        return results

    def revoke_invitation(self, invitation_id: str) -> bool:
        """Revoke a pending invitation. Returns True if revoked, False otherwise."""
        inv = self._invitations.get(invitation_id)
        if inv is None:
            return False
        if inv.status != InvitationStatus.PENDING:
            return False
        inv.status = InvitationStatus.REVOKED
        return True

    def get_invitation(self, invitation_id: str) -> Invitation | None:
        return self._invitations.get(invitation_id)


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

email_verification_manager = EmailVerificationManager()
password_reset_manager = PasswordResetManager(email_verification_manager)
invitation_manager = InvitationManager()
