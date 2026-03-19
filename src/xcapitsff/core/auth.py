"""Authentication system — users, passwords, JWT tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from xcapitsff.config import settings


# ---------------------------------------------------------------------------
# UserRole enum
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"


# ---------------------------------------------------------------------------
# User dataclass
# ---------------------------------------------------------------------------

@dataclass
class User:
    user_id: str
    email: str
    name: str
    hashed_password: str
    tenant_id: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-SHA256)
# ---------------------------------------------------------------------------

_PBKDF2_ITERATIONS = 260_000
_SALT_LENGTH = 32


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 and return a storable string."""
    salt = os.urandom(_SALT_LENGTH)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    # Format: iterations$salt_hex$hash_hex
    return f"{_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify *password* against a previously hashed value."""
    try:
        iterations_str, salt_hex, hash_hex = hashed.split("$")
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, AttributeError):
        return False

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(dk, expected)


# ---------------------------------------------------------------------------
# JWT helpers (manual HMAC-SHA256 — no external dependency)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_access_token(
    user_id: str,
    tenant_id: str,
    role: str,
    expires_hours: int = 24,
) -> str:
    """Create a JWT (HMAC-SHA256) with the given claims."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + expires_hours * 3600,
    }

    segments: list[str] = []
    for part in (header, payload):
        segments.append(_b64url_encode(json.dumps(part, separators=(",", ":")).encode("utf-8")))

    signing_input = f"{segments[0]}.{segments[1]}"
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    segments.append(_b64url_encode(signature))

    return ".".join(segments)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT. Returns the payload dict or ``None``."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        signing_input = f"{parts[0]}.{parts[1]}"
        expected_sig = hmac.new(
            settings.secret_key.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(_b64url_decode(parts[1]))

        # Check expiry
        if payload.get("exp", 0) < int(time.time()):
            return None

        return payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# AuthManager
# ---------------------------------------------------------------------------

class AuthManager:
    """In-memory user store (swap with DB-backed implementation later)."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}  # user_id -> User
        self._email_index: dict[str, str] = {}  # email -> user_id

    def register(
        self,
        email: str,
        password: str,
        name: str,
        tenant_id: str,
        role: str | UserRole = UserRole.USER,
    ) -> User:
        if email in self._email_index:
            raise ValueError(f"Email already registered: {email}")

        if isinstance(role, str):
            role = UserRole(role)

        user_id = str(uuid.uuid4())
        user = User(
            user_id=user_id,
            email=email,
            name=name,
            hashed_password=hash_password(password),
            tenant_id=tenant_id,
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self._users[user_id] = user
        self._email_index[email] = user_id
        return user

    def login(self, email: str, password: str) -> tuple[User, str] | None:
        user_id = self._email_index.get(email)
        if user_id is None:
            return None

        user = self._users[user_id]
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None

        user.last_login = datetime.now(timezone.utc)
        token = create_access_token(
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            role=user.role.value,
        )
        return user, token

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_users_by_tenant(self, tenant_id: str) -> list[User]:
        return [u for u in self._users.values() if u.tenant_id == tenant_id]

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        if not verify_password(old_password, user.hashed_password):
            return False
        user.hashed_password = hash_password(new_password)
        return True

    def deactivate_user(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user is None:
            return False
        user.is_active = False
        return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

auth_manager = AuthManager()
