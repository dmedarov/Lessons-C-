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


def _bootstrap(client: TestClient) -> str:
    client.post(
        "/auth/bootstrap-admin",
        json={"username": "admin", "display_name": "Fleet Admin", "password": "AdminPass123"},
    )
    res = client.post("/auth/login", json={"username": "admin", "password": "AdminPass123"})
    return f"Bearer {res.json()['access_token']}"


def _make_employee(client: TestClient, admin: str) -> str:
    client.post(
        "/users",
        json={
            "username": "ivan",
            "display_name": "Иван Петров",
            "password": "IvanPass123",
            "role": "employee",
        },
        headers=_auth(admin),
    )
    res = client.post("/auth/login", json={"username": "ivan", "password": "IvanPass123"})
    return f"Bearer {res.json()['access_token']}"


def _make_car(client: TestClient, admin: str, plate: str = "CB1234AB") -> int:
    res = client.post(
        "/cars",
        json={"plate_number": plate, "model": "Skoda Octavia"},
        headers=_auth(admin),
    )
    return res.json()["id"]


def _make_reservation(
    client: TestClient,
    employee: str,
    car_id: int,
    start: str = "2099-04-18T09:00:00+00:00",
    end: str = "2099-04-18T11:00:00+00:00",
    purpose: str = "Среща с клиент",
) -> int:
    res = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": start,
            "end_time": end,
            "purpose": purpose,
        },
        headers=_auth(employee),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def test_csv_export_requires_admin(client: TestClient) -> None:
    admin = _bootstrap(client)
    employee = _make_employee(client, admin)

    res = client.get("/reservations/export.csv", headers=_auth(employee))
    assert res.status_code == 403


def test_csv_export_unauthorized_without_token(client: TestClient) -> None:
    _bootstrap(client)
    res = client.get("/reservations/export.csv")
    assert res.status_code == 401


def test_csv_export_contains_bom_and_header(client: TestClient) -> None:
    admin = _bootstrap(client)
    employee = _make_employee(client, admin)
    car_id = _make_car(client, admin, plate="CB2000AB")
    _make_reservation(client, employee, car_id)

    res = client.get("/reservations/export.csv", headers=_auth(admin))
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "attachment" in res.headers.get("content-disposition", "")

    body = res.content
    # UTF-8 BOM so Excel opens Cyrillic correctly.
    assert body.startswith(b"\xef\xbb\xbf")

    text = body.decode("utf-8-sig")
    lines = text.strip().splitlines()
    # Header + one data row.
    assert lines[0].split(",")[:4] == ["id", "car_id", "plate_number", "employee_id"]
    assert len(lines) == 2
    # The plate number should be present in the data row.
    assert "CB2000AB" in lines[1]
    # Bulgarian purpose should survive round-trip through UTF-8.
    assert "Среща с клиент" in lines[1]


def test_csv_export_filters_by_car(client: TestClient) -> None:
    admin = _bootstrap(client)
    employee = _make_employee(client, admin)
    car_a = _make_car(client, admin, plate="CB3000AA")
    car_b = _make_car(client, admin, plate="CB3000BB")
    _make_reservation(
        client,
        employee,
        car_a,
        start="2099-05-01T09:00:00+00:00",
        end="2099-05-01T10:00:00+00:00",
    )
    _make_reservation(
        client,
        employee,
        car_b,
        start="2099-05-02T09:00:00+00:00",
        end="2099-05-02T10:00:00+00:00",
    )

    res = client.get(f"/reservations/export.csv?car_id={car_a}", headers=_auth(admin))
    assert res.status_code == 200
    text = res.content.decode("utf-8-sig")
    lines = text.strip().splitlines()
    assert len(lines) == 2  # header + one matching row
    assert "CB3000AA" in lines[1]
    assert "CB3000BB" not in text


def test_csv_export_filters_by_status(client: TestClient) -> None:
    admin = _bootstrap(client)
    employee = _make_employee(client, admin)
    car_id = _make_car(client, admin, plate="CB4000AA")
    r1 = _make_reservation(
        client,
        employee,
        car_id,
        start="2099-06-01T09:00:00+00:00",
        end="2099-06-01T10:00:00+00:00",
    )
    _make_reservation(
        client,
        employee,
        car_id,
        start="2099-06-02T09:00:00+00:00",
        end="2099-06-02T10:00:00+00:00",
    )
    approve = client.post(
        f"/reservations/{r1}/approve",
        json={"reason": "Approved"},
        headers=_auth(admin),
    )
    assert approve.status_code == 200

    res = client.get(
        "/reservations/export.csv?status_filter=approved", headers=_auth(admin)
    )
    assert res.status_code == 200
    lines = res.content.decode("utf-8-sig").strip().splitlines()
    # Header + one approved row.
    assert len(lines) == 2
    assert ",approved," in lines[1]


def test_csv_export_filters_by_search_and_date_window(client: TestClient) -> None:
    admin = _bootstrap(client)
    employee = _make_employee(client, admin)
    car_a = _make_car(client, admin, plate="CB5001AA")
    car_b = _make_car(client, admin, plate="CB5001BB")
    _make_reservation(
        client,
        employee,
        car_a,
        start="2099-07-01T09:00:00+00:00",
        end="2099-07-01T10:00:00+00:00",
        purpose="Moonshot review",
    )
    _make_reservation(
        client,
        employee,
        car_b,
        start="2099-08-01T09:00:00+00:00",
        end="2099-08-01T10:00:00+00:00",
        purpose="Routine route",
    )

    search = client.get("/reservations/export.csv?search=moonshot", headers=_auth(admin))
    assert search.status_code == 200
    search_text = search.content.decode("utf-8-sig")
    assert "CB5001AA" in search_text
    assert "CB5001BB" not in search_text

    window = client.get(
        "/reservations/export.csv",
        params={
            "start": "2099-08-01T00:00:00+00:00",
            "end": "2099-08-02T00:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert window.status_code == 200
    window_text = window.content.decode("utf-8-sig")
    assert "CB5001AA" not in window_text
    assert "CB5001BB" in window_text

    invalid = client.get(
        "/reservations/export.csv",
        params={
            "start": "2099-08-03T00:00:00+00:00",
            "end": "2099-08-02T00:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert invalid.status_code == 400
