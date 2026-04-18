from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_conn
from schemas import CarBlackoutCreate, CarBlackoutResponse, CarCreate
from security import AuthContext, require_admin

router = APIRouter(prefix="/cars", tags=["cars"])


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _to_blackout_response(row) -> CarBlackoutResponse:
    return CarBlackoutResponse(
        id=int(row["id"]),
        car_id=int(row["car_id"]),
        kind=row["kind"],
        start_time=str(row["start_time"]),
        end_time=str(row["end_time"]),
        reason=row["reason"],
        active=bool(row["active"]),
        created_by_id=int(row["created_by_id"]),
        created_at=str(row["created_at"]),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_car(payload: CarCreate, _: AuthContext = Depends(require_admin)) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        try:
            query = "INSERT INTO cars(plate_number, model, created_at) VALUES(?, ?, ?)"
            params = (payload.plate_number.upper().strip(), payload.model.strip(), now)
            if conn.backend == "postgres":
                car_id = conn.execute(f"{query} RETURNING id", params).fetchone()["id"]
            else:
                car_id = conn.execute(query, params).lastrowid
        except Exception as exc:
            pg_integrity_error = None
            try:
                from psycopg import IntegrityError as pg_integrity_error
            except ImportError:
                pass
            if not isinstance(exc, sqlite3.IntegrityError) and not (
                pg_integrity_error and isinstance(exc, pg_integrity_error)
            ):
                raise
            raise HTTPException(status_code=409, detail="Car already exists") from exc

        row = conn.execute("SELECT * FROM cars WHERE id=?", (car_id,)).fetchone()
        return dict(row)


@router.get("")
def list_cars(active_only: bool = True) -> dict[str, list[dict]]:
    query = "SELECT * FROM cars"
    params: tuple = ()
    if active_only:
        query += " WHERE active=1"
    query += " ORDER BY id"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/{car_id}/deactivate")
def deactivate_car(car_id: int, _: AuthContext = Depends(require_admin)) -> dict:
    with get_conn() as conn:
        cur = conn.execute("UPDATE cars SET active=0 WHERE id=? AND active=1", (car_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Car not found or already inactive")
        row = conn.execute("SELECT * FROM cars WHERE id=?", (car_id,)).fetchone()
        return dict(row)


@router.post("/{car_id}/activate")
def activate_car(car_id: int, _: AuthContext = Depends(require_admin)) -> dict:
    with get_conn() as conn:
        cur = conn.execute("UPDATE cars SET active=1 WHERE id=? AND active=0", (car_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Car not found or already active")
        row = conn.execute("SELECT * FROM cars WHERE id=?", (car_id,)).fetchone()
        return dict(row)


@router.get("/{car_id}/blackouts", response_model=list[CarBlackoutResponse])
def list_blackouts(car_id: int, active_only: bool = True, _: AuthContext = Depends(require_admin)) -> list[CarBlackoutResponse]:
    query = "SELECT * FROM car_blackouts WHERE car_id=?"
    params: list = [car_id]
    if active_only:
        query += " AND active=1"
    query += " ORDER BY start_time"
    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
    return [_to_blackout_response(row) for row in rows]


@router.post("/{car_id}/blackouts", response_model=CarBlackoutResponse, status_code=status.HTTP_201_CREATED)
def create_blackout(
    car_id: int,
    payload: CarBlackoutCreate,
    auth: AuthContext = Depends(require_admin),
) -> CarBlackoutResponse:
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    start_iso = _to_utc_iso(payload.start_time)
    end_iso = _to_utc_iso(payload.end_time)
    now = datetime.now(timezone.utc).isoformat()

    with get_conn() as conn:
        car = conn.execute("SELECT id FROM cars WHERE id=?", (car_id,)).fetchone()
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

        overlap = conn.execute(
            """
            SELECT id FROM car_blackouts
            WHERE car_id=?
              AND active=1
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (car_id, end_iso, start_iso),
        ).fetchone()
        if overlap:
            raise HTTPException(status_code=409, detail="Blackout overlaps an existing active blackout")

        if conn.backend == "postgres":
            row = conn.execute(
                """
                INSERT INTO car_blackouts(car_id, kind, start_time, end_time, reason, created_by_id, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                RETURNING *
                """,
                (car_id, payload.kind, start_iso, end_iso, payload.reason, auth.user_id, now),
            ).fetchone()
        else:
            blackout_id = conn.execute(
                """
                INSERT INTO car_blackouts(car_id, kind, start_time, end_time, reason, created_by_id, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (car_id, payload.kind, start_iso, end_iso, payload.reason, auth.user_id, now),
            ).lastrowid
            row = conn.execute("SELECT * FROM car_blackouts WHERE id=?", (blackout_id,)).fetchone()

    return _to_blackout_response(row)


@router.post("/blackouts/{blackout_id}/deactivate", response_model=CarBlackoutResponse)
def deactivate_blackout(blackout_id: int, _: AuthContext = Depends(require_admin)) -> CarBlackoutResponse:
    with get_conn() as conn:
        cur = conn.execute("UPDATE car_blackouts SET active=0 WHERE id=? AND active=1", (blackout_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Blackout not found or already inactive")
        row = conn.execute("SELECT * FROM car_blackouts WHERE id=?", (blackout_id,)).fetchone()
    return _to_blackout_response(row)
