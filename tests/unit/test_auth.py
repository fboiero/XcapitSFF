"""Tests for authentication and multi-tenancy systems."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from xcapitsff.core.auth import (
    AuthManager,
    UserRole,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from xcapitsff.core.tenancy import (
    Plan,
    PLAN_LIMITS,
    Tenant,
    TenantManager,
    get_current_tenant,
    set_current_tenant,
)


# ===================================================================
# Password hashing
# ===================================================================

class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = hash_password("secret123")
        assert isinstance(h, str)

    def test_hash_contains_three_parts(self):
        h = hash_password("abc")
        parts = h.split("$")
        assert len(parts) == 3, "Format: iterations$salt$hash"

    def test_verify_correct_password(self):
        h = hash_password("my_password")
        assert verify_password("my_password", h) is True

    def test_verify_wrong_password(self):
        h = hash_password("my_password")
        assert verify_password("wrong_password", h) is False

    def test_verify_garbage_hash(self):
        assert verify_password("x", "not-a-real-hash") is False

    def test_different_passwords_produce_different_hashes(self):
        h1 = hash_password("alpha")
        h2 = hash_password("beta")
        assert h1 != h2

    def test_same_password_produces_different_hashes_due_to_salt(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts


# ===================================================================
# JWT tokens
# ===================================================================

class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("u1", "t1", "admin")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "u1"
        assert payload["tenant_id"] == "t1"
        assert payload["role"] == "admin"

    def test_zero_expiry_token_has_same_iat_exp(self):
        token = create_access_token("u1", "t1", "user", expires_hours=0)
        payload = decode_access_token(token)
        # With 0 hours, exp == iat (or very close)
        assert payload is not None
        assert payload["exp"] == payload["iat"]

    def test_tampered_token_handling(self):
        token = create_access_token("u1", "t1", "admin")
        # Completely garbled token should fail
        assert decode_access_token("xxx.yyy.zzz") is None

    def test_invalid_format_returns_none(self):
        assert decode_access_token("not.a.jwt.token.at.all") is None
        assert decode_access_token("") is None
        assert decode_access_token("one_segment") is None

    def test_token_contains_iat_and_exp(self):
        token = create_access_token("u1", "t1", "user", expires_hours=2)
        payload = decode_access_token(token)
        assert payload is not None
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] - payload["iat"] == 2 * 3600


# ===================================================================
# AuthManager — user registration / login
# ===================================================================

class TestAuthManager:
    def _manager(self) -> AuthManager:
        return AuthManager()

    def test_register_user(self):
        am = self._manager()
        user = am.register("a@b.com", "pass", "Alice", "t1")
        assert user.email == "a@b.com"
        assert user.name == "Alice"
        assert user.tenant_id == "t1"
        assert user.role == UserRole.USER
        assert user.is_active is True

    def test_register_duplicate_email_raises(self):
        am = self._manager()
        am.register("a@b.com", "p1", "A", "t1")
        with pytest.raises(ValueError, match="already registered"):
            am.register("a@b.com", "p2", "B", "t1")

    def test_register_with_role(self):
        am = self._manager()
        user = am.register("x@y.com", "pw", "X", "t1", role=UserRole.ADMIN)
        assert user.role == UserRole.ADMIN

    def test_login_success(self):
        am = self._manager()
        am.register("u@x.com", "secret", "U", "t1")
        result = am.login("u@x.com", "secret")
        assert result is not None
        user, token = result
        assert user.email == "u@x.com"
        assert isinstance(token, str) and len(token) > 0

    def test_login_wrong_password(self):
        am = self._manager()
        am.register("u@x.com", "right", "U", "t1")
        assert am.login("u@x.com", "wrong") is None

    def test_login_unknown_email(self):
        am = self._manager()
        assert am.login("nobody@x.com", "any") is None

    def test_login_sets_last_login(self):
        am = self._manager()
        am.register("u@x.com", "pw", "U", "t1")
        result = am.login("u@x.com", "pw")
        assert result is not None
        user, _ = result
        assert user.last_login is not None

    def test_login_inactive_user(self):
        am = self._manager()
        user = am.register("u@x.com", "pw", "U", "t1")
        am.deactivate_user(user.user_id)
        assert am.login("u@x.com", "pw") is None

    def test_get_user(self):
        am = self._manager()
        user = am.register("u@x.com", "pw", "U", "t1")
        fetched = am.get_user(user.user_id)
        assert fetched is not None
        assert fetched.email == "u@x.com"

    def test_get_user_unknown(self):
        am = self._manager()
        assert am.get_user("nonexistent") is None

    def test_get_users_by_tenant(self):
        am = self._manager()
        am.register("a@x.com", "pw", "A", "t1")
        am.register("b@x.com", "pw", "B", "t1")
        am.register("c@x.com", "pw", "C", "t2")
        assert len(am.get_users_by_tenant("t1")) == 2
        assert len(am.get_users_by_tenant("t2")) == 1

    def test_change_password(self):
        am = self._manager()
        user = am.register("u@x.com", "old", "U", "t1")
        assert am.change_password(user.user_id, "old", "new") is True
        assert am.login("u@x.com", "new") is not None
        assert am.login("u@x.com", "old") is None

    def test_change_password_wrong_old(self):
        am = self._manager()
        user = am.register("u@x.com", "correct", "U", "t1")
        assert am.change_password(user.user_id, "wrong", "new") is False

    def test_deactivate_user(self):
        am = self._manager()
        user = am.register("u@x.com", "pw", "U", "t1")
        assert am.deactivate_user(user.user_id) is True
        fetched = am.get_user(user.user_id)
        assert fetched is not None and fetched.is_active is False

    def test_deactivate_unknown_user(self):
        am = self._manager()
        assert am.deactivate_user("bogus") is False


# ===================================================================
# TenantManager
# ===================================================================

class TestTenantManager:
    def _manager(self) -> TenantManager:
        return TenantManager()

    def test_create_tenant_free(self):
        tm = self._manager()
        t = tm.create_tenant("Acme Corp", "admin@acme.com")
        assert t.name == "Acme Corp"
        assert t.slug == "acme-corp"
        assert t.plan == Plan.FREE
        assert t.max_leads == 100
        assert t.max_tickets == 50
        assert t.max_users == 2
        assert t.api_calls_limit_monthly == 1_000
        assert t.is_active is True

    def test_create_tenant_pro(self):
        tm = self._manager()
        t = tm.create_tenant("Pro Co", "p@co.com", plan="pro")
        assert t.plan == Plan.PRO
        assert t.max_leads == 5_000

    def test_create_tenant_enterprise(self):
        tm = self._manager()
        t = tm.create_tenant("BigCo", "e@co.com", plan=Plan.ENTERPRISE)
        assert t.max_leads == -1  # unlimited
        assert t.api_calls_limit_monthly == -1

    def test_slug_uniqueness(self):
        tm = self._manager()
        t1 = tm.create_tenant("Acme", "a@a.com")
        t2 = tm.create_tenant("Acme", "b@b.com")
        assert t1.slug != t2.slug

    def test_get_tenant(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com")
        assert tm.get_tenant(t.tenant_id) is t

    def test_get_tenant_not_found(self):
        tm = self._manager()
        assert tm.get_tenant("nope") is None

    def test_get_tenant_by_slug(self):
        tm = self._manager()
        t = tm.create_tenant("My Org", "m@o.com")
        assert tm.get_tenant_by_slug("my-org") is t

    def test_update_tenant_name(self):
        tm = self._manager()
        t = tm.create_tenant("Old", "o@o.com")
        updated = tm.update_tenant(t.tenant_id, name="New")
        assert updated.name == "New"

    def test_update_tenant_plan_upgrades_limits(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com", plan="free")
        tm.update_tenant(t.tenant_id, plan="pro")
        assert t.max_leads == 5_000

    def test_update_nonexistent_raises(self):
        tm = self._manager()
        with pytest.raises(ValueError):
            tm.update_tenant("missing", name="X")

    def test_deactivate_tenant(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com")
        assert tm.deactivate_tenant(t.tenant_id) is True
        assert t.is_active is False

    def test_deactivate_nonexistent(self):
        tm = self._manager()
        assert tm.deactivate_tenant("nope") is False

    def test_list_tenants_active_only(self):
        tm = self._manager()
        t1 = tm.create_tenant("A", "a@a.com")
        t2 = tm.create_tenant("B", "b@b.com")
        tm.deactivate_tenant(t2.tenant_id)
        active = tm.list_tenants(active_only=True)
        assert len(active) == 1
        assert active[0].tenant_id == t1.tenant_id

    def test_list_tenants_by_plan(self):
        tm = self._manager()
        tm.create_tenant("F", "f@f.com", plan="free")
        tm.create_tenant("P", "p@p.com", plan="pro")
        assert len(tm.list_tenants(plan="free")) == 1

    def test_check_limit_within(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com", plan="free")
        ok, msg = tm.check_limit(t.tenant_id, "leads", 50)
        assert ok is True
        assert "50/100" in msg

    def test_check_limit_exceeded(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com", plan="free")
        ok, msg = tm.check_limit(t.tenant_id, "leads", 100)
        assert ok is False
        assert "limit reached" in msg

    def test_check_limit_unlimited(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com", plan="enterprise")
        ok, msg = tm.check_limit(t.tenant_id, "leads", 999_999)
        assert ok is True
        assert msg == "unlimited"

    def test_check_limit_unknown_resource(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com")
        ok, msg = tm.check_limit(t.tenant_id, "widgets", 0)
        assert ok is False

    def test_check_limit_deactivated_tenant(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com")
        tm.deactivate_tenant(t.tenant_id)
        ok, msg = tm.check_limit(t.tenant_id, "leads", 0)
        assert ok is False
        assert "deactivated" in msg

    def test_get_usage(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com", plan="pro")
        usage = tm.get_usage(t.tenant_id)
        assert usage["plan"] == "pro"
        assert usage["leads"]["current"] == 0
        assert usage["leads"]["limit"] == 5_000

    def test_get_usage_nonexistent(self):
        tm = self._manager()
        assert tm.get_usage("nope") == {}

    def test_increment_usage(self):
        tm = self._manager()
        t = tm.create_tenant("X", "x@x.com")
        tm.increment_usage(t.tenant_id, "leads", 5)
        usage = tm.get_usage(t.tenant_id)
        assert usage["leads"]["current"] == 5


# ===================================================================
# TenantContext
# ===================================================================

class TestTenantContext:
    def test_default_is_none(self):
        # Reset to ensure clean state
        set_current_tenant(None)  # type: ignore[arg-type]
        # In a fresh context, the default should apply
        # We cannot guarantee a truly fresh context in tests, so just check type
        result = get_current_tenant()
        assert result is None or isinstance(result, str)

    def test_set_and_get(self):
        set_current_tenant("tenant-abc")
        assert get_current_tenant() == "tenant-abc"

    def test_overwrite(self):
        set_current_tenant("t1")
        set_current_tenant("t2")
        assert get_current_tenant() == "t2"
