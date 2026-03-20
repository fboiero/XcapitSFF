"""API key management — generation, validation, rotation, and revocation.

Keys use the format ``xsff_<32 hex chars>`` and are stored hashed (SHA-256).
All storage is in-memory (dict-based) with no external dependencies.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEY_PREFIX = "xsff_"
KEY_HEX_LENGTH = 32  # 32 hex chars = 16 bytes of entropy

MAX_KEYS_PER_PLAN: dict[str, int] = {
    "free": 2,
    "pro": 10,
    "enterprise": -1,  # unlimited
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class APIKeyMeta:
    """Metadata stored alongside the hashed key."""

    key_id: str
    name: str
    tenant_id: str
    scopes: list[str]  # e.g. ["/api/v1/leads/*", "/api/v1/tickets/*"]
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked: bool = False
    key_prefix_hint: str = ""  # first 8 chars for identification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_raw_key() -> str:
    """Generate a raw API key string: ``xsff_<32 hex chars>``."""
    return KEY_PREFIX + secrets.token_hex(KEY_HEX_LENGTH // 2)


def _hash_key(raw_key: str) -> str:
    """SHA-256 hash of the raw key for safe storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _mask_key(raw_key: str) -> str:
    """Return a masked representation: ``xsff_ab12...ef34``."""
    if len(raw_key) <= 12:
        return raw_key[:4] + "..." + raw_key[-4:]
    return raw_key[:9] + "..." + raw_key[-4:]


def _matches_scope(endpoint: str, scope: str) -> bool:
    """Check if *endpoint* matches a *scope* pattern.

    Supports:
    - Exact match: ``/api/v1/leads``
    - Wildcard suffix: ``/api/v1/leads/*`` matches ``/api/v1/leads/123``
    - Star-all: ``*`` matches everything
    """
    if scope == "*":
        return True
    if scope.endswith("/*"):
        prefix = scope[:-1]  # keep the trailing /
        return endpoint == scope[:-2] or endpoint.startswith(prefix)
    return endpoint == scope


# ---------------------------------------------------------------------------
# API Key Manager
# ---------------------------------------------------------------------------


class APIKeyManager:
    """In-memory API key store.

    Keys are indexed by their SHA-256 hash.  The raw key is returned
    **only once** at creation time.
    """

    def __init__(self) -> None:
        self._keys_by_hash: dict[str, APIKeyMeta] = {}
        self._keys_by_id: dict[str, tuple[str, APIKeyMeta]] = {}  # key_id → (hash, meta)
        self._tenant_plans: dict[str, str] = {}  # tenant_id → plan name
        self._lock = threading.Lock()

    # -- plan management ---------------------------------------------------

    def set_tenant_plan(self, tenant_id: str, plan: str) -> None:
        with self._lock:
            self._tenant_plans[tenant_id] = plan

    def get_tenant_plan(self, tenant_id: str) -> str:
        return self._tenant_plans.get(tenant_id, "free")

    # -- create / list / revoke / rotate -----------------------------------

    def create_key(
        self,
        tenant_id: str,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[str, APIKeyMeta]:
        """Create a new API key.

        Returns
        -------
        tuple[str, APIKeyMeta]
            The raw key (shown once) and its metadata.

        Raises
        ------
        ValueError
            If the tenant has reached the maximum number of keys for their plan.
        """
        with self._lock:
            plan = self._tenant_plans.get(tenant_id, "free")
            max_keys = MAX_KEYS_PER_PLAN.get(plan, 2)

            if max_keys != -1:
                existing_count = sum(
                    1
                    for _, meta in self._keys_by_hash.items()
                    if meta.tenant_id == tenant_id and not meta.revoked
                )
                if existing_count >= max_keys:
                    raise ValueError(
                        f"Maximum keys ({max_keys}) reached for plan '{plan}'"
                    )

            raw_key = _generate_raw_key()
            hashed = _hash_key(raw_key)
            key_id = str(uuid.uuid4())

            meta = APIKeyMeta(
                key_id=key_id,
                name=name,
                tenant_id=tenant_id,
                scopes=scopes or ["*"],
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                key_prefix_hint=raw_key[:9],
            )

            self._keys_by_hash[hashed] = meta
            self._keys_by_id[key_id] = (hashed, meta)

            return raw_key, meta

    def list_keys(self, tenant_id: str) -> list[dict[str, Any]]:
        """List all keys for a tenant (masked, no raw keys)."""
        with self._lock:
            results = []
            for meta in self._keys_by_hash.values():
                if meta.tenant_id == tenant_id:
                    results.append(
                        {
                            "key_id": meta.key_id,
                            "name": meta.name,
                            "key_hint": meta.key_prefix_hint + "...",
                            "scopes": meta.scopes,
                            "created_at": meta.created_at.isoformat(),
                            "last_used_at": (
                                meta.last_used_at.isoformat()
                                if meta.last_used_at
                                else None
                            ),
                            "expires_at": (
                                meta.expires_at.isoformat()
                                if meta.expires_at
                                else None
                            ),
                            "revoked": meta.revoked,
                        }
                    )
            return results

    def revoke_key(self, key_id: str) -> APIKeyMeta:
        """Revoke a key by its ID.

        Raises
        ------
        ValueError
            If the key_id is not found.
        """
        with self._lock:
            if key_id not in self._keys_by_id:
                raise ValueError(f"Key '{key_id}' not found")
            _hash, meta = self._keys_by_id[key_id]
            meta.revoked = True
            return meta

    def rotate_key(self, key_id: str) -> tuple[str, APIKeyMeta]:
        """Rotate a key: revoke the old one and create a new one with the same metadata.

        Returns
        -------
        tuple[str, APIKeyMeta]
            The new raw key and its metadata.

        Raises
        ------
        ValueError
            If the key_id is not found or is already revoked.
        """
        with self._lock:
            if key_id not in self._keys_by_id:
                raise ValueError(f"Key '{key_id}' not found")
            old_hash, old_meta = self._keys_by_id[key_id]
            if old_meta.revoked:
                raise ValueError(f"Key '{key_id}' is already revoked")

            # Revoke old key
            old_meta.revoked = True

        # Create new key with same attributes (outside lock — create_key acquires it)
        new_raw, new_meta = self.create_key(
            tenant_id=old_meta.tenant_id,
            name=old_meta.name,
            scopes=list(old_meta.scopes),
            expires_at=old_meta.expires_at,
        )
        return new_raw, new_meta

    # -- validation --------------------------------------------------------

    def validate_key(self, raw_key: str) -> APIKeyMeta | None:
        """Validate a raw API key and return its metadata, or ``None``.

        Also updates ``last_used_at``.
        Returns ``None`` for invalid, revoked, or expired keys.
        """
        hashed = _hash_key(raw_key)
        with self._lock:
            meta = self._keys_by_hash.get(hashed)
            if meta is None:
                return None
            if meta.revoked:
                return None
            if meta.expires_at and datetime.now(timezone.utc) > meta.expires_at:
                return None
            meta.last_used_at = datetime.now(timezone.utc)
            return meta

    def check_scope(self, raw_key: str, endpoint: str) -> bool:
        """Check if a key has access to the given endpoint.

        Returns ``False`` for invalid/revoked/expired keys or if no scope matches.
        """
        meta = self.validate_key(raw_key)
        if meta is None:
            return False
        return any(_matches_scope(endpoint, scope) for scope in meta.scopes)

    def get_key_by_id(self, key_id: str) -> APIKeyMeta | None:
        """Look up key metadata by its ID."""
        with self._lock:
            if key_id in self._keys_by_id:
                return self._keys_by_id[key_id][1]
            return None


# ---------------------------------------------------------------------------
# Shared default manager instance
# ---------------------------------------------------------------------------

_default_manager: APIKeyManager | None = None
_default_lock = threading.Lock()


def get_default_manager() -> APIKeyManager:
    """Return (and lazily create) the global default API key manager."""
    global _default_manager
    if _default_manager is None:
        with _default_lock:
            if _default_manager is None:
                _default_manager = APIKeyManager()
    return _default_manager


def set_default_manager(manager: APIKeyManager) -> None:
    """Replace the global default manager (useful for testing)."""
    global _default_manager
    _default_manager = manager
