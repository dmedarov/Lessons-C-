"""Phase 3.3 — production gate on /auth/bootstrap-admin.

The dev environment keeps the endpoint permissive for smoke ergonomics; any
other environment (`prod`, `staging`, ...) must present the one-shot token
provisioned at startup."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _reload_stack() -> tuple[object, object]:
    import app as app_module
    import bootstrap_tokens
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
    importlib.reload(bootstrap_tokens)
    importlib.reload(app_module)

    from routers import auth, cars, notifications, reservations, users

    importlib.reload(auth)
    importlib.reload(cars)
    importlib.reload(notifications)
    importlib.reload(reservations)
    importlib.reload(users)
    importlib.reload(app_module)
    return app_module, bootstrap_tokens


@pytest.fixture()
def prod_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, object]]:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "prod.db"))
    # 32-byte secret so security._assert_secret_key_strong() passes.
    monkeypatch.setenv("SECRET_KEY", "k" * 32)
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DEV_SEED_DEMO_DATA", raising=False)
    # Relax rate limits so repeated attempts in one test don't hit 429.
    monkeypatch.setenv("BOOTSTRAP_RATE_LIMIT_ATTEMPTS", "50")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", "50")

    app_module, bootstrap_tokens = _reload_stack()
    with TestClient(app_module.app) as c:
        yield c, bootstrap_tokens


def _payload() -> dict:
    return {"username": "admin", "display_name": "Fleet Admin", "password": "AdminPass123"}


def test_prod_bootstrap_without_header_is_forbidden(prod_client) -> None:
    client, _ = prod_client
    res = client.post("/auth/bootstrap-admin", json=_payload())
    assert res.status_code == 403
    assert "X-Bootstrap-Token" in res.json()["detail"]


def test_prod_bootstrap_with_wrong_token_is_forbidden(prod_client) -> None:
    client, _ = prod_client
    res = client.post(
        "/auth/bootstrap-admin",
        json=_payload(),
        headers={"X-Bootstrap-Token": "totally-wrong-token"},
    )
    assert res.status_code == 403
    assert "Invalid" in res.json()["detail"]


def test_prod_bootstrap_with_correct_token_succeeds_once(prod_client) -> None:
    client, bootstrap_tokens = prod_client
    # The lifespan announces a token into the module's private state. Read it
    # via provision() would replace it — instead, generate a fresh known one
    # to drive the test deterministically.
    token = bootstrap_tokens.provision()
    res = client.post(
        "/auth/bootstrap-admin",
        json=_payload(),
        headers={"X-Bootstrap-Token": token},
    )
    assert res.status_code == 201, res.text

    # A second call with the same token must fail — the admin is created,
    # the token cleared, and the 409 / 403 outcome is fine either way.
    res2 = client.post(
        "/auth/bootstrap-admin",
        json=_payload(),
        headers={"X-Bootstrap-Token": token},
    )
    assert res2.status_code == 403
    assert "No bootstrap token" in res2.json()["detail"]


def test_prod_bootstrap_token_expires(prod_client, monkeypatch: pytest.MonkeyPatch) -> None:
    client, bootstrap_tokens = prod_client
    token = bootstrap_tokens.provision(ttl_seconds=-1)  # already expired
    res = client.post(
        "/auth/bootstrap-admin",
        json=_payload(),
        headers={"X-Bootstrap-Token": token},
    )
    assert res.status_code == 403
    assert "expired" in res.json()["detail"].lower()


def test_dev_bootstrap_still_permissive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Dev ergonomics must not regress — no header needed."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "dev.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    app_module, _ = _reload_stack()
    with TestClient(app_module.app) as c:
        res = c.post("/auth/bootstrap-admin", json=_payload())
        assert res.status_code == 201, res.text
