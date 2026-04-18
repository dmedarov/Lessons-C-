from __future__ import annotations

import importlib
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

import db


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import app as app_module
    import config
    import db as db_module
    import notifications_service
    import security

    importlib.reload(config)
    importlib.reload(security)
    importlib.reload(db_module)
    importlib.reload(notifications_service)
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": token}


def _bootstrap_admin(
    client: TestClient,
    username: str = "admin",
    display_name: str = "Fleet Admin",
    password: str = "AdminPass123",
) -> str:
    res = client.post(
        "/auth/bootstrap-admin",
        json={"username": username, "display_name": display_name, "password": password},
    )
    assert res.status_code == 201, res.text
    return _login(client, username, password)


def _login(client: TestClient, username: str, password: str) -> str:
    res = client.post("/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return f"Bearer {res.json()['access_token']}"


def _create_user(
    client: TestClient,
    admin_token: str,
    username: str,
    display_name: str,
    password: str,
    role: str = "employee",
) -> dict:
    res = client.post(
        "/users",
        json={
            "username": username,
            "display_name": display_name,
            "password": password,
            "role": role,
        },
        headers=_auth(admin_token),
    )
    assert res.status_code == 201, res.text
    return res.json()


def _create_car(client: TestClient, admin_token: str, plate: str = "CA1234AB") -> int:
    res = client.post(
        "/cars",
        json={"plate_number": plate, "model": "Skoda Octavia"},
        headers=_auth(admin_token),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _create_reservation(client: TestClient, car_id: int, token: str) -> int:
    res = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-04-18T09:00:00+00:00",
            "end_time": "2099-04-18T11:00:00+00:00",
            "purpose": "Client meeting",
        },
        headers=_auth(token),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _list_notifications(client: TestClient, token: str, unread_only: bool = False) -> list[dict]:
    query = "?unread_only=true" if unread_only else ""
    res = client.get(f"/notifications{query}", headers=_auth(token))
    assert res.status_code == 200, res.text
    return res.json()


def test_database_url_switches_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("DATABASE_URL", "postgresql://fleetflow:secret@postgres:5432/fleetflow")

    import config

    importlib.reload(config)
    assert config.settings.db_backend == "postgres"


def test_prod_init_db_starts_without_demo_users(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "prod.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import config

    importlib.reload(config)
    importlib.reload(db)

    db.init_db()

    with db.get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()

    assert row["n"] == 0


def test_setup_status_and_bootstrap_flow(client: TestClient) -> None:
    assert client.get("/auth/setup-status").json() == {"has_admin": False}

    admin = _bootstrap_admin(client)
    assert client.get("/auth/setup-status").json() == {"has_admin": True}

    me = client.get("/auth/me", headers=_auth(admin))
    assert me.status_code == 200
    assert me.json()["role"] == "fleet_admin"

    again = client.post(
        "/auth/bootstrap-admin",
        json={"username": "otheradmin", "display_name": "Other Admin", "password": "AdminPass456"},
    )
    assert again.status_code == 409


def test_login_success_and_failure(client: TestClient) -> None:
    _bootstrap_admin(client)
    ok = client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    bad = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert ok.status_code == 200
    assert ok.json()["role"] == "fleet_admin"
    assert bad.status_code == 401


def test_user_management_and_password_change(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    created = _create_user(client, admin, "maria", "Maria Petrova", "MariaPass123")
    employee = _login(client, "maria", "MariaPass123")

    users = client.get("/users", headers=_auth(admin))
    assert users.status_code == 200
    assert len(users.json()) == 2

    me = client.get("/auth/me", headers=_auth(employee))
    assert me.status_code == 200
    assert me.json()["username"] == "maria"

    changed = client.post(
        "/users/me/password",
        json={"current_password": "MariaPass123", "new_password": "MariaPass456"},
        headers=_auth(employee),
    )
    assert changed.status_code == 204

    old_login = client.post("/auth/login", json={"username": "maria", "password": "MariaPass123"})
    new_login = client.post("/auth/login", json={"username": "maria", "password": "MariaPass456"})
    assert old_login.status_code == 401
    assert new_login.status_code == 200

    deactivated = client.post(f"/users/{created['id']}/deactivate", headers=_auth(admin))
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    stale = client.get("/auth/me", headers=_auth(employee))
    assert stale.status_code == 401

    reactivated = client.post(f"/users/{created['id']}/activate", headers=_auth(admin))
    assert reactivated.status_code == 200
    assert reactivated.json()["active"] is True


def test_last_admin_cannot_deactivate_self(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    me = client.get("/auth/me", headers=_auth(admin)).json()

    res = client.post(f"/users/{me['id']}/deactivate", headers=_auth(admin))
    assert res.status_code == 409


def test_only_admin_can_create_car_and_list_users(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")

    car = client.post(
        "/cars",
        json={"plate_number": "CB7777AA", "model": "VW Golf"},
        headers=_auth(employee),
    )
    users = client.get("/users", headers=_auth(employee))
    assert car.status_code == 403
    assert users.status_code == 403


def test_end_to_end_admin_two_users_workflow(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    _create_user(client, admin, "maria", "Maria Petrova", "MariaPass123")

    employee_one = _login(client, "ivan", "IvanPass123")
    employee_two = _login(client, "maria", "MariaPass123")

    car_id = _create_car(client, admin, plate="CB1000AA")
    reservation_id = _create_reservation(client, car_id, employee_one)

    approve = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Approved by fleet admin"},
        headers=_auth(admin),
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    admin_notifications = _list_notifications(client, admin)
    employee_one_notifications = _list_notifications(client, employee_one)
    employee_two_notifications = _list_notifications(client, employee_two)

    assert len(admin_notifications) == 1
    assert admin_notifications[0]["kind"] == "reservation_requested"
    assert len(employee_one_notifications) == 1
    assert employee_one_notifications[0]["kind"] == "reservation_decision"
    assert employee_two_notifications == []

    admin_list = client.get("/reservations", headers=_auth(admin)).json()
    employee_one_list = client.get("/reservations", headers=_auth(employee_one)).json()
    employee_two_list = client.get("/reservations", headers=_auth(employee_two)).json()

    assert admin_list["total"] == 1
    assert employee_one_list["total"] == 1
    assert employee_one_list["items"][0]["status"] == "approved"
    assert employee_two_list["total"] == 0

    start_trip = client.post(
        f"/reservations/{reservation_id}/start",
        json={"note": "Keys collected from reception"},
        headers=_auth(employee_one),
    )
    assert start_trip.status_code == 200
    assert start_trip.json()["status"] == "checked_out"

    after_start_admin_notifications = _list_notifications(client, admin, unread_only=True)
    assert len(after_start_admin_notifications) == 2
    assert after_start_admin_notifications[0]["kind"] == "trip_started"

    returned = client.post(
        f"/reservations/{reservation_id}/return",
        json={"note": "Vehicle returned clean and parked"},
        headers=_auth(employee_one),
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "returned"

    returned_filter = client.get(
        "/reservations?status_filter=returned",
        headers=_auth(admin),
    )
    assert returned_filter.status_code == 200
    assert returned_filter.json()["total"] == 1

    read_notification = client.post(
        f"/notifications/{employee_one_notifications[0]['id']}/read",
        headers=_auth(employee_one),
    )
    assert read_notification.status_code == 200
    assert read_notification.json()["read_at"] is not None

    forbidden_cancel = client.post(f"/reservations/{reservation_id}/cancel", headers=_auth(employee_two))
    assert forbidden_cancel.status_code == 403


def test_notifications_read_all_and_visibility(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")
    car_id = _create_car(client, admin, plate="CB5000AA")
    reservation_id = _create_reservation(client, car_id, employee)

    approve = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Approved for customer visit"},
        headers=_auth(admin),
    )
    assert approve.status_code == 200

    employee_notifications = _list_notifications(client, employee, unread_only=True)
    assert len(employee_notifications) == 1

    mark_all = client.post("/notifications/read-all", headers=_auth(employee))
    assert mark_all.status_code == 200
    assert mark_all.json()["updated"] == 1

    after = _list_notifications(client, employee, unread_only=True)
    assert after == []


def test_blackout_blocks_and_then_allows_reservation(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")
    car_id = _create_car(client, admin, plate="CB6000AA")

    blackout = client.post(
        f"/cars/{car_id}/blackouts",
        json={
            "start_time": "2099-04-18T08:00:00+00:00",
            "end_time": "2099-04-18T12:00:00+00:00",
            "kind": "maintenance",
            "reason": "Planned service",
        },
        headers=_auth(admin),
    )
    assert blackout.status_code == 201, blackout.text

    blocked = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-04-18T09:00:00+00:00",
            "end_time": "2099-04-18T11:00:00+00:00",
            "purpose": "Client meeting",
        },
        headers=_auth(employee),
    )
    assert blocked.status_code == 409

    disabled = client.post(
        f"/cars/blackouts/{blackout.json()['id']}/deactivate",
        headers=_auth(admin),
    )
    assert disabled.status_code == 200
    assert disabled.json()["active"] is False

    allowed = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-04-18T09:00:00+00:00",
            "end_time": "2099-04-18T11:00:00+00:00",
            "purpose": "Client meeting",
        },
        headers=_auth(employee),
    )
    assert allowed.status_code == 201


def test_admin_handoff_promotes_target_and_demotes_actor(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    created = _create_user(client, admin, "maria", "Maria Petrova", "MariaPass123")
    maria = _login(client, "maria", "MariaPass123")

    handoff = client.post(
        f"/users/{created['id']}/handoff-admin",
        json={"demote_self": True, "reason": "Shifting operational ownership"},
        headers=_auth(admin),
    )
    assert handoff.status_code == 200, handoff.text
    assert handoff.json()["previous_admin"]["role"] == "employee"
    assert handoff.json()["next_admin"]["role"] == "fleet_admin"

    old_admin_me = client.get("/auth/me", headers=_auth(admin))
    new_admin_me = client.get("/auth/me", headers=_auth(maria))
    assert old_admin_me.status_code == 200
    assert old_admin_me.json()["role"] == "employee"
    assert new_admin_me.status_code == 200
    assert new_admin_me.json()["role"] == "fleet_admin"

    forbidden = client.post(
        "/cars",
        json={"plate_number": "CB7000AA", "model": "Toyota Corolla"},
        headers=_auth(admin),
    )
    allowed = client.post(
        "/cars",
        json={"plate_number": "CB7001AA", "model": "Toyota Corolla"},
        headers=_auth(maria),
    )
    assert forbidden.status_code == 403
    assert allowed.status_code == 201

    maria_notifications = _list_notifications(client, maria)
    assert maria_notifications[0]["kind"] == "admin_handoff"


def test_outbound_dispatch_hook_runs_for_notifications(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import routers.reservations as reservations_router
    import routers.users as users_router

    captured: list[int] = []

    def _capture(notification_ids: list[int]) -> None:
        captured.extend(notification_ids)

    monkeypatch.setattr(reservations_router, "dispatch_outbound_notifications", _capture)
    monkeypatch.setattr(users_router, "dispatch_outbound_notifications", _capture)

    admin = _bootstrap_admin(client)
    created = _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")
    car_id = _create_car(client, admin, plate="CB8000AA")
    reservation_id = _create_reservation(client, car_id, employee)

    approve = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Approved"},
        headers=_auth(admin),
    )
    assert approve.status_code == 200

    handoff = client.post(
        f"/users/{created['id']}/handoff-admin",
        json={"demote_self": False, "reason": "Co-admin handoff"},
        headers=_auth(admin),
    )
    assert handoff.status_code == 200
    assert captured


def test_overlap_blocked_for_pending_and_approved(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")

    car_id = _create_car(client, admin, plate="CB3000AA")
    _create_reservation(client, car_id, employee)

    overlap = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-04-18T10:00:00+00:00",
            "end_time": "2099-04-18T12:00:00+00:00",
        },
        headers=_auth(employee),
    )
    assert overlap.status_code == 409


def test_start_time_and_end_time_validation(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")
    car_id = _create_car(client, admin, plate="CB4000AA")

    past_start = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2000-01-01T09:00:00+00:00",
            "end_time": "2099-01-01T11:00:00+00:00",
        },
        headers=_auth(employee),
    )
    wrong_order = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-01-01T11:00:00+00:00",
            "end_time": "2099-01-01T09:00:00+00:00",
        },
        headers=_auth(employee),
    )
    assert past_start.status_code == 400
    assert wrong_order.status_code == 400


def test_protected_routes_require_auth(client: TestClient) -> None:
    assert client.post("/cars", json={"plate_number": "X", "model": "Y"}).status_code == 401
    assert client.get("/reservations").status_code == 401
    assert client.get("/users").status_code == 401


def test_health_and_ui(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    res = client.get("/")
    admin_res = client.get("/admin")
    assert res.status_code == 200
    assert admin_res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "text/html" in admin_res.headers["content-type"]
    assert "/static/i18n.js" in res.text
    assert "/static/i18n.js" in admin_res.text
