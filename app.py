from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH", "/data/fleet.db")

app = FastAPI(title="Corporate Car Pool Reservation")


class CarCreate(BaseModel):
    plate_number: str = Field(min_length=2, max_length=32)
    model: str = Field(min_length=2, max_length=100)


class ReservationCreate(BaseModel):
    car_id: int
    employee_name: str = Field(min_length=2, max_length=100)
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = Field(default=None, max_length=500)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
    finally:
        conn.close()


@app.on_event("startup")
def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT UNIQUE NOT NULL,
                model TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id INTEGER NOT NULL,
                employee_name TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                purpose TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(car_id) REFERENCES cars(id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reservations_car_time
            ON reservations(car_id, start_time, end_time)
            """
        )




@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/cars", status_code=status.HTTP_201_CREATED)
def create_car(payload: CarCreate) -> dict:
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO cars(plate_number, model) VALUES(?, ?)",
                (payload.plate_number.upper().strip(), payload.model.strip()),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Car already exists") from exc

        car_id = cur.lastrowid
        row = conn.execute("SELECT * FROM cars WHERE id=?", (car_id,)).fetchone()
        return dict(row)


@app.get("/cars")
def list_cars(active_only: bool = True) -> dict[str, list[dict]]:
    query = "SELECT * FROM cars"
    params = ()
    if active_only:
        query += " WHERE active=1"
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    return {"items": rows}


@app.post("/reservations", status_code=status.HTTP_201_CREATED)
def create_reservation(payload: ReservationCreate) -> dict:
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="end_time must be after start_time")

    start_iso = payload.start_time.isoformat()
    end_iso = payload.end_time.isoformat()

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        car = conn.execute(
            "SELECT id, active FROM cars WHERE id=?", (payload.car_id,)
        ).fetchone()
        if not car:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=404, detail="Car not found")
        if car["active"] != 1:
            conn.execute("ROLLBACK")
            raise HTTPException(status_code=409, detail="Car is inactive")

        overlapping = conn.execute(
            """
            SELECT id FROM reservations
            WHERE car_id = ?
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (payload.car_id, end_iso, start_iso),
        ).fetchone()

        if overlapping:
            conn.execute("ROLLBACK")
            raise HTTPException(
                status_code=409,
                detail="Car is already reserved for part of this period",
            )

        cur = conn.execute(
            """
            INSERT INTO reservations(car_id, employee_name, start_time, end_time, purpose, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                payload.car_id,
                payload.employee_name.strip(),
                start_iso,
                end_iso,
                payload.purpose,
                datetime.utcnow().isoformat() + "Z",
            ),
        )
        conn.execute("COMMIT")
        row = conn.execute("SELECT * FROM reservations WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)


@app.get("/reservations")
def list_reservations(car_id: Optional[int] = None) -> dict[str, list[dict]]:
    with get_conn() as conn:
        if car_id is None:
            rows = conn.execute(
                "SELECT * FROM reservations ORDER BY start_time"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reservations WHERE car_id=? ORDER BY start_time",
                (car_id,),
            ).fetchall()

        return {"items": [dict(r) for r in rows]}
