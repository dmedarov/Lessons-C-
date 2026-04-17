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


def issue_token(user_id: int, username: str, display_name: str, role: Role) -> str:
    payload = {
        "sub": user_id,
        "u": username,
        "n": display_name,
        "r": role,
        "exp": int(time.time()) + settings.token_ttl_seconds,
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

    if not hmac.compare_digest(expected, given):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    try:
        payload = json.loads(_b64d(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Malformed token payload")

    if payload.get("exp", 0) < int(time.time()):
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
    return verify_token(authorization[len(prefix):].strip())


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    if auth.role != "fleet_admin":
        raise HTTPException(status_code=403, detail="fleet_admin role is required")
    return auth
