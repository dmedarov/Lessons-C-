"""Guard tests for the "at least one active fleet_admin" invariant.

These exercise the safety net across both /deactivate and /role paths —
deliberately narrow, so a future regression (e.g. someone drops the
`_active_admin_count` check from one branch) surfaces immediately.
"""

from __future__ import annotations

import importlib
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

    from routers import auth, cars, intelligence, notifications, reservations, users

    importlib.reload(auth)
    importlib.reload(cars)
    importlib.reload(intelligence)
    importlib.reload(notifications)
    importlib.reload(reservations)
    importlib.reload(users)
    importlib.reload(app_module)

    with TestClient(app_module.app) as c:
        yield c


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": token}


def _bootstrap_admin(client: TestClient) -> tuple[str, int]:
    client.post(
        "/auth/bootstrap-admin",
        json={"username": "admin", "display_name": "Fleet Admin", "password": "AdminPass123"},
    )
    login = client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    token = f"Bearer {login.json()['access_token']}"
    me = client.get("/auth/me", headers=_auth(token)).json()
    return token, me["id"]


def _create_user(
    client: TestClient, admin: str, username: str, role: str = "employee"
) -> dict:
    res = client.post(
        "/users",
        json={
            "username": username,
            "display_name": username.title(),
            "password": f"{username.title()}Pass123",
            "role": role,
        },
        headers=_auth(admin),
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_last_active_admin_cannot_be_deactivated(client: TestClient) -> None:
    admin, admin_id = _bootstrap_admin(client)

    # Add an employee so the users table isn't empty — the invariant is
    # about *admins*, not total user count.
    _create_user(client, admin, "ivan")

    res = client.post(f"/users/{admin_id}/deactivate", headers=_auth(admin))
    assert res.status_code == 409
    assert "last active fleet_admin" in res.json()["detail"]


def test_last_active_admin_cannot_be_demoted(client: TestClient) -> None:
    admin, admin_id = _bootstrap_admin(client)
    _create_user(client, admin, "ivan")

    res = client.post(
        f"/users/{admin_id}/role",
        json={"role": "employee", "reason": "Should be refused"},
        headers=_auth(admin),
    )
    assert res.status_code == 409
    assert "last active fleet_admin" in res.json()["detail"]


def test_admin_can_be_demoted_when_a_second_admin_exists(client: TestClient) -> None:
    admin, admin_id = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", role="fleet_admin")

    res = client.post(
        f"/users/{admin_id}/role",
        json={"role": "employee", "reason": "Rotation"},
        headers=_auth(admin),
    )
    assert res.status_code == 200
    assert res.json()["role"] == "employee"


def test_admin_can_be_deactivated_when_a_second_active_admin_exists(
    client: TestClient,
) -> None:
    admin, admin_id = _bootstrap_admin(client)
    second = _create_user(client, admin, "ivan", role="fleet_admin")

    # Log in as the second admin so we aren't blocked by the self-deactivation
    # guard on the bootstrap admin.
    second_login = client.post(
        "/auth/login", json={"username": "ivan", "password": "IvanPass123"}
    )
    second_token = f"Bearer {second_login.json()['access_token']}"

    res = client.post(f"/users/{admin_id}/deactivate", headers=_auth(second_token))
    assert res.status_code == 200
    assert res.json()["active"] is False

    # And now the second admin is the last one — they can't deactivate
    # themselves.
    self_res = client.post(f"/users/{second['id']}/deactivate", headers=_auth(second_token))
    assert self_res.status_code == 409


def test_inactive_admin_does_not_count_toward_invariant(client: TestClient) -> None:
    """If a fleet_admin is deactivated, they no longer count as "active admin".

    This protects against a subtle bug where the invariant check only looks at
    role and forgets `active=1`.
    """
    admin, _admin_id = _bootstrap_admin(client)
    second = _create_user(client, admin, "ivan", role="fleet_admin")

    # Deactivate the second admin — leaves exactly one active admin.
    deactivate = client.post(f"/users/{second['id']}/deactivate", headers=_auth(admin))
    assert deactivate.status_code == 200

    # Now the bootstrap admin is the last active one — demoting them must fail.
    me = client.get("/auth/me", headers=_auth(admin)).json()
    res = client.post(
        f"/users/{me['id']}/role",
        json={"role": "employee", "reason": "Should fail with one inactive admin"},
        headers=_auth(admin),
    )
    assert res.status_code == 409
