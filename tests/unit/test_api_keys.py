"""Tests for API key management — generation, validation, rotation, revocation."""

from datetime import datetime, timedelta, timezone

import pytest

from xcapitsff.core.api_keys import (
    KEY_PREFIX,
    MAX_KEYS_PER_PLAN,
    APIKeyManager,
    APIKeyMeta,
    _generate_raw_key,
    _hash_key,
    _mask_key,
    _matches_scope,
)


# ---------------------------------------------------------------------------
# Key generation helpers
# ---------------------------------------------------------------------------


class TestKeyGeneration:
    """Key format and helper functions."""

    def test_key_starts_with_prefix(self):
        key = _generate_raw_key()
        assert key.startswith(KEY_PREFIX)

    def test_key_length(self):
        key = _generate_raw_key()
        # "xsff_" (5) + 32 hex chars = 37
        assert len(key) == 37

    def test_key_hex_portion_is_hex(self):
        key = _generate_raw_key()
        hex_part = key[len(KEY_PREFIX):]
        int(hex_part, 16)  # should not raise

    def test_keys_are_unique(self):
        keys = {_generate_raw_key() for _ in range(100)}
        assert len(keys) == 100

    def test_hash_is_deterministic(self):
        key = "xsff_abc123"
        assert _hash_key(key) == _hash_key(key)

    def test_hash_differs_for_different_keys(self):
        assert _hash_key("xsff_aaa") != _hash_key("xsff_bbb")

    def test_mask_key(self):
        key = "xsff_abcdef1234567890abcdef1234567890"
        masked = _mask_key(key)
        assert masked.startswith("xsff_abcd")
        assert masked.endswith("7890")
        assert "..." in masked
        # raw key is not fully visible
        assert len(masked) < len(key)


# ---------------------------------------------------------------------------
# Scope matching
# ---------------------------------------------------------------------------


class TestScopeMatching:
    def test_exact_match(self):
        assert _matches_scope("/api/v1/leads", "/api/v1/leads") is True

    def test_exact_no_match(self):
        assert _matches_scope("/api/v1/leads", "/api/v1/tickets") is False

    def test_wildcard_suffix_matches_sub_path(self):
        assert _matches_scope("/api/v1/leads/123", "/api/v1/leads/*") is True

    def test_wildcard_suffix_matches_base(self):
        assert _matches_scope("/api/v1/leads", "/api/v1/leads/*") is True

    def test_wildcard_no_match_different_prefix(self):
        assert _matches_scope("/api/v1/tickets/1", "/api/v1/leads/*") is False

    def test_star_all_matches_anything(self):
        assert _matches_scope("/any/path", "*") is True


# ---------------------------------------------------------------------------
# APIKeyManager — create / list / revoke
# ---------------------------------------------------------------------------


class TestAPIKeyManager:
    """Core CRUD operations."""

    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_create_key_returns_raw_key(self):
        raw, meta = self.mgr.create_key("t1", "My Key")
        assert raw.startswith(KEY_PREFIX)
        assert len(raw) == 37

    def test_create_key_metadata(self):
        raw, meta = self.mgr.create_key("t1", "My Key", scopes=["/api/v1/leads/*"])
        assert meta.name == "My Key"
        assert meta.tenant_id == "t1"
        assert meta.scopes == ["/api/v1/leads/*"]
        assert meta.revoked is False
        assert meta.key_id is not None

    def test_create_key_default_scope_is_star(self):
        _, meta = self.mgr.create_key("t1", "All Access")
        assert meta.scopes == ["*"]

    def test_list_keys_returns_masked(self):
        self.mgr.create_key("t1", "Key A")
        self.mgr.create_key("t1", "Key B")
        keys = self.mgr.list_keys("t1")
        assert len(keys) == 2
        # No raw key in the list
        for k in keys:
            assert "key" not in k or k.get("key_hint", "").endswith("...")

    def test_list_keys_empty_for_other_tenant(self):
        self.mgr.create_key("t1", "Key A")
        assert self.mgr.list_keys("t2") == []

    def test_revoke_key(self):
        _, meta = self.mgr.create_key("t1", "Key A")
        revoked_meta = self.mgr.revoke_key(meta.key_id)
        assert revoked_meta.revoked is True

    def test_revoke_nonexistent_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.mgr.revoke_key("nonexistent-id")

    def test_revoked_key_fails_validation(self):
        raw, meta = self.mgr.create_key("t1", "Key A")
        self.mgr.revoke_key(meta.key_id)
        assert self.mgr.validate_key(raw) is None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_valid_key_returns_metadata(self):
        raw, meta = self.mgr.create_key("t1", "Test")
        result = self.mgr.validate_key(raw)
        assert result is not None
        assert result.key_id == meta.key_id

    def test_invalid_key_returns_none(self):
        assert self.mgr.validate_key("xsff_boguskey00000000000000000000") is None

    def test_validate_updates_last_used(self):
        raw, meta = self.mgr.create_key("t1", "Test")
        assert meta.last_used_at is None
        self.mgr.validate_key(raw)
        assert meta.last_used_at is not None

    def test_expired_key_returns_none(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        raw, meta = self.mgr.create_key("t1", "Expired", expires_at=past)
        assert self.mgr.validate_key(raw) is None

    def test_non_expired_key_works(self):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        raw, meta = self.mgr.create_key("t1", "Valid", expires_at=future)
        assert self.mgr.validate_key(raw) is not None


# ---------------------------------------------------------------------------
# Scope checking
# ---------------------------------------------------------------------------


class TestScopeChecking:
    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_check_scope_with_wildcard(self):
        raw, _ = self.mgr.create_key("t1", "Admin", scopes=["*"])
        assert self.mgr.check_scope(raw, "/anything") is True

    def test_check_scope_with_specific(self):
        raw, _ = self.mgr.create_key("t1", "Leads Only", scopes=["/api/v1/leads/*"])
        assert self.mgr.check_scope(raw, "/api/v1/leads/123") is True
        assert self.mgr.check_scope(raw, "/api/v1/tickets/1") is False

    def test_check_scope_invalid_key(self):
        assert self.mgr.check_scope("xsff_invalid00000000000000000000", "/api") is False


# ---------------------------------------------------------------------------
# Key rotation
# ---------------------------------------------------------------------------


class TestKeyRotation:
    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_rotate_returns_new_key(self):
        raw_old, meta_old = self.mgr.create_key("t1", "Rotatable")
        raw_new, meta_new = self.mgr.rotate_key(meta_old.key_id)
        assert raw_new != raw_old
        assert raw_new.startswith(KEY_PREFIX)

    def test_old_key_revoked_after_rotation(self):
        raw_old, meta_old = self.mgr.create_key("t1", "Rotatable")
        self.mgr.rotate_key(meta_old.key_id)
        assert self.mgr.validate_key(raw_old) is None

    def test_new_key_valid_after_rotation(self):
        _, meta_old = self.mgr.create_key("t1", "Rotatable")
        raw_new, _ = self.mgr.rotate_key(meta_old.key_id)
        assert self.mgr.validate_key(raw_new) is not None

    def test_rotated_key_preserves_scopes(self):
        _, meta_old = self.mgr.create_key(
            "t1", "Rotatable", scopes=["/api/v1/leads/*"]
        )
        _, meta_new = self.mgr.rotate_key(meta_old.key_id)
        assert meta_new.scopes == ["/api/v1/leads/*"]

    def test_rotate_nonexistent_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.mgr.rotate_key("nonexistent-id")

    def test_rotate_revoked_raises(self):
        _, meta = self.mgr.create_key("t1", "Test")
        self.mgr.revoke_key(meta.key_id)
        with pytest.raises(ValueError, match="already revoked"):
            self.mgr.rotate_key(meta.key_id)


# ---------------------------------------------------------------------------
# Max keys per plan
# ---------------------------------------------------------------------------


class TestMaxKeysPerPlan:
    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_free_plan_max_2(self):
        self.mgr.create_key("t1", "Key 1")
        self.mgr.create_key("t1", "Key 2")
        with pytest.raises(ValueError, match="Maximum keys"):
            self.mgr.create_key("t1", "Key 3")

    def test_pro_plan_max_10(self):
        self.mgr.set_tenant_plan("t1", "pro")
        for i in range(10):
            self.mgr.create_key("t1", f"Key {i+1}")
        with pytest.raises(ValueError, match="Maximum keys"):
            self.mgr.create_key("t1", "Key 11")

    def test_enterprise_unlimited(self):
        self.mgr.set_tenant_plan("t1", "enterprise")
        for i in range(50):
            self.mgr.create_key("t1", f"Key {i+1}")
        # No exception — enterprise is unlimited

    def test_revoked_keys_not_counted(self):
        """Revoking a key frees up a slot."""
        _, meta1 = self.mgr.create_key("t1", "Key 1")
        self.mgr.create_key("t1", "Key 2")
        # At limit
        with pytest.raises(ValueError):
            self.mgr.create_key("t1", "Key 3")
        self.mgr.revoke_key(meta1.key_id)
        # Now there's room
        self.mgr.create_key("t1", "Key 3")

    def test_max_keys_constants(self):
        assert MAX_KEYS_PER_PLAN["free"] == 2
        assert MAX_KEYS_PER_PLAN["pro"] == 10
        assert MAX_KEYS_PER_PLAN["enterprise"] == -1


# ---------------------------------------------------------------------------
# Key masking in list response
# ---------------------------------------------------------------------------


class TestKeyMaskingInList:
    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_list_contains_key_hint(self):
        raw, _ = self.mgr.create_key("t1", "Secret Key")
        keys = self.mgr.list_keys("t1")
        assert len(keys) == 1
        hint = keys[0]["key_hint"]
        assert hint.startswith("xsff_")
        assert hint.endswith("...")

    def test_list_does_not_leak_full_key(self):
        raw, _ = self.mgr.create_key("t1", "Secret Key")
        keys = self.mgr.list_keys("t1")
        hint = keys[0]["key_hint"]
        # The hint should be much shorter than the full key
        assert len(hint) < len(raw)

    def test_list_shows_revoked_status(self):
        _, meta = self.mgr.create_key("t1", "Revocable")
        self.mgr.revoke_key(meta.key_id)
        keys = self.mgr.list_keys("t1")
        assert keys[0]["revoked"] is True

    def test_list_shows_expiry(self):
        future = datetime.now(timezone.utc) + timedelta(days=30)
        self.mgr.create_key("t1", "Expiring", expires_at=future)
        keys = self.mgr.list_keys("t1")
        assert keys[0]["expires_at"] is not None


# ---------------------------------------------------------------------------
# get_key_by_id
# ---------------------------------------------------------------------------


class TestGetKeyById:
    def setup_method(self):
        self.mgr = APIKeyManager()

    def test_found(self):
        _, meta = self.mgr.create_key("t1", "Test")
        found = self.mgr.get_key_by_id(meta.key_id)
        assert found is not None
        assert found.key_id == meta.key_id

    def test_not_found(self):
        assert self.mgr.get_key_by_id("nope") is None
