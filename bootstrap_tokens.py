"""One-shot bootstrap-admin token.

In production (`APP_ENV != "dev"`) the `/auth/bootstrap-admin` endpoint is
dangerous: whoever hits it first becomes the first fleet admin. To close that
window we generate a random, hashed, TTL-bounded token at startup when no
admin yet exists, log it to stdout exactly once, and require it as a header.

In dev the endpoint stays permissive so the local smoke flow is unchanged.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Optional

from config import settings

_LOG = logging.getLogger("fleetflow.bootstrap")

# 30-minute window — enough for an ops human to run the deploy, tail the logs,
# and POST once. Configurable via env if ops needs longer.
_DEFAULT_TTL_SECONDS = 30 * 60


@dataclass
class _TokenRecord:
    digest: bytes  # sha256(token) — we never keep the plaintext
    expires_at: float
    consumed: bool = False


_lock = threading.Lock()
_record: Optional[_TokenRecord] = None


def _hash(raw: str) -> bytes:
    return hashlib.sha256(raw.encode("utf-8")).digest()


def is_enforced() -> bool:
    """Whether the endpoint requires a valid token to succeed."""
    return settings.app_env != "dev"


def provision(ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> str:
    """Generate a fresh token, replacing any prior one. Returns the plaintext.

    The plaintext is only handed back here (for the startup log) — it is
    immediately discarded from in-memory state.
    """
    token = secrets.token_urlsafe(32)
    with _lock:
        global _record
        _record = _TokenRecord(
            digest=_hash(token),
            expires_at=time.time() + ttl_seconds,
        )
    return token


def clear() -> None:
    """Forget any provisioned token — used after the admin is created."""
    with _lock:
        global _record
        _record = None


def verify_and_consume(raw: Optional[str]) -> None:
    """Raise if `raw` doesn't match a live unused token. Marks it consumed on
    success. Safe to call under the `is_enforced()` branch only."""
    if not raw:
        raise _denied("Missing X-Bootstrap-Token header")
    with _lock:
        global _record
        if _record is None:
            raise _denied("No bootstrap token provisioned — restart the service to generate one")
        if _record.consumed:
            raise _denied("Bootstrap token already used")
        if time.time() > _record.expires_at:
            _record = None
            raise _denied("Bootstrap token expired — restart to regenerate")
        if not hmac.compare_digest(_record.digest, _hash(raw)):
            raise _denied("Invalid bootstrap token")
        _record.consumed = True


def _denied(detail: str):
    # Local import keeps this module free of FastAPI at import time, making it
    # trivially unit-testable.
    from fastapi import HTTPException

    return HTTPException(status_code=403, detail=detail)


def announce_if_needed(admin_exists: bool) -> None:
    """Called from the app lifespan. Provisions + logs a token the first time
    a prod instance starts without any admin. No-op in dev, and no-op once an
    admin exists."""
    if not is_enforced():
        return
    if admin_exists:
        return
    token = provision()
    # One line, unmissable. Ops captures it from the deploy logs.
    _LOG.warning(
        "==============================================================\n"
        "  FleetFlow bootstrap token (valid 30 min, one-shot):\n"
        "    %s\n"
        "  Pass as X-Bootstrap-Token header to POST /auth/bootstrap-admin.\n"
        "==============================================================",
        token,
    )
