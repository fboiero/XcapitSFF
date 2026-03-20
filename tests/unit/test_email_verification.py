"""Tests for email verification, password reset, and invitation systems."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from xcapitsff.core.email_verification import (
    EmailVerificationManager,
    Invitation,
    InvitationManager,
    InvitationStatus,
    PasswordResetManager,
    VerificationPurpose,
    VerificationToken,
)


# ===================================================================
# EmailVerificationManager — token creation and verification
# ===================================================================

class TestEmailVerificationManager:
    def _manager(self) -> EmailVerificationManager:
        return EmailVerificationManager()

    def test_create_verification_token(self):
        vm = self._manager()
        vt = vm.create_token("alice@example.com", "t1", "u1", VerificationPurpose.SIGNUP)
        assert isinstance(vt, VerificationToken)
        assert vt.email == "alice@example.com"
        assert vt.tenant_id == "t1"
        assert vt.user_id == "u1"
        assert vt.purpose == VerificationPurpose.SIGNUP
        assert vt.used is False
        assert vt.verified_at is None
        assert len(vt.token) == 32  # uuid4 hex

    def test_create_token_with_string_purpose(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1", "signup")
        assert vt.purpose == VerificationPurpose.SIGNUP

    def test_signup_token_expires_in_24h(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1", VerificationPurpose.SIGNUP)
        delta = vt.expires_at - vt.created_at
        assert abs(delta.total_seconds() - 24 * 3600) < 1

    def test_password_reset_token_expires_in_1h(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1", VerificationPurpose.PASSWORD_RESET)
        delta = vt.expires_at - vt.created_at
        assert abs(delta.total_seconds() - 3600) < 1

    def test_verify_valid_token(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1")
        result = vm.verify_token(vt.token)
        assert result is not None
        assert result.email == "a@b.com"
        assert result.used is True
        assert result.verified_at is not None

    def test_verify_nonexistent_token_returns_none(self):
        vm = self._manager()
        assert vm.verify_token("nonexistent_token") is None

    def test_reject_expired_token(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1")
        # Manually expire the token
        vt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert vm.verify_token(vt.token) is None

    def test_reject_already_used_token(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1")
        # First use succeeds
        assert vm.verify_token(vt.token) is not None
        # Second use fails
        assert vm.verify_token(vt.token) is None

    def test_is_email_verified_after_verification(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1")
        assert vm.is_email_verified("u1") is False
        vm.verify_token(vt.token)
        assert vm.is_email_verified("u1") is True

    def test_is_email_verified_unknown_user(self):
        vm = self._manager()
        assert vm.is_email_verified("unknown") is False

    def test_resend_creates_new_token(self):
        vm = self._manager()
        vt1 = vm.create_token("a@b.com", "t1", "u1")
        vt2 = vm.resend_verification("u1")
        assert vt2 is not None
        assert vt2.token != vt1.token
        assert vt2.email == "a@b.com"
        assert vt2.tenant_id == "t1"

    def test_resend_invalidates_old_tokens(self):
        vm = self._manager()
        vt1 = vm.create_token("a@b.com", "t1", "u1")
        vm.resend_verification("u1")
        # Old token should be marked as used
        assert vm.verify_token(vt1.token) is None

    def test_resend_returns_none_for_unknown_user(self):
        vm = self._manager()
        assert vm.resend_verification("unknown") is None

    def test_cleanup_expired(self):
        vm = self._manager()
        vt1 = vm.create_token("a@b.com", "t1", "u1")
        vt2 = vm.create_token("b@b.com", "t1", "u2")
        # Expire one token
        vt1.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        removed = vm.cleanup_expired()
        assert removed == 1
        # Only vt2 should remain
        assert vt1.token not in vm._tokens
        assert vt2.token in vm._tokens

    def test_get_pending_verifications(self):
        vm = self._manager()
        vm.create_token("a@b.com", "t1", "u1")
        vm.create_token("b@b.com", "t1", "u2")
        vm.create_token("c@b.com", "t2", "u3")
        pending = vm.get_pending_verifications("t1")
        assert len(pending) == 2

    def test_get_pending_excludes_used(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1")
        vm.verify_token(vt.token)
        pending = vm.get_pending_verifications("t1")
        assert len(pending) == 0

    def test_get_pending_excludes_expired(self):
        vm = self._manager()
        vt = vm.create_token("a@b.com", "t1", "u1")
        vt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        pending = vm.get_pending_verifications("t1")
        assert len(pending) == 0


# ===================================================================
# PasswordResetManager
# ===================================================================

class TestPasswordResetManager:
    def _manager(self) -> PasswordResetManager:
        return PasswordResetManager()

    def test_request_reset_creates_token(self):
        pm = self._manager()
        vt = pm.request_reset("user@example.com", tenant_id="t1", user_id="u1")
        assert vt.email == "user@example.com"
        assert vt.purpose == VerificationPurpose.PASSWORD_RESET

    def test_validate_reset_token_returns_email(self):
        pm = self._manager()
        vt = pm.request_reset("user@example.com", tenant_id="t1", user_id="u1")
        email = pm.validate_reset_token(vt.token)
        assert email == "user@example.com"

    def test_validate_nonexistent_token(self):
        pm = self._manager()
        assert pm.validate_reset_token("bogus") is None

    def test_complete_reset_success(self):
        pm = self._manager()
        vt = pm.request_reset("user@example.com", tenant_id="t1", user_id="u1")
        assert pm.complete_reset(vt.token, "new_hash_abc") is True
        assert vt.token in pm._completed_resets

    def test_complete_reset_marks_used(self):
        pm = self._manager()
        vt = pm.request_reset("user@example.com", tenant_id="t1", user_id="u1")
        pm.complete_reset(vt.token, "hash")
        # Second attempt fails because token is used
        assert pm.complete_reset(vt.token, "hash2") is False

    def test_validate_expired_reset_token(self):
        pm = self._manager()
        vt = pm.request_reset("user@example.com")
        vt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert pm.validate_reset_token(vt.token) is None

    def test_complete_reset_expired_token(self):
        pm = self._manager()
        vt = pm.request_reset("user@example.com")
        vt.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert pm.complete_reset(vt.token, "hash") is False

    def test_validate_rejects_non_reset_token(self):
        pm = self._manager()
        # Manually create a signup token in the underlying verification manager
        vm = pm._vm
        vt = vm.create_token("a@b.com", "t1", "u1", VerificationPurpose.SIGNUP)
        assert pm.validate_reset_token(vt.token) is None


# ===================================================================
# InvitationManager
# ===================================================================

class TestInvitationManager:
    def _manager(self) -> InvitationManager:
        return InvitationManager()

    def test_create_invitation(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "new@example.com")
        assert isinstance(inv, Invitation)
        assert inv.tenant_id == "t1"
        assert inv.inviter_id == "admin1"
        assert inv.email == "new@example.com"
        assert inv.role == "member"
        assert inv.status == InvitationStatus.PENDING
        assert len(inv.token) == 32

    def test_create_invitation_custom_role(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "mgr@example.com", role="manager")
        assert inv.role == "manager"

    def test_invitation_expires_in_7_days(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        delta = inv.expires_at - inv.created_at
        assert abs(delta.total_seconds() - 7 * 24 * 3600) < 1

    def test_accept_invitation(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        result = im.accept_invitation(inv.token)
        assert result is not None
        assert result.status == InvitationStatus.ACCEPTED
        assert result.id == inv.id

    def test_accept_nonexistent_token(self):
        im = self._manager()
        assert im.accept_invitation("bogus_token") is None

    def test_accept_already_accepted(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        im.accept_invitation(inv.token)
        # Second accept should fail
        assert im.accept_invitation(inv.token) is None

    def test_revoke_invitation(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        assert im.revoke_invitation(inv.id) is True
        assert inv.status == InvitationStatus.REVOKED

    def test_revoke_nonexistent(self):
        im = self._manager()
        assert im.revoke_invitation("nonexistent-id") is False

    def test_revoke_non_pending(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        im.accept_invitation(inv.token)
        assert im.revoke_invitation(inv.id) is False

    def test_accept_expired_invitation(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        inv.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        result = im.accept_invitation(inv.token)
        assert result is None
        assert inv.status == InvitationStatus.EXPIRED

    def test_list_pending(self):
        im = self._manager()
        im.create_invitation("t1", "admin1", "a@b.com")
        im.create_invitation("t1", "admin1", "b@b.com")
        im.create_invitation("t2", "admin2", "c@b.com")
        pending = im.list_pending("t1")
        assert len(pending) == 2

    def test_list_pending_excludes_accepted(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        im.accept_invitation(inv.token)
        pending = im.list_pending("t1")
        assert len(pending) == 0

    def test_list_pending_excludes_expired(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        inv.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        pending = im.list_pending("t1")
        assert len(pending) == 0
        # Status should have been updated to expired
        assert inv.status == InvitationStatus.EXPIRED

    def test_duplicate_invitation_same_email_raises(self):
        im = self._manager()
        im.create_invitation("t1", "admin1", "a@b.com")
        with pytest.raises(ValueError, match="Pending invitation already exists"):
            im.create_invitation("t1", "admin1", "a@b.com")

    def test_duplicate_allowed_after_revoke(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        im.revoke_invitation(inv.id)
        # Should succeed now
        inv2 = im.create_invitation("t1", "admin1", "a@b.com")
        assert inv2.email == "a@b.com"

    def test_duplicate_allowed_different_tenant(self):
        im = self._manager()
        im.create_invitation("t1", "admin1", "a@b.com")
        inv2 = im.create_invitation("t2", "admin2", "a@b.com")
        assert inv2.tenant_id == "t2"

    def test_get_invitation(self):
        im = self._manager()
        inv = im.create_invitation("t1", "admin1", "a@b.com")
        fetched = im.get_invitation(inv.id)
        assert fetched is inv

    def test_get_invitation_not_found(self):
        im = self._manager()
        assert im.get_invitation("nope") is None
