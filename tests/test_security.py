from __future__ import annotations

import base64
import hmac
import importlib
import json
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DEV_SEED_DEMO_DATA", raising=False)

    import app as app_module
    import config
    import db as db_module
    import notifications_service
    import rate_limit
    import security

    importlib.reload(config)
    importlib.reload(security)
    importlib.reload(db_module)
    importlib.reload(notifications_service)
    importlib.reload(rate_limit)
    importlib.reload(app_module)

    from routers import auth, cars, notifications, reservations, users

    importlib.reload(auth)
    importlib.reload(cars)
    importlib.reload(notifications)
    importlib.reload(reservations)
    importlib.reload(users)
    importlib.reload(app_module)

    with TestClient(app_module.app) as c:
        yield c


def _bootstrap(client: TestClient) -> str:
    client.post(
        "/auth/bootstrap-admin",
        json={"username": "admin", "display_name": "Fleet Admin", "password": "AdminPass123"},
    )
    res = client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    return res.json()["access_token"]


def _split(token: str) -> tuple[str, str]:
    body, sig = token.split(".", 1)
    return body, sig


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def test_issued_token_contains_iat_and_jti(client: TestClient) -> None:
    token = _bootstrap(client)
    body, _sig = _split(token)
    payload = json.loads(_b64url_decode(body).decode("utf-8"))

    assert "iat" in payload
    assert "jti" in payload
    assert "exp" in payload
    # iat should be within a minute of "now" — we just issued it.
    assert abs(int(time.time()) - int(payload["iat"])) < 60
    # jti must be unguessable — base64url without padding, at least 12 bytes.
    assert len(_b64url_decode(payload["jti"])) >= 12


def test_tampered_payload_is_rejected(client: TestClient) -> None:
    token = _bootstrap(client)
    body, sig = _split(token)
    payload = json.loads(_b64url_decode(body).decode("utf-8"))
    # Extend the lifetime 10 years into the future — if signature verification
    # is missing or weak, we'd get a forever-valid token. Signature must reject it.
    payload["exp"] = int(time.time()) + 10 * 365 * 24 * 3600
    forged_body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    forged = f"{forged_body}.{sig}"

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


def test_expired_token_is_rejected(client: TestClient) -> None:
    """Verify_token rejects a structurally valid but past-exp token."""
    import security

    # Hand-build a token with exp in the past, signed with the right key.
    now = int(time.time())
    payload = {
        "sub": 1,
        "u": "admin",
        "n": "Fleet Admin",
        "r": "fleet_admin",
        "iat": now - 3600,
        "exp": now - 60,
        "jti": "abc123",
    }
    import config

    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    import hashlib

    sig = hmac.new(
        config.settings.secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256
    ).digest()
    token = f"{body}.{_b64url_encode(sig)}"

    with pytest.raises(Exception) as exc:
        security.verify_token(token)
    assert "expired" in str(exc.value).lower() or "401" in str(exc.value)


def test_future_iat_is_rejected(client: TestClient) -> None:
    """Tokens that claim to be issued in the future (beyond skew) are refused."""
    import hashlib

    import config
    import security

    now = int(time.time())
    payload = {
        "sub": 1,
        "u": "admin",
        "n": "Fleet Admin",
        "r": "fleet_admin",
        # 10 minutes ahead of now — well beyond 60s skew tolerance.
        "iat": now + 600,
        "exp": now + 7200,
        "jti": "abc123",
    }
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(
        config.settings.secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256
    ).digest()
    token = f"{body}.{_b64url_encode(sig)}"

    with pytest.raises(Exception) as exc:
        security.verify_token(token)
    # Message says "future" — be lenient on wording but check a status code or substring.
    msg = str(exc.value).lower()
    assert "future" in msg or "401" in msg


def test_signature_comparison_is_timing_safe() -> None:
    """Sanity check — verify_token uses hmac.compare_digest, not ==."""
    import inspect

    import security

    src = inspect.getsource(security.verify_token)
    assert "compare_digest" in src, (
        "verify_token should use hmac.compare_digest to avoid timing attacks"
    )


def test_short_secret_refused_in_non_dev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Import-time guard: a short SECRET_KEY must fail fast in prod."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("SECRET_KEY", "short")  # way under 32 bytes
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import config

    importlib.reload(config)
    # security reload should hit _assert_secret_key_strong() and raise.
    with pytest.raises(RuntimeError) as exc:
        import security

        importlib.reload(security)
    assert "SECRET_KEY" in str(exc.value)


def test_short_secret_accepted_in_dev(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dev environments don't enforce the key-length guard so local tinkering works."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("SECRET_KEY", "tiny")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import config
    import security

    importlib.reload(config)
    importlib.reload(security)  # should not raise
