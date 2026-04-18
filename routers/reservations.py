from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db import PostgresConnectionAdapter, SQLiteConnectionAdapter, get_conn, transaction
from notifications_service import create_notification, create_notifications, dispatch_outbound_notifications
from schemas import DecisionPayload, LifecycleNotePayload, ReservationCreate, ReservationStatus
from security import AuthContext, get_auth_context, require_admin

DbConn = Union[SQLiteConnectionAdapter, PostgresConnectionAdapter]

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _log(conn: DbConn, reservation_id: int, actor_id: int, action: str, reason: Optional[str]) -> None:
    conn.execute(
        "INSERT INTO audit_log(reservation_id, actor_id, action, reason, at) VALUES(?, ?, ?, ?, ?)",
        (reservation_id, actor_id, action, reason, _utcnow_iso()),
    )


def _active_admin_ids(conn: DbConn) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM users WHERE role='fleet_admin' AND active=1 ORDER BY id"
    ).fetchall()
    return [int(row["id"]) for row in rows]


def _presentation_status(row: Any) -> str:
    status_value = str(row["status"])
    if status_value != "approved":
        return status_value
    if row["returned_at"]:
        return "returned"
    if row["checked_out_at"]:
        return "checked_out"
    return "approved"


def _serialize_reservation(row: Any) -> dict[str, Any]:
    payload = dict(row)
    payload["status"] = _presentation_status(row)
    return payload


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    if payload.start_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="start_time must be in the future")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    if payload.end_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="end_time must be in the future")

    start_iso = _to_utc_iso(payload.start_time)
    end_iso = _to_utc_iso(payload.end_time)
    now = _utcnow_iso()
    notification_ids: list[int] = []

    with get_conn() as conn, transaction(conn):
        car = conn.execute("SELECT id, active, plate_number, model FROM cars WHERE id=?", (payload.car_id,)).fetchone()
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        if not car["active"]:
            raise HTTPException(status_code=409, detail="Car is inactive")

        overlapping = conn.execute(
            """
            SELECT id FROM reservations
            WHERE car_id = ?
              AND (
                    status = 'pending'
                 OR (status = 'approved' AND returned_at IS NULL)
              )
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (payload.car_id, end_iso, start_iso),
        ).fetchone()
        if overlapping:
            raise HTTPException(status_code=409, detail="Car is already reserved for part of this period")

        blackout = conn.execute(
            """
            SELECT id FROM car_blackouts
            WHERE car_id = ?
              AND active = 1
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (payload.car_id, end_iso, start_iso),
        ).fetchone()
        if blackout:
            raise HTTPException(status_code=409, detail="Car is unavailable due to service or maintenance blackout")

        query = """
            INSERT INTO reservations(
                car_id, created_by_id, employee_name, start_time, end_time,
                purpose, status, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """
        params = (
            payload.car_id,
            auth.user_id,
            auth.display_name,
            start_iso,
            end_iso,
            payload.purpose,
            now,
            now,
        )
        if conn.backend == "postgres":
            reservation_id = int(conn.execute(f"{query} RETURNING id", params).fetchone()["id"])
        else:
            reservation_id = int(conn.execute(query, params).lastrowid)

        _log(conn, reservation_id, auth.user_id, "created", payload.purpose)

        admin_ids = [admin_id for admin_id in _active_admin_ids(conn) if admin_id != auth.user_id]
        if admin_ids:
            notification_ids.extend(
                create_notifications(
                    conn,
                    admin_ids,
                    kind="reservation_requested",
                    title="Нова заявка за автомобил",
                    body=f"{auth.display_name} заяви {car['plate_number']} за {start_iso}.",
                    reservation_id=reservation_id,
                )
            )

        row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        response = _serialize_reservation(row)

    dispatch_outbound_notifications(notification_ids)
    return response


def _decide(reservation_id: int, new_status: str, auth: AuthContext, reason: Optional[str]) -> dict[str, Any]:
    now = _utcnow_iso()
    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        cur = conn.execute(
            """
            UPDATE reservations
            SET status=?, decision_reason=?, decided_by_id=?, updated_at=?
            WHERE id=? AND status='pending'
            """,
            (new_status, reason, auth.user_id, now, reservation_id),
        )
        if cur.rowcount == 0:
            existing = conn.execute("SELECT 1 FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Reservation not found")
            raise HTTPException(status_code=409, detail=f"Only pending reservations can be {new_status}")

        row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        _log(conn, reservation_id, auth.user_id, new_status, reason)
        notification_ids.append(
            create_notification(
                conn,
                user_id=int(row["created_by_id"]),
                kind="reservation_decision",
                title="Резервацията е обновена",
                body=f"Заявката ти е {('одобрена' if new_status == 'approved' else 'отказана')}.",
                reservation_id=reservation_id,
            )
        )
        response = _serialize_reservation(row)

    dispatch_outbound_notifications(notification_ids)
    return response


@router.post("/{reservation_id}/approve")
def approve(reservation_id: int, payload: DecisionPayload, auth: AuthContext = Depends(require_admin)) -> dict[str, Any]:
    return _decide(reservation_id, "approved", auth, payload.reason)


@router.post("/{reservation_id}/reject")
def reject(reservation_id: int, payload: DecisionPayload, auth: AuthContext = Depends(require_admin)) -> dict[str, Any]:
    return _decide(reservation_id, "rejected", auth, payload.reason)


def _load_reservation_for_transition(conn: DbConn, reservation_id: int) -> Any:
    row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return row


@router.post("/{reservation_id}/start")
def start_trip(
    reservation_id: int,
    payload: LifecycleNotePayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    now = _utcnow_iso()
    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        row = _load_reservation_for_transition(conn, reservation_id)
        if auth.role != "fleet_admin" and int(row["created_by_id"]) != auth.user_id:
            raise HTTPException(status_code=403, detail="You can start only your own reservations")
        if row["status"] != "approved":
            raise HTTPException(status_code=409, detail="Only approved reservations can be started")
        if row["returned_at"]:
            raise HTTPException(status_code=409, detail="Returned reservations cannot be started again")
        if row["checked_out_at"]:
            raise HTTPException(status_code=409, detail="Trip already started")

        conn.execute(
            "UPDATE reservations SET checked_out_at=?, updated_at=? WHERE id=?",
            (now, now, reservation_id),
        )
        _log(conn, reservation_id, auth.user_id, "checked_out", payload.note)

        targets = [admin_id for admin_id in _active_admin_ids(conn) if admin_id != auth.user_id]
        if auth.role == "fleet_admin" and int(row["created_by_id"]) != auth.user_id:
            targets.append(int(row["created_by_id"]))
        if targets:
            notification_ids.extend(
                create_notifications(
                    conn,
                    targets,
                    kind="trip_started",
                    title="Автомобилът е взет",
                    body=f"Резервация #{reservation_id} е маркирана като активен курс.",
                    reservation_id=reservation_id,
                )
            )

        updated = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        response = _serialize_reservation(updated)

    dispatch_outbound_notifications(notification_ids)
    return response


@router.post("/{reservation_id}/return")
def return_trip(
    reservation_id: int,
    payload: LifecycleNotePayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    now = _utcnow_iso()
    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        row = _load_reservation_for_transition(conn, reservation_id)
        if auth.role != "fleet_admin" and int(row["created_by_id"]) != auth.user_id:
            raise HTTPException(status_code=403, detail="You can return only your own reservations")
        if row["status"] != "approved":
            raise HTTPException(status_code=409, detail="Only approved reservations can be returned")
        if not row["checked_out_at"]:
            raise HTTPException(status_code=409, detail="Trip must be started before it can be returned")
        if row["returned_at"]:
            raise HTTPException(status_code=409, detail="Trip already returned")

        conn.execute(
            "UPDATE reservations SET returned_at=?, updated_at=? WHERE id=?",
            (now, now, reservation_id),
        )
        _log(conn, reservation_id, auth.user_id, "returned", payload.note)

        targets = [admin_id for admin_id in _active_admin_ids(conn) if admin_id != auth.user_id]
        if auth.role == "fleet_admin" and int(row["created_by_id"]) != auth.user_id:
            targets.append(int(row["created_by_id"]))
        if targets:
            notification_ids.extend(
                create_notifications(
                    conn,
                    targets,
                    kind="trip_returned",
                    title="Автомобилът е върнат",
                    body=f"Резервация #{reservation_id} е приключена.",
                    reservation_id=reservation_id,
                )
            )

        updated = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        response = _serialize_reservation(updated)

    dispatch_outbound_notifications(notification_ids)
    return response


@router.post("/{reservation_id}/cancel")
def cancel(reservation_id: int, auth: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    now = _utcnow_iso()
    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        row = conn.execute(
            "SELECT id, created_by_id, status FROM reservations WHERE id=?",
            (reservation_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")
        if row["status"] not in {"pending", "approved"}:
            raise HTTPException(status_code=409, detail="Only pending/approved reservations can be cancelled")
        if auth.role != "fleet_admin" and int(row["created_by_id"]) != auth.user_id:
            raise HTTPException(status_code=403, detail="You can cancel only your own reservations")

        conn.execute(
            "UPDATE reservations SET status='cancelled', updated_at=? WHERE id=?",
            (now, reservation_id),
        )
        _log(conn, reservation_id, auth.user_id, "cancelled", None)

        targets: list[int] = []
        if auth.role == "fleet_admin":
            if int(row["created_by_id"]) != auth.user_id:
                targets.append(int(row["created_by_id"]))
        else:
            targets.extend([admin_id for admin_id in _active_admin_ids(conn) if admin_id != auth.user_id])
        if targets:
            notification_ids.extend(
                create_notifications(
                    conn,
                    targets,
                    kind="reservation_cancelled",
                    title="Резервацията е отменена",
                    body=f"Резервация #{reservation_id} вече не е активна.",
                    reservation_id=reservation_id,
                )
            )

        updated = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        response = _serialize_reservation(updated)

    dispatch_outbound_notifications(notification_ids)
    return response


@router.get("")
def list_reservations(
    car_id: Optional[int] = None,
    status_filter: Optional[ReservationStatus] = Query(default=None, alias="status_filter"),
    mine: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if car_id is not None:
        clauses.append("car_id = ?")
        params.append(car_id)
    if mine or auth.role == "employee":
        clauses.append("created_by_id = ?")
        params.append(auth.user_id)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM reservations{where} ORDER BY start_time"

    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    items = [_serialize_reservation(row) for row in rows]
    if status_filter is not None:
        items = [item for item in items if item["status"] == status_filter]

    total = len(items)
    paged = items[offset : offset + limit]
    return {"items": paged, "total": total, "limit": limit, "offset": offset}
