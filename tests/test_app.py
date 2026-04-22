from __future__ import annotations

import importlib
import json
import logging
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import db


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
    email: str | None = None,
    gsm_number: str | None = None,
) -> dict:
    payload = {
        "username": username,
        "display_name": display_name,
        "password": password,
        "role": role,
    }
    if email is not None:
        payload["email"] = email
    if gsm_number is not None:
        payload["gsm_number"] = gsm_number
    res = client.post(
        "/users",
        json=payload,
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


def _create_reservation(
    client: TestClient,
    car_id: int,
    token: str,
    start: str = "2099-04-18T09:00:00+00:00",
    end: str = "2099-04-18T11:00:00+00:00",
    purpose: str = "Client meeting",
) -> int:
    res = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": start,
            "end_time": end,
            "purpose": purpose,
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
    monkeypatch.delenv("DEV_SEED_DEMO_DATA", raising=False)

    import config

    importlib.reload(config)
    importlib.reload(db)

    db.init_db()

    with db.get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()

    assert row["n"] == 0


def test_dev_seed_demo_data_resets_local_test_accounts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "dev.db"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("DEV_SEED_DEMO_DATA", "true")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    import config
    import db as db_module

    importlib.reload(config)
    importlib.reload(db_module)

    db_module.init_db()
    db_module.init_db()

    with db_module.get_conn() as conn:
        users = conn.execute("SELECT username, role, active, password_hash FROM users ORDER BY username").fetchall()
        cars = conn.execute("SELECT plate_number, model, active FROM cars ORDER BY plate_number").fetchall()

    assert {row["username"]: (row["role"], row["active"]) for row in users} == {
        "admin": ("fleet_admin", 1),
        "ivan": ("employee", 1),
        "maria": ("employee", 1),
    }
    assert {row["plate_number"]: (row["model"], row["active"]) for row in cars} == {
        "CA1330PT": ("HYUNDAI i30 Wagon", 1),
        "CA6945TB": ("HYUNDAI i30 Wagon", 1),
        "CA6946TB": ("HYUNDAI i30 Wagon", 1),
        "CA6947TB": ("HYUNDAI i20", 1),
        "CB2426BH": ("HYUNDAI i20", 1),
    }

    import security

    password_by_user = {
        "admin": "AdminPass123",
        "ivan": "IvanPass123",
        "maria": "MariaPass123",
    }
    assert all(security.verify_password(password_by_user[row["username"]], row["password_hash"]) for row in users)


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


def test_login_rate_limit_rejects_repeated_bad_attempts(client: TestClient) -> None:
    for _ in range(5):
        res = client.post("/auth/login", json={"username": "ghost", "password": "wrong"})
        assert res.status_code == 401

    limited = client.post("/auth/login", json={"username": "ghost", "password": "wrong"})
    assert limited.status_code == 429
    assert "Твърде много опити" in limited.json()["detail"]


def test_user_management_and_password_change(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    created = _create_user(
        client,
        admin,
        "maria",
        "Maria Petrova",
        "MariaPass123",
        email="maria@company.bg",
        gsm_number="+359 88 123 4567",
    )
    employee = _login(client, "maria", "MariaPass123")

    users = client.get("/users", headers=_auth(admin))
    assert users.status_code == 200
    assert len(users.json()) == 2
    maria = next(user for user in users.json() if user["username"] == "maria")
    assert created["email"] == "maria@company.bg"
    assert created["gsm_number"] == "+359 88 123 4567"
    assert maria["gsm_number"] == "+359 88 123 4567"

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


def test_admin_can_reset_password_and_audit_records_action(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    created = _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")

    forbidden = client.post(
        f"/users/{created['id']}/reset-password",
        json={"new_password": "IvanPass456", "reason": "Forgotten password"},
        headers=_auth(employee),
    )
    assert forbidden.status_code == 403

    reset = client.post(
        f"/users/{created['id']}/reset-password",
        json={"new_password": "IvanPass456", "reason": "Forgotten password"},
        headers=_auth(admin),
    )
    assert reset.status_code == 204

    old_login = client.post("/auth/login", json={"username": "ivan", "password": "IvanPass123"})
    new_login = client.post("/auth/login", json={"username": "ivan", "password": "IvanPass456"})
    assert old_login.status_code == 401
    assert new_login.status_code == 200

    audit = client.get(f"/users/{created['id']}/audit", headers=_auth(admin))
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "password_reset"
    assert audit.json()[0]["reason"] == "Forgotten password"

    employee_audit = client.get(f"/users/{created['id']}/audit", headers=_auth(employee))
    assert employee_audit.status_code == 403


def test_user_gsm_number_is_optional_and_length_limited(client: TestClient) -> None:
    admin = _bootstrap_admin(client)

    no_phone = _create_user(client, admin, "no-phone", "No Phone", "UserPass123")
    assert no_phone["gsm_number"] is None

    too_long = client.post(
        "/users",
        json={
            "username": "long-phone",
            "display_name": "Long Phone",
            "password": "UserPass123",
            "role": "employee",
            "gsm_number": "+" + ("1" * 40),
        },
        headers=_auth(admin),
    )
    assert too_long.status_code == 422


def test_admin_can_update_user_contact_fields(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    created = _create_user(client, admin, "contact-user", "Contact User", "UserPass123")
    employee = _login(client, "contact-user", "UserPass123")

    forbidden = client.put(
        f"/users/{created['id']}/contact",
        json={"email": "blocked@example.com", "gsm_number": "+359000000000"},
        headers=_auth(employee),
    )
    assert forbidden.status_code == 403

    updated = client.put(
        f"/users/{created['id']}/contact",
        json={
            "email": "contact.user@example.com",
            "gsm_number": "+359882422442",
            "reason": "Production contact correction",
        },
        headers=_auth(admin),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["email"] == "contact.user@example.com"
    assert updated.json()["gsm_number"] == "+359882422442"

    users = client.get("/users", headers=_auth(admin)).json()
    assert next(user for user in users if user["id"] == created["id"])["gsm_number"] == "+359882422442"

    too_long = client.put(
        f"/users/{created['id']}/contact",
        json={"gsm_number": "+" + ("1" * 40)},
        headers=_auth(admin),
    )
    assert too_long.status_code == 422

    audit = client.get(f"/users/{created['id']}/audit", headers=_auth(admin))
    assert audit.status_code == 200
    assert audit.json()[0]["action"] == "contact_updated"
    assert audit.json()[0]["reason"] == "Production contact correction"


def test_admin_can_bulk_import_employee_names_and_gsm_numbers(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(
        client,
        admin,
        "old.kamberov",
        "Велян Камберов",
        "OldPass123",
        gsm_number="+359000000000",
    )

    _create_user(client, admin, "plain.employee", "Plain Employee", "UserPass123")
    employee = _login(client, "plain.employee", "UserPass123")
    forbidden = client.post(
        "/users/import-employees",
        json={"text": "Натали\t\tФилипова\t+359882422442", "password": "Cars2026"},
        headers=_auth(employee),
    )
    assert forbidden.status_code == 403

    payload = {
        "password": "Cars2026",
        "reset_existing_passwords": True,
        "text": "\n".join(
            [
                "Име\tПрезиме\tФамилия\tТелефон\tНомер на чип",
                "Натали\t\tФилипова\t+359882422442\t430002003D23CE01",
                "Велян\t\tКамберов\t+359884144305\t7100020034163901",
                "Оборотна\t\tСервиз\t\t1F00020042C79901",
                "Натали\t\tФилипова\t+359882422442\tduplicate",
            ]
        ),
    }
    res = client.post("/users/import-employees", json=payload, headers=_auth(admin))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["created"] == 2
    assert data["updated"] == 1
    assert data["skipped"] == 1
    assert {item["display_name"] for item in data["items"]} == {
        "Натали Филипова",
        "Велян Камберов",
        "Оборотна Сервиз",
    }

    users = client.get("/users", headers=_auth(admin)).json()
    by_name = {user["display_name"]: user for user in users}
    assert by_name["Натали Филипова"]["username"] == "natali.filipova"
    assert by_name["Натали Филипова"]["gsm_number"] == "+359882422442"
    assert by_name["Велян Камберов"]["username"] == "velyan.kamberov"
    assert by_name["Велян Камберов"]["gsm_number"] == "+359884144305"
    assert by_name["Оборотна Сервиз"]["gsm_number"] is None
    _login(client, "natali.filipova", "Cars2026")
    _login(client, "velyan.kamberov", "Cars2026")


def test_admin_role_change_updates_stale_tokens_and_preserves_last_admin(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    admin_user_id = client.get("/auth/me", headers=_auth(admin)).json()["id"]
    created = _create_user(client, admin, "maria", "Maria Petrova", "MariaPass123")
    maria = _login(client, "maria", "MariaPass123")

    promote = client.post(
        f"/users/{created['id']}/role",
        json={"role": "fleet_admin", "reason": "Admin shift"},
        headers=_auth(admin),
    )
    assert promote.status_code == 200
    assert promote.json()["role"] == "fleet_admin"

    stale_token_create_car = client.post(
        "/cars",
        json={"plate_number": "CB9000AA", "model": "Tesla Model Y"},
        headers=_auth(maria),
    )
    assert stale_token_create_car.status_code == 201

    demote_original_admin = client.post(
        f"/users/{admin_user_id}/role",
        json={"role": "employee", "reason": "Handoff complete"},
        headers=_auth(maria),
    )
    assert demote_original_admin.status_code == 200
    assert demote_original_admin.json()["role"] == "employee"

    demoted_admin_stale_token = client.post(
        "/cars",
        json={"plate_number": "CB9001AA", "model": "Tesla Model 3"},
        headers=_auth(admin),
    )
    assert demoted_admin_stale_token.status_code == 403

    last_admin_demote = client.post(
        f"/users/{created['id']}/role",
        json={"role": "employee", "reason": "Should fail"},
        headers=_auth(maria),
    )
    assert last_admin_demote.status_code == 409

    audit = client.get(f"/users/{created['id']}/audit", headers=_auth(maria))
    assert audit.status_code == 200
    assert any(item["action"] == "role_changed" for item in audit.json())


def test_admin_cannot_reset_inactive_user_password(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    created = _create_user(client, admin, "georgi", "Georgi Ivanov", "GeorgiPass123")
    deactivated = client.post(f"/users/{created['id']}/deactivate", headers=_auth(admin))
    assert deactivated.status_code == 200

    reset = client.post(
        f"/users/{created['id']}/reset-password",
        json={"new_password": "GeorgiPass456"},
        headers=_auth(admin),
    )
    assert reset.status_code == 409


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

    employee_start = client.post(
        f"/reservations/{reservation_id}/start",
        json={"note": "Keys collected from reception"},
        headers=_auth(employee_one),
    )
    assert employee_start.status_code == 403

    start_trip = client.post(
        f"/reservations/{reservation_id}/start",
        json={"note": "Keys collected from reception"},
        headers=_auth(admin),
    )
    assert start_trip.status_code == 200
    assert start_trip.json()["status"] == "checked_out"

    after_start_employee_notifications = _list_notifications(client, employee_one, unread_only=True)
    assert len(after_start_employee_notifications) == 2
    assert after_start_employee_notifications[0]["kind"] == "trip_started"

    employee_return = client.post(
        f"/reservations/{reservation_id}/return",
        json={"note": "Vehicle returned clean and parked"},
        headers=_auth(employee_one),
    )
    assert employee_return.status_code == 403

    returned = client.post(
        f"/reservations/{reservation_id}/return",
        json={"note": "Vehicle returned clean and parked"},
        headers=_auth(admin),
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


def test_split_operational_roles_match_pool_process(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "approver", "Fleet Approver", "ApproverPass123", role="fleet_approver")
    _create_user(client, admin, "reception", "Reception Desk", "ReceptionPass123", role="fleet_reception")
    _create_user(
        client,
        admin,
        "driver",
        "Driver User",
        "DriverPass123",
        gsm_number="+359 88 555 0101",
    )
    approver = _login(client, "approver", "ApproverPass123")
    reception = _login(client, "reception", "ReceptionPass123")
    driver = _login(client, "driver", "DriverPass123")
    car_id = _create_car(client, admin, plate="CB1200AA")
    reservation_id = _create_reservation(client, car_id, driver)

    approver_list = client.get("/reservations", headers=_auth(approver))
    assert approver_list.status_code == 200
    assert approver_list.json()["total"] == 1
    assert approver_list.json()["items"][0]["requester_gsm_number"] == "+359 88 555 0101"

    reception_list = client.get("/reservations", headers=_auth(reception))
    assert reception_list.status_code == 200
    assert reception_list.json()["items"][0]["requester_gsm_number"] == "+359 88 555 0101"

    driver_list = client.get("/reservations", headers=_auth(driver))
    assert driver_list.status_code == 200
    assert driver_list.json()["items"][0]["requester_gsm_number"] == "+359 88 555 0101"

    approver_booking = client.post(
        "/reservations",
        json={
            "car_id": car_id,
            "start_time": "2099-04-19T09:00:00+00:00",
            "end_time": "2099-04-19T11:00:00+00:00",
            "purpose": "Approver should not book",
        },
        headers=_auth(approver),
    )
    assert approver_booking.status_code == 403

    forbidden_start = client.post(
        f"/reservations/{reservation_id}/start",
        json={"note": "Keys handed over"},
        headers=_auth(approver),
    )
    assert forbidden_start.status_code == 403

    forbidden_approve = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Reception cannot approve"},
        headers=_auth(reception),
    )
    assert forbidden_approve.status_code == 403

    approved = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Approved by dedicated approver"},
        headers=_auth(approver),
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"

    started = client.post(
        f"/reservations/{reservation_id}/start",
        json={"note": "Documents and keys handed over"},
        headers=_auth(reception),
    )
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "checked_out"

    returned = client.post(
        f"/reservations/{reservation_id}/return",
        json={"note": "Keys returned to reception"},
        headers=_auth(reception),
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "returned"

    users_for_approver = client.get("/users", headers=_auth(approver))
    users_for_reception = client.get("/users", headers=_auth(reception))
    assert users_for_approver.status_code == 403
    assert users_for_reception.status_code == 403


def test_admin_reservation_list_filters_by_search_and_date_window(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")
    car_a = _create_car(client, admin, plate="CB9100AA")
    car_b = _create_car(client, admin, plate="CB9101BB")
    first_id = _create_reservation(
        client,
        car_a,
        employee,
        start="2099-05-01T09:00:00+00:00",
        end="2099-05-01T11:00:00+00:00",
        purpose="Mission Alpha",
    )
    second_id = _create_reservation(
        client,
        car_b,
        employee,
        start="2099-06-01T09:00:00+00:00",
        end="2099-06-01T11:00:00+00:00",
        purpose="Routine logistics",
    )

    purpose_search = client.get("/reservations", params={"search": "mission"}, headers=_auth(admin))
    assert purpose_search.status_code == 200, purpose_search.text
    assert [item["id"] for item in purpose_search.json()["items"]] == [first_id]

    plate_search = client.get("/reservations", params={"search": "cb9101bb"}, headers=_auth(admin))
    assert plate_search.status_code == 200, plate_search.text
    assert [item["id"] for item in plate_search.json()["items"]] == [second_id]

    may_window = client.get(
        "/reservations",
        params={
            "start": "2099-05-01T00:00:00+00:00",
            "end": "2099-05-02T00:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert may_window.status_code == 200, may_window.text
    assert [item["id"] for item in may_window.json()["items"]] == [first_id]

    after_first_trip = client.get(
        "/reservations",
        params={
            "start": "2099-05-01T11:00:00+00:00",
            "end": "2099-05-01T12:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert after_first_trip.status_code == 200, after_first_trip.text
    assert after_first_trip.json()["items"] == []

    invalid_window = client.get(
        "/reservations",
        params={
            "start": "2099-05-03T00:00:00+00:00",
            "end": "2099-05-02T00:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert invalid_window.status_code == 400


def test_cancel_records_reason_in_audit_log(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")
    car_id = _create_car(client, admin, plate="CB9191AA")
    reservation_id = _create_reservation(
        client,
        car_id,
        employee,
        start="2099-05-04T09:00:00+00:00",
        end="2099-05-04T11:00:00+00:00",
    )

    cancelled = client.post(
        f"/reservations/{reservation_id}/cancel",
        json={"note": "Meeting moved online"},
        headers=_auth(employee),
    )

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    with db.get_conn() as conn:
        row = conn.execute(
            """
            SELECT reason
            FROM audit_log
            WHERE reservation_id=? AND action='cancelled'
            ORDER BY id DESC
            LIMIT 1
            """,
            (reservation_id,),
        ).fetchone()
    assert row["reason"] == "Meeting moved online"


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


def test_role_outbound_notifications_reach_approver_requester_and_reception(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    import config
    import notifications_service

    sent_to: list[str] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert host == "smtp.company.bg"

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args) -> None:
            return None

        def send_message(self, message) -> None:
            sent_to.append(message["To"])

    monkeypatch.setattr(
        notifications_service,
        "settings",
        replace(
            config.settings,
            smtp_host="smtp.company.bg",
            smtp_from_email="fleetflow@company.bg",
            smtp_to_email="",
            smtp_use_tls=False,
        ),
    )
    monkeypatch.setattr(notifications_service.smtplib, "SMTP", FakeSMTP)

    admin = _bootstrap_admin(client)
    _create_user(
        client,
        admin,
        "approver",
        "Approver User",
        "ApproverPass123",
        role="fleet_approver",
        email="approver@company.bg",
    )
    _create_user(
        client,
        admin,
        "reception",
        "Reception User",
        "ReceptionPass123",
        role="fleet_reception",
        email="reception@company.bg",
    )
    _create_user(
        client,
        admin,
        "employee",
        "Employee User",
        "EmployeePass123",
        email="employee@company.bg",
    )
    approver = _login(client, "approver", "ApproverPass123")
    reception = _login(client, "reception", "ReceptionPass123")
    employee = _login(client, "employee", "EmployeePass123")
    car_id = _create_car(client, admin, plate="CB8111AA")

    reservation_id = _create_reservation(client, car_id, employee)
    assert any(item["kind"] == "reservation_requested" for item in _list_notifications(client, approver))

    approve = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Approved for handoff"},
        headers=_auth(approver),
    )
    assert approve.status_code == 200

    assert any(item["kind"] == "reservation_decision" for item in _list_notifications(client, employee))
    assert any(item["kind"] == "reception_handoff" for item in _list_notifications(client, reception))
    assert {"approver@company.bg", "employee@company.bg", "reception@company.bg"} <= set(sent_to)


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


def test_reservation_conflicts_preview_reports_reservations_and_blackouts(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "IvanPass123")
    employee = _login(client, "ivan", "IvanPass123")

    car_id = _create_car(client, admin, plate="CB3500AA")
    _create_reservation(client, car_id, employee)

    blackout = client.post(
        f"/cars/{car_id}/blackouts",
        json={
            "start_time": "2099-04-18T13:00:00+00:00",
            "end_time": "2099-04-18T15:00:00+00:00",
            "kind": "service",
            "reason": "Service visit",
        },
        headers=_auth(admin),
    )
    assert blackout.status_code == 201, blackout.text

    conflicts = client.get(
        "/reservations/conflicts",
        params={
            "car_id": car_id,
            "start": "2099-04-18T10:00:00+00:00",
            "end": "2099-04-18T14:00:00+00:00",
        },
        headers=_auth(employee),
    )
    assert conflicts.status_code == 200, conflicts.text
    assert conflicts.json()["total"] == 2
    assert [item["type"] for item in conflicts.json()["items"]] == ["reservation", "blackout"]
    assert "employee_name" not in conflicts.json()["items"][0]
    assert conflicts.json()["items"][1]["reason"] is None

    admin_conflicts = client.get(
        "/reservations/conflicts",
        params={
            "car_id": car_id,
            "start": "2099-04-18T10:00:00+00:00",
            "end": "2099-04-18T14:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert admin_conflicts.status_code == 200, admin_conflicts.text
    assert admin_conflicts.json()["items"][0]["employee_name"] == "Ivan Petrov"
    assert admin_conflicts.json()["items"][1]["reason"] == "Service visit"

    clear = client.get(
        "/reservations/conflicts",
        params={
            "car_id": car_id,
            "start": "2099-04-18T16:00:00+00:00",
            "end": "2099-04-18T17:00:00+00:00",
        },
        headers=_auth(employee),
    )
    assert clear.status_code == 200, clear.text
    assert clear.json() == {"items": [], "total": 0}


def test_reservation_conflicts_require_auth_and_valid_window(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    car_id = _create_car(client, admin, plate="CB3600AA")

    unauth = client.get(
        "/reservations/conflicts",
        params={
            "car_id": car_id,
            "start": "2099-04-18T10:00:00+00:00",
            "end": "2099-04-18T14:00:00+00:00",
        },
    )
    assert unauth.status_code == 401

    invalid = client.get(
        "/reservations/conflicts",
        params={
            "car_id": car_id,
            "start": "2099-04-18T14:00:00+00:00",
            "end": "2099-04-18T10:00:00+00:00",
        },
        headers=_auth(admin),
    )
    assert invalid.status_code == 400


def test_reservation_suggest_returns_first_available_active_car(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "suggest", "Suggest User", "SuggestPass123")
    employee = _login(client, "suggest", "SuggestPass123")
    car_id = _create_car(client, admin, plate="CB3700AA")

    res = client.get("/reservations/suggest", headers=_auth(employee))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["car_id"] == car_id
    assert data["plate_number"] == "CB3700AA"
    assert data["duration_minutes"] == 120
    assert datetime.fromisoformat(data["end_time"]) > datetime.fromisoformat(data["start_time"])


def test_quick_book_creates_pending_reservation(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "quick", "Quick User", "QuickPass123")
    employee = _login(client, "quick", "QuickPass123")
    car_id = _create_car(client, admin, plate="CB3701AA")

    res = client.post("/reservations/quick-book", headers=_auth(employee))
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["car_id"] == car_id
    assert data["status"] == "pending"
    assert data["purpose"] == "Бърза заявка от FleetFlow"
    assert data["quick_suggestion"]["plate_number"] == "CB3701AA"
    assert data["quick_suggestion"]["reason_code"] == "available_balanced"

    with db.get_conn() as conn:
        assignment = conn.execute(
            "SELECT * FROM car_assignments WHERE reservation_id=?",
            (int(data["id"]),),
        ).fetchone()
    assert assignment["assignment_mode"] == "quick_book"
    assert assignment["reason_code"] == "available_balanced"
    assert float(assignment["score"]) >= 100


def test_suggest_best_car_prefers_lower_recent_utilization(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "balanced", "Balanced User", "BalancedPass123")
    employee = _login(client, "balanced", "BalancedPass123")
    overused_car = _create_car(client, admin, plate="CB3710AA")
    balanced_car = _create_car(client, admin, plate="CB3711AA")

    _create_reservation(
        client,
        overused_car,
        employee,
        "2099-04-18T08:00:00+00:00",
        "2099-04-18T18:00:00+00:00",
        "Long planned usage",
    )

    res = client.get(
        "/reservations/suggest-best-car",
        params={
            "start": "2099-05-18T10:00:00+00:00",
            "end": "2099-05-18T12:00:00+00:00",
        },
        headers=_auth(employee),
    )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["car_id"] == balanced_car
    assert data["reason_code"] == "low_recent_utilization"
    assert data["score"] > 100


def test_admin_intelligence_pulse_is_admin_only(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "pulse", "Pulse User", "PulsePass123")
    employee = _login(client, "pulse", "PulsePass123")
    car_id = _create_car(client, admin, plate="CB3712AA")
    _create_reservation(client, car_id, employee)

    forbidden = client.get("/admin/intelligence/pulse", headers=_auth(employee))
    assert forbidden.status_code == 403

    res = client.get("/admin/intelligence/pulse", headers=_auth(admin))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["active_cars"] == 1
    assert data["pending_requests"] == 1
    assert data["available_now"] == 1
    assert data["insights"][0]["kind"] == "pending_bottleneck"


def test_public_overview_exposes_real_counts_without_auth(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "public", "Public User", "PublicPass123")
    employee = _login(client, "public", "PublicPass123")
    car_id = _create_car(client, admin, plate="CB3713AA")
    reservation_id = _create_reservation(client, car_id, employee)

    pending = client.get("/public/overview")
    assert pending.status_code == 200, pending.text
    assert pending.json() == {
        "active_cars": 1,
        "pending_requests": 1,
        "active_trips": 0,
        "available_cars": 1,
    }

    approve = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Operational approval"},
        headers=_auth(admin),
    )
    assert approve.status_code == 200, approve.text
    start = client.post(
        f"/reservations/{reservation_id}/start",
        json={"note": "Handed over"},
        headers=_auth(admin),
    )
    assert start.status_code == 200, start.text

    active = client.get("/public/overview")
    assert active.status_code == 200, active.text
    assert active.json() == {
        "active_cars": 1,
        "pending_requests": 0,
        "active_trips": 1,
        "available_cars": 0,
    }


def test_public_calendar_exposes_anonymized_operational_slots_without_auth(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "calendar", "Calendar User", "CalendarPass123")
    employee = _login(client, "calendar", "CalendarPass123")
    car_id = _create_car(client, admin, plate="CB3714AA")
    reservation_id = _create_reservation(
        client,
        car_id,
        employee,
        "2099-05-12T09:00:00+00:00",
        "2099-05-12T11:00:00+00:00",
        "Board visit",
    )
    approve = client.post(
        f"/reservations/{reservation_id}/approve",
        json={"reason": "Operational approval"},
        headers=_auth(admin),
    )
    assert approve.status_code == 200, approve.text
    start = client.post(
        f"/reservations/{reservation_id}/start",
        json={"note": "Handed over"},
        headers=_auth(admin),
    )
    assert start.status_code == 200, start.text

    res = client.get(
        "/public/calendar",
        params={
            "start": "2099-05-01T00:00:00+00:00",
            "end": "2099-06-01T00:00:00+00:00",
        },
    )
    assert res.status_code == 200, res.text
    item = res.json()["items"][0]
    assert item == {
        "start_time": "2099-05-12T09:00:00+00:00",
        "end_time": "2099-05-12T11:00:00+00:00",
        "status": "checked_out",
        "plate_number": "CB3714AA",
        "model": "Skoda Octavia",
    }
    assert "employee_name" not in item
    assert "purpose" not in item
    assert "requester_gsm_number" not in item
    assert "id" not in item


def test_reservation_suggest_skips_conflicting_car(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "busy", "Busy User", "BusyPass123")
    employee = _login(client, "busy", "BusyPass123")
    busy_car = _create_car(client, admin, plate="CB3702AA")
    free_car = _create_car(client, admin, plate="CB3703AA")
    start = datetime.now(timezone.utc) + timedelta(minutes=20)
    end = start + timedelta(days=8)
    _create_reservation(client, busy_car, employee, start.isoformat(), end.isoformat(), "Long reservation")

    res = client.get("/reservations/suggest", headers=_auth(employee))
    assert res.status_code == 200, res.text
    assert res.json()["car_id"] == free_car


def test_reservation_preferences_return_common_car_hour_and_duration(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "prefs", "Prefs User", "PrefsPass123")
    employee = _login(client, "prefs", "PrefsPass123")
    car_id = _create_car(client, admin, plate="CB3704AA")
    _create_reservation(
        client,
        car_id,
        employee,
        "2099-04-18T09:00:00+00:00",
        "2099-04-18T11:00:00+00:00",
        "Morning trip",
    )
    _create_reservation(
        client,
        car_id,
        employee,
        "2099-04-19T09:00:00+00:00",
        "2099-04-19T11:00:00+00:00",
        "Morning trip",
    )

    res = client.get("/reservations/preferences", headers=_auth(employee))
    assert res.status_code == 200, res.text
    assert res.json() == {
        "available": True,
        "car_id": car_id,
        "plate_number": "CB3704AA",
        "model": "Skoda Octavia",
        "start_hour": 9,
        "duration_minutes": 120,
        "sample_size": 2,
    }


def test_reservation_preferences_empty_for_new_employee(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "newprefs", "New Prefs", "PrefsPass123")
    employee = _login(client, "newprefs", "PrefsPass123")

    res = client.get("/reservations/preferences", headers=_auth(employee))
    assert res.status_code == 200, res.text
    assert res.json()["available"] is False
    assert res.json()["sample_size"] == 0


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
    assert client.get("/health/ready").json() == {"status": "ready", "database": "sqlite"}
    res = client.get("/")
    admin_res = client.get("/admin")
    assert res.status_code == 200
    assert admin_res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "text/html" in admin_res.headers["content-type"]
    assert "/static/i18n.js?v=" in res.text
    assert "/static/i18n.js?v=" in admin_res.text
    assert "/static/app.js?v=" in res.text
    assert "/static/app.js?v=" in admin_res.text
    assert "/static/styles.css?v=" in res.text
    assert "/static/styles.css?v=" in admin_res.text
    assert res.headers["cache-control"] == "no-cache, must-revalidate"
    assert admin_res.headers["cache-control"] == "no-cache, must-revalidate"
    assert client.get("/static/i18n.js").headers["cache-control"] == "no-cache, must-revalidate"
    assert client.get("/static/app.js").headers["cache-control"] == "no-cache, must-revalidate"
    assert client.get("/static/styles.css").headers["cache-control"] == "no-cache, must-revalidate"
    assert 'id="notificationBadge"' in res.text
    assert 'id="notificationBadge"' in admin_res.text
    assert 'id="bootstrapToken"' in res.text
    assert 'id="bootstrapToken"' in admin_res.text
    assert 'aria-label="Основна навигация"' in res.text
    assert 'aria-label="Административна навигация"' in admin_res.text
    assert 'aria-label="Бърза мобилна навигация"' in res.text
    assert 'aria-label="Бърза административна навигация"' in admin_res.text
    assert 'role="group" aria-label="Филтри за резервации"' in res.text
    assert 'role="group" aria-label="Филтри за резервации"' in admin_res.text
    assert 'id="reservationsTableBody" aria-live="polite"' in res.text
    assert 'id="reservationsTableBody" aria-live="polite"' in admin_res.text
    assert 'id="userCreatePanel"' not in res.text
    assert 'id="usersGrid"' not in res.text
    assert 'id="bulkActionBar"' not in res.text
    assert 'id="bulkActionBar"' in admin_res.text
    assert 'id="bulkSelectAll"' in admin_res.text
    assert 'id="productionReadinessPanel"' in admin_res.text
    assert 'class="glass-card hidden" id="userCreatePanel"' in admin_res.text
    assert 'class="glass-card hidden" id="usersDeck"' in admin_res.text


def test_ops_readiness_is_admin_only_and_does_not_leak_secrets(client: TestClient) -> None:
    assert client.get("/ops/readiness").status_code == 401

    admin = _bootstrap_admin(client)
    _create_user(client, admin, "ivan", "Ivan Petrov", "UserPass123")
    employee = _login(client, "ivan", "UserPass123")

    assert client.get("/ops/readiness", headers=_auth(employee)).status_code == 403

    res = client.get("/ops/readiness", headers=_auth(admin))
    assert res.status_code == 200
    data = res.json()
    ids = {item["id"] for item in data["items"]}

    assert data["ready"] is False
    assert data["app_env"] == "dev"
    assert data["database_backend"] == "sqlite"
    assert {"app_env", "database_connection", "active_admin", "admin_redundancy", "netfleet", "notifications"} <= ids
    redundancy = next(item for item in data["items"] if item["id"] == "admin_redundancy")
    assert redundancy["status"] == "warn"
    assert "само един активен администратор" in redundancy["detail"]
    assert not any("test-secret-key" in str(item) for item in data["items"])
    assert not any("DATABASE_URL" in item["detail"] and "://" in item["detail"] for item in data["items"])

    _create_user(client, admin, "backupadmin", "Backup Admin", "BackupAdmin123", role="fleet_admin")
    redundant = client.get("/ops/readiness", headers=_auth(admin)).json()
    redundancy_after = next(item for item in redundant["items"] if item["id"] == "admin_redundancy")
    assert redundancy_after["status"] == "pass"
    assert "двама активни администратори" in redundancy_after["detail"]


def test_admin_responsive_css_prevents_module_overlap() -> None:
    css = Path("static/styles.css").read_text()

    assert ".glass-card__header--split {\n  align-items: center;\n  flex-wrap: wrap;" in css
    assert ".hero__secondary {\n    grid-template-columns: 1fr;" in css
    assert "@media (max-width: 560px)" in css
    assert ".mission-filter__actions .btn,\n  .button-row .btn," in css
    assert ".bulk-action-bar__actions .btn {\n    width: 100%;" in css
    assert ".bulk-action-bar" in css
    assert ".calendar-grid--mobile" in css
    assert ".skeleton-card" in css


def test_request_id_and_security_headers(client: TestClient) -> None:
    request_id = "fleetflow-test-request"
    res = client.get("/health", headers={"X-Request-ID": request_id})
    generated = client.get("/health")

    assert res.headers["x-request-id"] == request_id
    assert len(generated.headers["x-request-id"]) == 32
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert res.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_access_log_format_is_json_in_production_and_text_in_dev() -> None:
    from logging_config import (
        ACCESS_LOGGER_NAME,
        build_access_log,
        configure_access_logger,
        format_access_log,
        use_json_logs,
    )

    event = build_access_log(
        request_id="rid-123",
        method="GET",
        path="/health",
        route="/health",
        status_code=200,
        latency_ms=12.34,
        app_env="prod",
        client_host="127.0.0.1",
    )

    encoded = format_access_log(event, json_logs=True)
    decoded = json.loads(encoded)

    assert use_json_logs("prod", "auto") is True
    assert use_json_logs("dev", "auto") is False
    assert decoded["event"] == "http_request"
    assert decoded["request_id"] == "rid-123"
    assert decoded["route"] == "/health"
    assert decoded["status_code"] == 200
    assert "SECRET_KEY" not in encoded
    assert "POSTGRES_PASSWORD" not in encoded
    assert format_access_log(event, json_logs=False).startswith("http_request request_id=rid-123")

    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    configure_access_logger()
    after_first_config = len(logger.handlers)
    configure_access_logger()
    assert logger.level == logging.INFO
    assert logger.propagate is False
    assert len(logger.handlers) == after_first_config


def test_prod_request_access_log_is_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("SECRET_KEY", "k" * 40)
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("LOG_FORMAT", "json")
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

    messages: list[str] = []

    class ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(record.getMessage())

    access_logger = logging.getLogger("fleetflow.access")
    handler = ListHandler()
    access_logger.addHandler(handler)
    with TestClient(app_module.app) as c:
        try:
            res = c.get("/health", headers={"X-Request-ID": "prod-log-test"})
        finally:
            access_logger.removeHandler(handler)

    assert res.status_code == 200
    payload = json.loads(messages[-1])
    assert payload["event"] == "http_request"
    assert payload["request_id"] == "prod-log-test"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["route"] == "/health"
    assert payload["status_code"] == 200
    assert payload["app_env"] == "prod"
    assert isinstance(payload["latency_ms"], float)
    assert "kkkk" not in messages[-1]


def test_dev_cors_preflight_allows_local_clients(client: TestClient) -> None:
    res = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in res.headers


# ---------------------------------------------------------------------------
# 2.10 Blackout edit (PUT /cars/{car_id}/blackouts/{blackout_id})
# ---------------------------------------------------------------------------

def test_blackout_update_changes_window(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    car_id = _create_car(client, admin, plate="CB9010AA")

    created = client.post(
        f"/cars/{car_id}/blackouts",
        json={
            "start_time": "2099-05-01T08:00:00+00:00",
            "end_time": "2099-05-01T12:00:00+00:00",
            "kind": "maintenance",
            "reason": "Oil change",
        },
        headers=_auth(admin),
    )
    assert created.status_code == 201
    boid = created.json()["id"]

    updated = client.put(
        f"/cars/{car_id}/blackouts/{boid}",
        json={
            "start_time": "2099-05-02T08:00:00+00:00",
            "end_time": "2099-05-02T18:00:00+00:00",
            "kind": "service",
            "reason": "Full service",
        },
        headers=_auth(admin),
    )
    assert updated.status_code == 200
    data = updated.json()
    assert data["kind"] == "service"
    assert data["reason"] == "Full service"
    assert "2099-05-02" in data["start_time"]


def test_blackout_update_overlap_rejected(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    car_id = _create_car(client, admin, plate="CB9011AA")

    b1 = client.post(
        f"/cars/{car_id}/blackouts",
        json={"start_time": "2099-06-01T08:00:00+00:00", "end_time": "2099-06-01T12:00:00+00:00", "kind": "maintenance"},
        headers=_auth(admin),
    )
    b2 = client.post(
        f"/cars/{car_id}/blackouts",
        json={"start_time": "2099-06-02T08:00:00+00:00", "end_time": "2099-06-02T12:00:00+00:00", "kind": "service"},
        headers=_auth(admin),
    )
    assert b1.status_code == 201
    assert b2.status_code == 201

    conflict = client.put(
        f"/cars/{car_id}/blackouts/{b2.json()['id']}",
        json={"start_time": "2099-06-01T10:00:00+00:00", "end_time": "2099-06-01T14:00:00+00:00", "kind": "service"},
        headers=_auth(admin),
    )
    assert conflict.status_code == 409


def test_blackout_update_employee_forbidden(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "emp1", "Emp One", "EmpPass123")
    emp = _login(client, "emp1", "EmpPass123")
    car_id = _create_car(client, admin, plate="CB9012AA")

    b = client.post(
        f"/cars/{car_id}/blackouts",
        json={"start_time": "2099-07-01T08:00:00+00:00", "end_time": "2099-07-01T12:00:00+00:00", "kind": "inspection"},
        headers=_auth(admin),
    )
    assert b.status_code == 201

    res = client.put(
        f"/cars/{car_id}/blackouts/{b.json()['id']}",
        json={"start_time": "2099-07-01T08:00:00+00:00", "end_time": "2099-07-01T12:00:00+00:00", "kind": "inspection"},
        headers=_auth(emp),
    )
    assert res.status_code == 403


def test_blackout_update_invalid_window(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    car_id = _create_car(client, admin, plate="CB9013AA")

    b = client.post(
        f"/cars/{car_id}/blackouts",
        json={"start_time": "2099-08-01T08:00:00+00:00", "end_time": "2099-08-01T12:00:00+00:00", "kind": "blocked"},
        headers=_auth(admin),
    )
    assert b.status_code == 201

    res = client.put(
        f"/cars/{car_id}/blackouts/{b.json()['id']}",
        json={"start_time": "2099-08-01T12:00:00+00:00", "end_time": "2099-08-01T08:00:00+00:00", "kind": "blocked"},
        headers=_auth(admin),
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# 2.11 Car notes (PUT /cars/{car_id}/notes)
# ---------------------------------------------------------------------------

def test_car_notes_save_and_retrieve(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    car_id = _create_car(client, admin, plate="CB9020AA")

    res = client.put(
        f"/cars/{car_id}/notes",
        json={"notes": "Предстои смяна на гуми преди 15 май."},
        headers=_auth(admin),
    )
    assert res.status_code == 200
    assert res.json()["notes"] == "Предстои смяна на гуми преди 15 май."

    # Notes survive a list_cars call
    cars = client.get("/cars?active_only=false", headers=_auth(admin)).json()["items"]
    found = next((c for c in cars if c["id"] == car_id), None)
    assert found is not None
    assert found["notes"] == "Предстои смяна на гуми преди 15 май."


def test_car_notes_clear(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    car_id = _create_car(client, admin, plate="CB9021AA")

    client.put(f"/cars/{car_id}/notes", json={"notes": "old note"}, headers=_auth(admin))
    res = client.put(f"/cars/{car_id}/notes", json={"notes": None}, headers=_auth(admin))
    assert res.status_code == 200
    assert res.json()["notes"] is None


def test_car_notes_employee_forbidden(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "emp2", "Emp Two", "EmpPass123")
    emp = _login(client, "emp2", "EmpPass123")
    car_id = _create_car(client, admin, plate="CB9022AA")

    res = client.put(f"/cars/{car_id}/notes", json={"notes": "hack"}, headers=_auth(emp))
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 2.13 NetFleet telemetry (GET /cars/telemetry/latest)
# ---------------------------------------------------------------------------

def test_car_telemetry_returns_unconfigured_without_secret(client: TestClient) -> None:
    admin = _bootstrap_admin(client)

    res = client.get("/cars/telemetry/latest", headers=_auth(admin))
    assert res.status_code == 200
    assert res.json() == {"configured": False, "items": []}


def test_netfleet_config_can_be_saved_once_or_changed_by_admin(client: TestClient) -> None:
    admin = _bootstrap_admin(client)

    status_res = client.get("/cars/telemetry/config", headers=_auth(admin))
    assert status_res.status_code == 200
    assert status_res.json() == {
        "configured": False,
        "source": "none",
        "updated_at": None,
        "updated_by_id": None,
    }

    create_res = client.put(
        "/cars/telemetry/config",
        json={"api_key": "stored-test-key-123456"},
        headers=_auth(admin),
    )
    assert create_res.status_code == 200
    data = create_res.json()
    assert data["configured"] is True
    assert data["source"] == "database"
    assert data["updated_by_id"] is not None
    assert "api_key" not in data

    change_res = client.put(
        "/cars/telemetry/config",
        json={"api_key": "changed-test-key-654321"},
        headers=_auth(admin),
    )
    assert change_res.status_code == 200
    assert change_res.json()["source"] == "database"


def test_netfleet_config_is_admin_only(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "nogpsadmin", "No GPS Admin", "EmpPass123")
    emp = _login(client, "nogpsadmin", "EmpPass123")

    read_res = client.get("/cars/telemetry/config", headers=_auth(emp))
    write_res = client.put(
        "/cars/telemetry/config",
        json={"api_key": "employee-test-key-123456"},
        headers=_auth(emp),
    )

    assert read_res.status_code == 403
    assert write_res.status_code == 403


def test_car_telemetry_uses_admin_saved_netfleet_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from routers import cars

    admin = _bootstrap_admin(client)
    captured = {}

    client.put(
        "/cars/telemetry/config",
        json={"api_key": "stored-ui-key-123456"},
        headers=_auth(admin),
    )

    def fake_fetch(api_key=None):
        captured["api_key"] = api_key
        return SimpleNamespace(configured=True, items=[])

    monkeypatch.setattr(cars, "fetch_latest_gps_events", fake_fetch)

    res = client.get("/cars/telemetry/latest", headers=_auth(admin))
    assert res.status_code == 200
    assert res.json() == {"configured": True, "items": []}
    assert captured["api_key"] == "stored-ui-key-123456"


def test_car_telemetry_employee_forbidden(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "empgps", "Emp GPS", "EmpPass123")
    emp = _login(client, "empgps", "EmpPass123")

    res = client.get("/cars/telemetry/latest", headers=_auth(emp))
    assert res.status_code == 403


def test_car_telemetry_returns_normalized_netfleet_payload(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from routers import cars

    admin = _bootstrap_admin(client)
    monkeypatch.setattr(
        cars,
        "fetch_latest_gps_events",
        lambda api_key=None: SimpleNamespace(
            configured=True,
            items=[
                {
                    "plate_number": "CB9023AA",
                    "latitude": 42.6977,
                    "longitude": 23.3219,
                    "speed": 12.5,
                    "utc_time": "2024-04-29 14:48:05",
                }
            ],
        ),
    )

    res = client.get("/cars/telemetry/latest", headers=_auth(admin))
    assert res.status_code == 200
    assert res.json()["configured"] is True
    assert res.json()["items"][0]["plate_number"] == "CB9023AA"
    assert res.json()["items"][0]["latitude"] == 42.6977


def test_employee_can_read_pickup_telemetry_for_approved_trip(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from routers import cars

    admin = _bootstrap_admin(client)
    _create_user(client, admin, "pick", "Pickup User", "PickupPass123")
    employee = _login(client, "pick", "PickupPass123")
    car_id = _create_car(client, admin, plate="CB9024AA")
    reservation_id = _create_reservation(client, car_id, employee)
    approve = client.post(f"/reservations/{reservation_id}/approve", json={"reason": "ok"}, headers=_auth(admin))
    assert approve.status_code == 200
    monkeypatch.setattr(
        cars,
        "fetch_latest_gps_events",
        lambda api_key=None: SimpleNamespace(
            configured=True,
            items=[{"plate_number": "CB9024AA", "latitude": 42.7, "longitude": 23.3, "speed": 0}],
        ),
    )

    res = client.get(f"/cars/{car_id}/telemetry/latest", headers=_auth(employee))
    assert res.status_code == 200
    assert res.json()["configured"] is True
    assert res.json()["item"]["plate_number"] == "CB9024AA"
    start = client.post(f"/reservations/{reservation_id}/start", json={"note": "active pickup"}, headers=_auth(admin))
    assert start.status_code == 200
    active_res = client.get(f"/cars/{car_id}/telemetry/latest", headers=_auth(employee))
    assert active_res.status_code == 200
    assert active_res.json()["item"]["plate_number"] == "CB9024AA"


def test_reception_can_read_pickup_telemetry_for_approved_handoff(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from routers import cars

    admin = _bootstrap_admin(client)
    _create_user(client, admin, "handoff-owner", "Handoff Owner", "PickupPass123")
    _create_user(client, admin, "gps-reception", "GPS Reception", "ReceptionPass123", role="fleet_reception")
    employee = _login(client, "handoff-owner", "PickupPass123")
    reception = _login(client, "gps-reception", "ReceptionPass123")
    car_id = _create_car(client, admin, plate="CB9026AA")
    reservation_id = _create_reservation(client, car_id, employee)
    approve = client.post(f"/reservations/{reservation_id}/approve", json={"reason": "ok"}, headers=_auth(admin))
    assert approve.status_code == 200
    monkeypatch.setattr(
        cars,
        "fetch_latest_gps_events",
        lambda api_key=None: SimpleNamespace(
            configured=True,
            items=[{"plate_number": "CB9026AA", "latitude": 42.71, "longitude": 23.31, "speed": 0}],
        ),
    )

    res = client.get(f"/cars/{car_id}/telemetry/latest", headers=_auth(reception))
    assert res.status_code == 200
    assert res.json()["configured"] is True
    assert res.json()["item"]["plate_number"] == "CB9026AA"


def test_employee_cannot_read_pickup_telemetry_without_approved_trip(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "nopick", "No Pickup", "PickupPass123")
    employee = _login(client, "nopick", "PickupPass123")
    car_id = _create_car(client, admin, plate="CB9025AA")

    res = client.get(f"/cars/{car_id}/telemetry/latest", headers=_auth(employee))
    assert res.status_code == 403


def test_reception_cannot_read_pickup_telemetry_without_handoff(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "nogps-reception", "No GPS Reception", "ReceptionPass123", role="fleet_reception")
    reception = _login(client, "nogps-reception", "ReceptionPass123")
    car_id = _create_car(client, admin, plate="CB9027AA")

    res = client.get(f"/cars/{car_id}/telemetry/latest", headers=_auth(reception))
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 2.12 Test notification (POST /notifications/test)
# ---------------------------------------------------------------------------

def test_notification_test_creates_inapp(client: TestClient) -> None:
    admin = _bootstrap_admin(client)

    res = client.post("/notifications/test", headers=_auth(admin))
    assert res.status_code == 200
    data = res.json()
    assert "channels" in data
    assert "notification_id" in data
    in_app = next((ch for ch in data["channels"] if ch["name"] == "in_app"), None)
    assert in_app is not None
    assert in_app["status"] == "sent"

    # The notification should appear in admin inbox
    inbox = client.get("/notifications", headers=_auth(admin)).json()
    assert any(n["kind"] == "test" for n in inbox)


def test_notification_test_sends_smtp_to_user_email(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    import config
    import notifications_service

    sent_messages = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            assert host == "smtp.company.bg"
            assert port == 587
            assert timeout == 5

        def __enter__(self) -> "FakeSMTP":
            return self

        def __exit__(self, *args) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            raise AssertionError("Login should not run without SMTP credentials")

        def send_message(self, message) -> None:
            sent_messages.append(message)

    monkeypatch.setattr(
        notifications_service,
        "settings",
        replace(
            config.settings,
            smtp_host="smtp.company.bg",
            smtp_from_email="fleetflow@company.bg",
            smtp_to_email="",
            smtp_use_tls=False,
        ),
    )
    monkeypatch.setattr(notifications_service.smtplib, "SMTP", FakeSMTP)

    admin = _bootstrap_admin(client)
    admin_id = client.get("/auth/me", headers=_auth(admin)).json()["id"]
    update_contact = client.put(
        f"/users/{admin_id}/contact",
        json={"email": "admin.user@company.bg", "gsm_number": "+359888000111", "reason": "SMTP routing proof"},
        headers=_auth(admin),
    )
    assert update_contact.status_code == 200

    res = client.post("/notifications/test", headers=_auth(admin))
    assert res.status_code == 200
    channels = {channel["name"]: channel["status"] for channel in res.json()["channels"]}

    assert channels["email"] == "sent"
    assert sent_messages
    assert sent_messages[0]["To"] == "admin.user@company.bg"
    assert sent_messages[0]["From"] == "fleetflow@company.bg"
    assert "[FleetFlow]" in sent_messages[0]["Subject"]


def test_notification_test_sends_teams_webhook(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import replace

    import config
    import notifications_service

    payloads = []

    def fake_post_json(url: str, payload: dict) -> None:
        payloads.append((url, payload))

    monkeypatch.setattr(
        notifications_service,
        "settings",
        replace(config.settings, teams_webhook_url="https://teams.company.bg/webhook"),
    )
    monkeypatch.setattr(notifications_service, "_post_json", fake_post_json)

    admin = _bootstrap_admin(client)
    res = client.post("/notifications/test", headers=_auth(admin))
    assert res.status_code == 200
    channels = {channel["name"]: channel["status"] for channel in res.json()["channels"]}

    assert channels["teams"] == "sent"
    assert payloads
    assert payloads[0][0] == "https://teams.company.bg/webhook"
    assert payloads[0][1]["@type"] == "MessageCard"
    assert payloads[0][1]["title"] == "FleetFlow — тест известие"


def test_notification_test_employee_forbidden(client: TestClient) -> None:
    admin = _bootstrap_admin(client)
    _create_user(client, admin, "emp3", "Emp Three", "EmpPass123")
    emp = _login(client, "emp3", "EmpPass123")

    res = client.post("/notifications/test", headers=_auth(emp))
    assert res.status_code == 403


def test_notification_test_unauthenticated(client: TestClient) -> None:
    res = client.post("/notifications/test")
    assert res.status_code == 401
