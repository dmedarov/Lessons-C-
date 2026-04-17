from __future__ import annotations

import base64
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DB_PATH", "/data/fleet.db")

app = FastAPI(title="Corporate Car Pool Reservation")

Role = Literal["employee", "fleet_admin"]
ReservationStatus = Literal["pending", "approved", "rejected", "cancelled"]

DEMO_USERS = {
    "admin": {"password": "admin123", "display_name": "Fleet Admin", "role": "fleet_admin"},
    "ivan": {"password": "employee123", "display_name": "Ivan Petrov", "role": "employee"},
}


class AuthContext(BaseModel):
    user: str
    role: Role


class LoginPayload(BaseModel):
    username: str
    password: str


class CarCreate(BaseModel):
    plate_number: str = Field(min_length=2, max_length=32)
    model: str = Field(min_length=2, max_length=100)


class ReservationCreate(BaseModel):
    car_id: int
    employee_name: str = Field(min_length=2, max_length=100)
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = Field(default=None, max_length=500)


class DecisionPayload(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


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


def build_token(user: str, role: Role) -> str:
    raw = json.dumps({"user": user, "role": role}, ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def parse_token(token: str) -> AuthContext:
    try:
        payload = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        data = json.loads(payload)
        role = data.get("role", "")
        user = data.get("user", "anonymous")
        if role not in {"employee", "fleet_admin"}:
            raise ValueError("invalid role")
        return AuthContext(user=user, role=role)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid bearer token") from exc


def get_auth_context(
    authorization: Optional[str] = Header(default=None),
    x_user: Optional[str] = Header(default="anonymous"),
    x_role: Optional[str] = Header(default="employee"),
) -> AuthContext:
    if authorization:
        prefix = "Bearer "
        if not authorization.startswith(prefix):
            raise HTTPException(status_code=401, detail="Authorization must be Bearer token")
        return parse_token(authorization[len(prefix) :].strip())

    role = (x_role or "employee").strip().lower()
    if role not in {"employee", "fleet_admin"}:
        raise HTTPException(status_code=400, detail="Invalid role. Use employee or fleet_admin")
    return AuthContext(user=(x_user or "anonymous").strip(), role=role)  # type: ignore[arg-type]


def require_admin(auth: AuthContext) -> None:
    if auth.role != "fleet_admin":
        raise HTTPException(status_code=403, detail="fleet_admin role is required")


def ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(ddl)


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
                status TEXT NOT NULL DEFAULT 'pending',
                decision_reason TEXT,
                created_by TEXT,
                approved_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(car_id) REFERENCES cars(id)
            )
            """
        )
        ensure_column(conn, "reservations", "status", "ALTER TABLE reservations ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
        ensure_column(conn, "reservations", "decision_reason", "ALTER TABLE reservations ADD COLUMN decision_reason TEXT")
        ensure_column(conn, "reservations", "created_by", "ALTER TABLE reservations ADD COLUMN created_by TEXT")
        ensure_column(conn, "reservations", "approved_by", "ALTER TABLE reservations ADD COLUMN approved_by TEXT")
        ensure_column(conn, "reservations", "updated_at", "ALTER TABLE reservations ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_reservations_car_time
            ON reservations(car_id, start_time, end_time)
            """
        )


@app.post("/auth/login")
def login(payload: LoginPayload) -> dict:
    user = DEMO_USERS.get(payload.username.strip().lower())
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = build_token(user=user["display_name"], role=user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user["display_name"],
        "role": user["role"],
    }


@app.get("/", include_in_schema=False)
def ui() -> FileResponse:
    return FileResponse(BASE_DIR / "templates" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/cars", status_code=status.HTTP_201_CREATED)
def create_car(payload: CarCreate, auth: AuthContext = Depends(get_auth_context)) -> dict:
    require_admin(auth)
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
def create_reservation(payload: ReservationCreate, auth: AuthContext = Depends(get_auth_context)) -> dict:
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
              AND status IN ('pending', 'approved')
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

        now = datetime.utcnow().isoformat() + "Z"
        cur = conn.execute(
            """
            INSERT INTO reservations(
                car_id, employee_name, start_time, end_time, purpose,
                status, created_by, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (
                payload.car_id,
                payload.employee_name.strip(),
                start_iso,
                end_iso,
                payload.purpose,
                auth.user,
                now,
                now,
            ),
        )
        conn.execute("COMMIT")
        row = conn.execute("SELECT * FROM reservations WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)


@app.post("/reservations/{reservation_id}/approve")
def approve_reservation(
    reservation_id: int,
    payload: DecisionPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    require_admin(auth)
    with get_conn() as conn:
        now = datetime.utcnow().isoformat() + "Z"
        cur = conn.execute(
            """
            UPDATE reservations
            SET status='approved', decision_reason=?, approved_by=?, updated_at=?
            WHERE id=? AND status='pending'
            """,
            (payload.reason, auth.user, now, reservation_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=409, detail="Only pending reservations can be approved")
        row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        return dict(row)


@app.post("/reservations/{reservation_id}/reject")
def reject_reservation(
    reservation_id: int,
    payload: DecisionPayload,
    auth: AuthContext = Depends(get_auth_context),
) -> dict:
    require_admin(auth)
    with get_conn() as conn:
        now = datetime.utcnow().isoformat() + "Z"
        cur = conn.execute(
            """
            UPDATE reservations
            SET status='rejected', decision_reason=?, approved_by=?, updated_at=?
            WHERE id=? AND status='pending'
            """,
            (payload.reason, auth.user, now, reservation_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=409, detail="Only pending reservations can be rejected")
        row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        return dict(row)


@app.post("/reservations/{reservation_id}/cancel")
def cancel_reservation(reservation_id: int, auth: AuthContext = Depends(get_auth_context)) -> dict:
    with get_conn() as conn:
        reservation = conn.execute(
            "SELECT id, employee_name, status FROM reservations WHERE id=?", (reservation_id,)
        ).fetchone()
        if not reservation:
            raise HTTPException(status_code=404, detail="Reservation not found")
        if reservation["status"] not in {"pending", "approved"}:
            raise HTTPException(status_code=409, detail="Only pending/approved reservations can be cancelled")
        if auth.role != "fleet_admin" and auth.user != reservation["employee_name"]:
            raise HTTPException(status_code=403, detail="You can cancel only your own reservations")

        now = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            "UPDATE reservations SET status='cancelled', updated_at=? WHERE id=?",
            (now, reservation_id),
        )
        row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
        return dict(row)


@app.get("/reservations")
def list_reservations(
    car_id: Optional[int] = None,
    status_filter: Optional[ReservationStatus] = None,
) -> dict[str, list[dict]]:
    with get_conn() as conn:
        if car_id is None and status_filter is None:
            rows = conn.execute(
                "SELECT * FROM reservations ORDER BY start_time"
            ).fetchall()
        elif car_id is not None and status_filter is None:
            rows = conn.execute(
                "SELECT * FROM reservations WHERE car_id=? ORDER BY start_time",
                (car_id,),
            ).fetchall()
        elif car_id is None and status_filter is not None:
            rows = conn.execute(
                "SELECT * FROM reservations WHERE status=? ORDER BY start_time",
                (status_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reservations WHERE car_id=? AND status=? ORDER BY start_time",
                (car_id, status_filter),
            ).fetchall()

        return {"items": [dict(r) for r in rows]}
