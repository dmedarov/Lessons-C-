"""Phase 2.4 — bulk approve/reject for pending reservations."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.test_app import (  # reuse fixtures and helpers
    _auth,
    _bootstrap_admin,
    _create_car,
    _create_reservation,
    _create_user,
    _login,
    client,  # noqa: F401 — pytest picks up the fixture via import
)


def _seed(client: TestClient) -> tuple[str, str, list[int]]:
    admin_token = _bootstrap_admin(client)
    _create_user(client, admin_token, "ivan", "Ivan Petrov", "UserPass123")
    employee_token = _login(client, "ivan", "UserPass123")
    car_id = _create_car(client, admin_token)
    # Three non-overlapping reservations — all pending.
    ids: list[int] = []
    for hour in (9, 12, 15):
        res = client.post(
            "/reservations",
            json={
                "car_id": car_id,
                "start_time": f"2099-05-{hour:02d}T{hour:02d}:00:00+00:00",
                "end_time": f"2099-05-{hour:02d}T{hour + 1:02d}:00:00+00:00",
                "purpose": "work",
            },
            headers=_auth(employee_token),
        )
        assert res.status_code == 201, res.text
        ids.append(res.json()["id"])
    return admin_token, employee_token, ids


def test_bulk_approve_requires_admin(client: TestClient) -> None:  # noqa: F811
    _, employee_token, ids = _seed(client)
    res = client.post(
        "/reservations/bulk-approve",
        json={"ids": ids},
        headers=_auth(employee_token),
    )
    assert res.status_code == 403


def test_bulk_approve_all_succeed(client: TestClient) -> None:  # noqa: F811
    admin_token, _, ids = _seed(client)
    res = client.post(
        "/reservations/bulk-approve",
        json={"ids": ids, "reason": "batch"},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["succeeded"] == 3
    assert body["failed"] == 0
    assert {r["id"] for r in body["results"]} == set(ids)
    assert all(r["status"] == "approved" for r in body["results"])


def test_bulk_reject_mixed_with_already_decided(client: TestClient) -> None:  # noqa: F811
    admin_token, _, ids = _seed(client)
    # Pre-approve the first one via the single-id route.
    client.post(
        f"/reservations/{ids[0]}/approve",
        json={"reason": "ok"},
        headers=_auth(admin_token),
    )
    res = client.post(
        "/reservations/bulk-reject",
        json={"ids": ids, "reason": "batch"},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    # Two pending → rejected; one already_approved → skipped.
    assert body["succeeded"] == 2
    assert body["failed"] == 1
    by_id = {r["id"]: r for r in body["results"]}
    assert by_id[ids[0]]["status"] == "skipped"
    assert by_id[ids[0]]["error"] == "already_approved"
    assert by_id[ids[1]]["status"] == "rejected"
    assert by_id[ids[2]]["status"] == "rejected"


def test_bulk_approve_handles_missing_ids(client: TestClient) -> None:  # noqa: F811
    admin_token, _, ids = _seed(client)
    res = client.post(
        "/reservations/bulk-approve",
        json={"ids": [ids[0], 999_999]},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["succeeded"] == 1
    assert body["failed"] == 1
    by_id = {r["id"]: r for r in body["results"]}
    assert by_id[ids[0]]["status"] == "approved"
    assert by_id[999_999]["status"] == "skipped"
    assert by_id[999_999]["error"] == "not_found"


def test_bulk_approve_deduplicates_ids(client: TestClient) -> None:  # noqa: F811
    admin_token, _, ids = _seed(client)
    res = client.post(
        "/reservations/bulk-approve",
        json={"ids": [ids[0], ids[0], ids[0]]},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    body = res.json()
    # The same id sent three times collapses to one result row.
    assert len(body["results"]) == 1
    assert body["succeeded"] == 1


def test_bulk_empty_ids_rejected_by_validator(client: TestClient) -> None:  # noqa: F811
    admin_token, _, _ = _seed(client)
    res = client.post(
        "/reservations/bulk-approve",
        json={"ids": []},
        headers=_auth(admin_token),
    )
    assert res.status_code == 422
