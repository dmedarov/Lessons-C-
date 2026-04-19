from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Literal, Optional

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from config import settings

Role = Literal["employee", "fleet_admin"]

_PBKDF2_ITERATIONS = 200_000
_PBKDF2_ALGO = "sha256"


class AuthContext(BaseModel):
    user_id: int
    username: str
    display_name: str
    role: Role


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations_s, salt_b64, digest_b64 = stored.split("$")
        if not scheme.startswith("pbkdf2_"):
            return False
        algo = scheme.split("_", 1)[1]
        iterations = int(iterations_s)
        salt = _b64d(salt_b64)
        expected = _b64d(digest_b64)
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac(algo, password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


_MIN_SECRET_KEY_LEN = 32


def _assert_secret_key_strong() -> None:
    """Refuse to sign tokens with a weak secret outside dev."""
    if settings.app_env == "dev":
        return
    if len(settings.secret_key) < _MIN_SECRET_KEY_LEN:
        raise RuntimeError(
            f"SECRET_KEY must be at least {_MIN_SECRET_KEY_LEN} bytes long in non-dev environments"
        )


# Fail fast at import time in production if the secret is misconfigured.
_assert_secret_key_strong()


def issue_token(user_id: int, username: str, display_name: str, role: Role) -> str:
    issued_at = int(time.time())
    payload = {
        "sub": user_id,
        "u": username,
        "n": display_name,
        "r": role,
        "iat": issued_at,
        "exp": issued_at + settings.token_ttl_seconds,
        # Random per-token id — reserved for a future revoke list (Phase 3.1).
        "jti": _b64e(secrets.token_bytes(12)),
    }
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(settings.secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def verify_token(token: str) -> AuthContext:
    try:
        body, sig_b64 = token.split(".", 1)
        expected = hmac.new(settings.secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        given = _b64d(sig_b64)
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed token")

    # Timing-safe comparison: same work regardless of where the mismatch is.
    if not hmac.compare_digest(expected, given):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        payload = json.loads(_b64d(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Malformed token payload")

    now = int(time.time())
    # Reject tokens that claim to be issued in the future — small clock-skew
    # tolerance keeps legitimate drift from failing.
    iat = payload.get("iat")
    if isinstance(iat, (int, float)) and iat > now + 60:
        raise HTTPException(status_code=401, detail="Token issued in the future")

    if payload.get("exp", 0) < now:
        raise HTTPException(status_code=401, detail="Token expired")

    role = payload.get("r")
    if role not in {"employee", "fleet_admin"}:
        raise HTTPException(status_code=401, detail="Invalid role in token")

    return AuthContext(
        user_id=int(payload["sub"]),
        username=str(payload["u"]),
        display_name=str(payload["n"]),
        role=role,
    )


def get_auth_context(authorization: Optional[str] = Header(default=None)) -> AuthContext:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Authorization must be Bearer token")
    token_auth = verify_token(authorization[len(prefix):].strip())

    # Re-bind the signed token to the current database state so role changes
    # and user deactivation take effect immediately.
    from db import get_conn

    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, display_name, role, active FROM users WHERE id=?",
            (token_auth.user_id,),
        ).fetchone()

    if not row or not row["active"]:
        raise HTTPException(status_code=401, detail="User is inactive or no longer exists")

    return AuthContext(
        user_id=int(row["id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]),
        role=row["role"],
    )


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if auth.role != "fleet_admin":
        raise HTTPException(status_code=403, detail="fleet_admin role is required")
    return auth
