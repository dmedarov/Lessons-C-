from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

import db


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")

    import importlib

    import app as app_module
    import config
    import db
    import security

    importlib.reload(config)
    importlib.reload(security)
    importlib.reload(db)
    importlib.reload(app_module)
    # Routers were already imported with stale settings; reload them too.
    from routers import auth, cars, reservations

    importlib.reload(auth)
    importlib.reload(cars)
    importlib.reload(reservations)
    importlib.reload(app_module)

    with TestClient(app_module.app) as c:
        yield c


def _login(client: TestClient, username: str, password: str) -> str:
    res = client.post("/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return f"Bearer {res.json()['access_token']}"


def _auth(header: str) -> dict:
    return {"Authorization": header}


def _create_car(client: TestClient, admin: str, plate: str = "CA1234AB") -> int:
    res = client.post("/cars", json={"plate_number": plate, "model": "Skoda Octavia"}, headers=_auth(admin))
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
    assert res.json()["status"] == "pending"
    return res.json()["id"]


def test_login_success_and_failure(client: TestClient) -> None:
    ok = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    bad = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert ok.status_code == 200
    assert ok.json()["role"] == "fleet_admin"
    assert "access_token" in ok.json()
    assert bad.status_code == 401


def test_health_and_ui(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_protected_routes_require_auth(client: TestClient) -> None:
    assert client.post("/cars", json={"plate_number": "X", "model": "Y"}).status_code == 401
    assert client.get("/reservations").status_code == 401


def test_forged_token_rejected(client: TestClient) -> None:
    res = client.post("/cars", json={"plate_number": "CB", "model": "M"}, headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_only_admin_can_create_car(client: TestClient) -> None:
    employee = _login(client, "ivan", "employee123")
    res = client.post("/cars", json={"plate_number": "CB7777AA", "model": "VW Golf"}, headers=_auth(employee))
    assert res.status_code == 403


def test_create_and_list_cars(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    car_id = _create_car(client, admin)
    items = client.get("/cars").json()["items"]
    assert len(items) == 1 and items[0]["id"] == car_id


def test_reservation_workflow(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    employee = _login(client, "ivan", "employee123")

    car_id = _create_car(client, admin, plate="CB1000AA")
    res_id = _create_reservation(client, car_id, employee)

    forbidden = client.post(f"/reservations/{res_id}/approve", json={"reason": "ok"}, headers=_auth(employee))
    assert forbidden.status_code == 403

    approved = client.post(f"/reservations/{res_id}/approve", json={"reason": "Manager approved"}, headers=_auth(admin))
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    # Re-approving a non-pending reservation fails.
    again = client.post(f"/reservations/{res_id}/approve", json={}, headers=_auth(admin))
    assert again.status_code == 409


def test_employee_cannot_cancel_others_reservation(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    employee = _login(client, "ivan", "employee123")

    car_id = _create_car(client, admin, plate="CB2000AA")
    res_id = _create_reservation(client, car_id, employee)

    # Admin can cancel anyone's.
    cancelled = client.post(f"/reservations/{res_id}/cancel", headers=_auth(admin))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_overlap_blocked_for_pending_and_approved(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    employee = _login(client, "ivan", "employee123")

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


def test_end_time_must_be_future(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    employee = _login(client, "ivan", "employee123")
    car_id = _create_car(client, admin, plate="CB4000AA")

    res = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2000-01-01T09:00:00+00:00",
            "end_time": "2000-01-01T11:00:00+00:00",
        },
        headers=_auth(employee),
    )
    assert res.status_code == 400


def test_employee_list_sees_only_own_reservations(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    employee = _login(client, "ivan", "employee123")

    car_id = _create_car(client, admin, plate="CB5000AA")
    _create_reservation(client, car_id, employee)

    # Admin also makes a reservation.
    r = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-05-01T09:00:00+00:00",
            "end_time": "2099-05-01T11:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201

    admin_list = client.get("/reservations", headers=_auth(admin)).json()
    employee_list = client.get("/reservations", headers=_auth(employee)).json()

    assert admin_list["total"] == 2
    assert employee_list["total"] == 1


def test_deactivated_car_rejects_new_reservations(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    employee = _login(client, "ivan", "employee123")
    car_id = _create_car(client, admin, plate="CB6000AA")

    deact = client.post(f"/cars/{car_id}/deactivate", headers=_auth(admin))
    assert deact.status_code == 200

    res = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-06-01T09:00:00+00:00",
            "end_time": "2099-06-01T11:00:00+00:00",
        },
        headers=_auth(employee),
    )
    assert res.status_code == 409


def test_deactivated_user_token_is_rejected(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")

    with db.get_conn() as conn:
        conn.execute("UPDATE users SET active=0 WHERE username='admin'")

    res = client.post("/cars", json={"plate_number": "CB7000AA", "model": "Audi A4"}, headers=_auth(admin))
    assert res.status_code == 401


def test_role_change_removes_admin_access_for_existing_token(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")

    with db.get_conn() as conn:
        conn.execute("UPDATE users SET role='employee' WHERE username='admin'")

    res = client.post("/cars", json={"plate_number": "CB8000AA", "model": "Audi A6"}, headers=_auth(admin))
    assert res.status_code == 403


def test_start_time_must_be_future(client: TestClient) -> None:
    admin = _login(client, "admin", "admin123")
    employee = _login(client, "ivan", "employee123")
    car_id = _create_car(client, admin, plate="CB9000AA")

    res = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2000-01-01T09:00:00+00:00",
            "end_time": "2099-01-01T11:00:00+00:00",
        },
        headers=_auth(employee),
    )
    assert res.status_code == 400
