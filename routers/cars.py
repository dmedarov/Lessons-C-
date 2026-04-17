from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from db import get_conn
from schemas import CarCreate
from security import AuthContext, require_admin

router = APIRouter(prefix="/cars", tags=["cars"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_car(payload: CarCreate, _: AuthContext = Depends(require_admin)) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO cars(plate_number, model, created_at) VALUES(?, ?, ?)",
                (payload.plate_number.upper().strip(), payload.model.strip(), now),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Car already exists") from exc

        row = conn.execute("SELECT * FROM cars WHERE id=?", (cur.lastrowid,)).fetchone()
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
