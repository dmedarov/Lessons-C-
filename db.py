from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from config import settings
from security import hash_password

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('employee','fleet_admin')),
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT UNIQUE NOT NULL,
        model TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        car_id INTEGER NOT NULL REFERENCES cars(id),
        created_by_id INTEGER NOT NULL REFERENCES users(id),
        employee_name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        purpose TEXT,
        status TEXT NOT NULL DEFAULT 'pending'
            CHECK(status IN ('pending','approved','rejected','cancelled')),
        decision_reason TEXT,
        decided_by_id INTEGER REFERENCES users(id),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reservation_id INTEGER NOT NULL REFERENCES reservations(id),
        actor_id INTEGER NOT NULL REFERENCES users(id),
        action TEXT NOT NULL,
        reason TEXT,
        at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reservations_car_time ON reservations(car_id, start_time, end_time)",
    "CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status)",
    "CREATE INDEX IF NOT EXISTS idx_audit_reservation ON audit_log(reservation_id)",
]

DEMO_USERS = [
    ("admin", "Fleet Admin", "admin123", "fleet_admin"),
    ("ivan", "Ivan Petrov", "employee123", "employee"),
]


def _db_path() -> str:
    # Read dynamically so tests can monkeypatch the setting.
    return os.getenv("DB_PATH", settings.db_path)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path(), timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def init_db() -> None:
    db_path = _db_path()
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with get_conn() as conn:
        for stmt in SCHEMA:
            conn.execute(stmt)
        _seed_users(conn)


def _seed_users(conn: sqlite3.Connection) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    for username, display, password, role in DEMO_USERS:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE username=?", (username,)
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """
            INSERT INTO users(username, display_name, password_hash, role, created_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (username, display, hash_password(password), role, now),
        )
