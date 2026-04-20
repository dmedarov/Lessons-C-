from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def strict_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Fresh app with very tight rate limits so we can assert the 429 path."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "2")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("BOOTSTRAP_RATE_LIMIT_ATTEMPTS", "2")
    monkeypatch.setenv("BOOTSTRAP_RATE_LIMIT_WINDOW_SECONDS", "3600")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import app as app_module
    import bootstrap_tokens
    import config
    import db as db_module
    import notifications_service
    import rate_limit as rate_limit_module
    import security

    importlib.reload(config)
    importlib.reload(security)
    importlib.reload(db_module)
    importlib.reload(notifications_service)
    importlib.reload(rate_limit_module)
    importlib.reload(bootstrap_tokens)
    importlib.reload(app_module)

    from routers import auth, cars, intelligence, notifications, reservations, users

    importlib.reload(auth)
    importlib.reload(cars)
    importlib.reload(intelligence)
    importlib.reload(notifications)
    importlib.reload(reservations)
    importlib.reload(users)
    importlib.reload(app_module)

    # Ensure a clean bucket even if a prior test leaked state before reload.
    rate_limit_module.limiter.reset()

    with TestClient(app_module.app) as c:
        yield c


def test_login_rate_limit_returns_429(strict_client: TestClient) -> None:
    # Seed an admin — bootstrap uses its own bucket, so login is untouched here.
    strict_client.post(
        "/auth/bootstrap-admin",
        json={"username": "admin", "display_name": "Fleet Admin", "password": "AdminPass123"},
    )

    first = strict_client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    second = strict_client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    third = strict_client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_bootstrap_rate_limit_returns_429(strict_client: TestClient) -> None:
    # The limiter fires inside the handler before the admin-exists check, so each
    # call with a valid payload counts as one attempt regardless of the 409/201.
    payload = {
        "username": "admin",
        "display_name": "Fleet Admin",
        "password": "AdminPass123",
    }

    r1 = strict_client.post("/auth/bootstrap-admin", json=payload)
    r2 = strict_client.post("/auth/bootstrap-admin", json=payload)
    r3 = strict_client.post("/auth/bootstrap-admin", json=payload)

    assert r1.status_code == 201
    assert r2.status_code == 409  # admin already exists, but the limiter counted it
    assert r3.status_code == 429


def test_rate_limit_reset_clears_buckets(strict_client: TestClient) -> None:
    import rate_limit as rate_limit_module

    strict_client.post(
        "/auth/bootstrap-admin",
        json={"username": "admin", "display_name": "Fleet Admin", "password": "AdminPass123"},
    )
    strict_client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    strict_client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    blocked = strict_client.post(
        "/auth/login", json={"username": "admin", "password": "AdminPass123"}
    )
    assert blocked.status_code == 429

    rate_limit_module.limiter.reset()

    recovered = strict_client.post(
        "/auth/login", json={"username": "admin", "password": "AdminPass123"}
    )
    assert recovered.status_code == 200
