"""Phase 3.1 - refresh-token rotation and logout invalidation."""

from fastapi.testclient import TestClient

import db
from tests.test_app import _auth, _bootstrap_admin, client  # noqa: F401


REFRESH_COOKIE = "fleetflow_refresh"


def _refresh_cookie(test_client: TestClient) -> str:
    value = test_client.cookies.get(REFRESH_COOKIE)
    assert value
    return value


def _force_refresh_cookie(test_client: TestClient, value: str) -> None:
    test_client.cookies.clear()
    test_client.cookies.set(REFRESH_COOKIE, value)


def test_login_sets_refresh_cookie_and_refresh_rotates(client: TestClient) -> None:  # noqa: F811
    old_access = _bootstrap_admin(client)
    old_refresh = _refresh_cookie(client)

    res = client.post("/auth/refresh")

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["access_token"]
    assert f"Bearer {body['access_token']}" != old_access
    assert _refresh_cookie(client) != old_refresh

    me = client.get("/auth/me", headers=_auth(f"Bearer {body['access_token']}"))
    assert me.status_code == 200
    assert me.json()["role"] == "fleet_admin"

    with db.get_conn() as conn:
        rows = conn.execute("SELECT revoked_at FROM refresh_tokens ORDER BY id").fetchall()
    assert len(rows) == 2
    assert rows[0]["revoked_at"] is not None
    assert rows[1]["revoked_at"] is None


def test_refresh_replay_revokes_current_chain(client: TestClient) -> None:  # noqa: F811
    _bootstrap_admin(client)
    old_refresh = _refresh_cookie(client)
    first = client.post("/auth/refresh")
    assert first.status_code == 200
    rotated_refresh = _refresh_cookie(client)

    _force_refresh_cookie(client, old_refresh)
    replay = client.post("/auth/refresh")
    assert replay.status_code == 401

    _force_refresh_cookie(client, rotated_refresh)
    after_replay = client.post("/auth/refresh")
    assert after_replay.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:  # noqa: F811
    _bootstrap_admin(client)
    refresh = _refresh_cookie(client)

    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    _force_refresh_cookie(client, refresh)
    res = client.post("/auth/refresh")
    assert res.status_code == 401
