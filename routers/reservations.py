from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from db import get_conn, transaction
from schemas import DecisionPayload, ReservationCreate, ReservationStatus
from security import AuthContext, get_auth_context, require_admin

router = APIRouter(prefix="/reservations", tags=["reservations"])


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _log(conn: sqlite3.Connection, reservation_id: int, actor_id: int, action: str, reason: Optional[str]) -> None:
    conn.execute(
        "INSERT INTO audit_log(reservation_id, actor_id, action, reason, at) VALUES(?, ?, ?, ?, ?)",
        (reservation_id, actor_id, action, reason, _utcnow_iso()),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")
    if payload.end_time <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="end_time must be in the future")

    start_iso = _to_utc_iso(payload.start_time)
    end_iso = _to_utc_iso(payload.end_time)
    now = _utcnow_iso()

    with get_conn() as conn, transaction(conn):
        car = conn.execute("SELECT id, active FROM cars WHERE id=?", (payload.car_id,)).fetchone()
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        if not car["active"]:
            raise HTTPException(status_code=409, detail="Car is inactive")

        overlapping = conn.execute(
            """
            SELECT id FROM reservations
            WHERE car_id = ?
              AND status IN ('pending', 'approved')
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (payload.car_id, end_iso, start_iso),
        ).fetchone()
        if overlapping:
            raise HTTPException(status_code=409, detail="Car is already reserved for part of this period")

        cur = conn.execute(
            """
            INSERT INTO reservations(
                car_id, created_by_id, employee_name, start_time, end_time,
                purpose, status, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                payload.car_id,
                auth.user_id,
                auth.display_name,
                start_iso,
                end_iso,
                payload.purpose,
                now,
                now,
            ),
        )
        _log(conn, cur.lastrowid, auth.user_id, "created", payload.purpose)
        row = conn.execute("SELECT * FROM reservations WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)


def _decide(reservation_id: int, new_status: str, auth: AuthContext, reason: Optional[str]) -> dict:
    now = _utcnow_iso()
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

        _log(conn, reservation_id, auth.user_id, new_status, reason)
        row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        return dict(row)


@router.post("/{reservation_id}/approve")
def approve(reservation_id: int, payload: DecisionPayload, auth: AuthContext = Depends(require_admin)) -> dict:
    return _decide(reservation_id, "approved", auth, payload.reason)


@router.post("/{reservation_id}/reject")
def reject(reservation_id: int, payload: DecisionPayload, auth: AuthContext = Depends(require_admin)) -> dict:
    return _decide(reservation_id, "rejected", auth, payload.reason)


@router.post("/{reservation_id}/cancel")
def cancel(reservation_id: int, auth: AuthContext = Depends(get_auth_context)) -> dict:
    now = _utcnow_iso()
    with get_conn() as conn, transaction(conn):
        row = conn.execute(
            "SELECT id, created_by_id, status FROM reservations WHERE id=?",
            (reservation_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Reservation not found")
        if row["status"] not in {"pending", "approved"}:
            raise HTTPException(status_code=409, detail="Only pending/approved reservations can be cancelled")
        if auth.role != "fleet_admin" and row["created_by_id"] != auth.user_id:
            raise HTTPException(status_code=403, detail="You can cancel only your own reservations")

        conn.execute(
            "UPDATE reservations SET status='cancelled', updated_at=? WHERE id=?",
            (now, reservation_id),
        )
        _log(conn, reservation_id, auth.user_id, "cancelled", None)
        updated = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        return dict(updated)


@router.get("")
def list_reservations(
    car_id: Optional[int] = None,
    status_filter: Optional[ReservationStatus] = Query(default=None, alias="status_filter"),
    mine: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    clauses: list[str] = []
    params: list = []
    if car_id is not None:
        clauses.append("car_id = ?")
        params.append(car_id)
    if status_filter is not None:
        clauses.append("status = ?")
        params.append(status_filter)
    if mine or auth.role == "employee":
        clauses.append("created_by_id = ?")
        params.append(auth.user_id)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM reservations{where} ORDER BY start_time LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        total_query = f"SELECT COUNT(*) AS n FROM reservations{where}"
        total = conn.execute(total_query, params[:-2]).fetchone()["n"]

    return {"items": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}
