from pathlib import Path

from fastapi.testclient import TestClient

import app as app_module


ADMIN_HEADERS = {"X-User": "Admin", "X-Role": "fleet_admin"}
EMPLOYEE_HEADERS = {"X-User": "Ivan Petrov", "X-Role": "employee"}


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return f"Bearer {token}"


def _create_car(client: TestClient, auth_header: str, plate: str = "CA1234AB", model: str = "Skoda Octavia") -> int:
    resp = client.post(
        "/cars",
        json={"plate_number": plate, "model": model},
        headers={"Authorization": auth_header},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_reservation(client: TestClient, car_id: int, auth_header: str, user: str = "Ivan Petrov") -> int:
    response = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "employee_name": user,
            "start_time": "2026-04-18T09:00:00",
            "end_time": "2026-04-18T11:00:00",
            "purpose": "Client meeting",
        },
        headers={"Authorization": auth_header},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    return response.json()["id"]


def test_login_success_and_failure() -> None:
    with TestClient(app_module.app) as client:
        ok = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
        bad = client.post("/auth/login", json={"username": "admin", "password": "wrong"})

    assert ok.status_code == 200
    assert ok.json()["role"] == "fleet_admin"
    assert bad.status_code == 401


def test_health() -> None:
    with TestClient(app_module.app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ui_route_serves_html() -> None:
    with TestClient(app_module.app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_only_admin_can_create_car(tmp_path: Path) -> None:
    app_module.DB_PATH = str(tmp_path / "fleet.db")
    app_module.init_db()

    with TestClient(app_module.app) as client:
        response = client.post(
            "/cars",
            json={"plate_number": "CB7777AA", "model": "VW Golf"},
            headers=EMPLOYEE_HEADERS,
        )

    assert response.status_code == 403


def test_create_and_list_cars_with_token(tmp_path: Path) -> None:
    app_module.DB_PATH = str(tmp_path / "fleet.db")
    app_module.init_db()

    with TestClient(app_module.app) as client:
        admin_token = _login(client, "admin", "admin123")
        car_id = _create_car(client, admin_token)
        response = client.get("/cars")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == car_id


def test_approval_workflow_roles_and_status(tmp_path: Path) -> None:
    app_module.DB_PATH = str(tmp_path / "fleet.db")
    app_module.init_db()

    with TestClient(app_module.app) as client:
        admin_token = _login(client, "admin", "admin123")
        employee_token = _login(client, "ivan", "employee123")

        car_id = _create_car(client, admin_token, plate="CB1000AA")
        reservation_id = _create_reservation(client, car_id, employee_token, user="Ivan Petrov")

        forbidden = client.post(
            f"/reservations/{reservation_id}/approve",
            json={"reason": "ok"},
            headers={"Authorization": employee_token},
        )
        assert forbidden.status_code == 403

        approved = client.post(
            f"/reservations/{reservation_id}/approve",
            json={"reason": "Manager approved"},
            headers={"Authorization": admin_token},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"


def test_cancel_permissions(tmp_path: Path) -> None:
    app_module.DB_PATH = str(tmp_path / "fleet.db")
    app_module.init_db()

    with TestClient(app_module.app) as client:
        admin_token = _login(client, "admin", "admin123")
        employee_token = _login(client, "ivan", "employee123")

        car_id = _create_car(client, admin_token, plate="CB2000AA")
        reservation_id = _create_reservation(client, car_id, employee_token, user="Ivan Petrov")

        denied = client.post(
            f"/reservations/{reservation_id}/cancel",
            headers={"X-User": "Maria Ivanova", "X-Role": "employee"},
        )
        assert denied.status_code == 403

        cancelled = client.post(
            f"/reservations/{reservation_id}/cancel",
            headers={"Authorization": employee_token},
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"


def test_overlap_check_uses_pending_and_approved(tmp_path: Path) -> None:
    app_module.DB_PATH = str(tmp_path / "fleet.db")
    app_module.init_db()

    with TestClient(app_module.app) as client:
        admin_token = _login(client, "admin", "admin123")
        employee_token = _login(client, "ivan", "employee123")

        car_id = _create_car(client, admin_token, plate="CB3000AA")
        _create_reservation(client, car_id, employee_token, user="Ivan Petrov")

        overlap = client.post(
            "/reservations",
            json={
                "car_id": car_id,
                "employee_name": "Maria Ivanova",
                "start_time": "2026-04-18T10:00:00",
                "end_time": "2026-04-18T12:00:00",
            },
            headers={"Authorization": employee_token},
        )
        assert overlap.status_code == 409
