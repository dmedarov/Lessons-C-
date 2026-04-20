from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_conn
from netfleet_service import fetch_latest_gps_events
from schemas import BlackoutUpdatePayload, CarBlackoutCreate, CarBlackoutResponse, CarCreate, CarNotesPayload
from security import AuthContext, get_auth_context, require_admin

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


@router.get("/telemetry/latest")
def latest_car_telemetry(_: AuthContext = Depends(require_admin)) -> dict:
    try:
        telemetry = fetch_latest_gps_events()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="NetFleet telemetry unavailable") from exc
    return {"configured": telemetry.configured, "items": telemetry.items}


@router.get("/{car_id}/telemetry/latest")
def latest_car_telemetry_for_car(car_id: int, auth: AuthContext = Depends(get_auth_context)) -> dict:
    with get_conn() as conn:
        car = conn.execute("SELECT id, plate_number FROM cars WHERE id=?", (car_id,)).fetchone()
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        if auth.role != "fleet_admin":
            reservation = conn.execute(
                """
                SELECT id FROM reservations
                WHERE car_id=? AND created_by_id=? AND status='approved' AND returned_at IS NULL
                LIMIT 1
                """,
                (car_id, auth.user_id),
            ).fetchone()
            if not reservation:
                raise HTTPException(status_code=403, detail="No approved trip for this car")

    try:
        telemetry = fetch_latest_gps_events()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="NetFleet telemetry unavailable") from exc

    plate = str(car["plate_number"]).strip().upper()
    item = next((event for event in telemetry.items if event.get("plate_number") == plate), None)
    return {"configured": telemetry.configured, "item": item}


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


@router.put("/{car_id}/blackouts/{blackout_id}", response_model=CarBlackoutResponse)
def update_blackout(
    car_id: int,
    blackout_id: int,
    payload: BlackoutUpdatePayload,
    _: AuthContext = Depends(require_admin),
) -> CarBlackoutResponse:
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    start_iso = _to_utc_iso(payload.start_time)
    end_iso = _to_utc_iso(payload.end_time)

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM car_blackouts WHERE id=? AND car_id=? AND active=1",
            (blackout_id, car_id),
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Blackout not found or inactive")

        overlap = conn.execute(
            """
            SELECT id FROM car_blackouts
            WHERE car_id=? AND active=1 AND id != ?
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (car_id, blackout_id, end_iso, start_iso),
        ).fetchone()
        if overlap:
            raise HTTPException(status_code=409, detail="Blackout overlaps an existing active blackout")

        conn.execute(
            "UPDATE car_blackouts SET kind=?, start_time=?, end_time=?, reason=? WHERE id=?",
            (payload.kind, start_iso, end_iso, payload.reason, blackout_id),
        )
        row = conn.execute("SELECT * FROM car_blackouts WHERE id=?", (blackout_id,)).fetchone()
    return _to_blackout_response(row)


@router.put("/{car_id}/notes")
def update_car_notes(car_id: int, payload: CarNotesPayload, _: AuthContext = Depends(require_admin)) -> dict:
    with get_conn() as conn:
        cur = conn.execute("UPDATE cars SET notes=? WHERE id=?", (payload.notes, car_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Car not found")
        row = conn.execute("SELECT * FROM cars WHERE id=?", (car_id,)).fetchone()
    return dict(row)


@router.post("/blackouts/{blackout_id}/deactivate", response_model=CarBlackoutResponse)
def deactivate_blackout(blackout_id: int, _: AuthContext = Depends(require_admin)) -> CarBlackoutResponse:
    with get_conn() as conn:
        cur = conn.execute("UPDATE car_blackouts SET active=0 WHERE id=? AND active=1", (blackout_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Blackout not found or already inactive")
        row = conn.execute("SELECT * FROM car_blackouts WHERE id=?", (blackout_id,)).fetchone()
    return _to_blackout_response(row)
