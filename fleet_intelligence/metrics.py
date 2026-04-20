from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any


def parse_datetime(value: Any) -> datetime:
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def active_cars(conn: Any) -> list[Any]:
    return conn.execute(
        "SELECT id, plate_number, model FROM cars WHERE active=1 ORDER BY id"
    ).fetchall()


def unavailable_car_ids(conn: Any, start_iso: str, end_iso: str) -> set[int]:
    reservation_rows = conn.execute(
        """
        SELECT DISTINCT car_id
        FROM reservations
        WHERE (
                status = 'pending'
             OR (status = 'approved' AND returned_at IS NULL)
          )
          AND start_time < ?
          AND end_time > ?
        """,
        (end_iso, start_iso),
    ).fetchall()
    blackout_rows = conn.execute(
        """
        SELECT DISTINCT car_id
        FROM car_blackouts
        WHERE active = 1
          AND start_time < ?
          AND end_time > ?
        """,
        (end_iso, start_iso),
    ).fetchall()
    return {int(row["car_id"]) for row in [*reservation_rows, *blackout_rows]}


def recent_utilization_minutes(conn: Any, *, now: datetime | None = None, days: int = 7) -> dict[int, int]:
    now = now or datetime.now(timezone.utc)
    since_iso = to_utc_iso(now - timedelta(days=days))
    rows = conn.execute(
        """
        SELECT car_id, start_time, end_time
        FROM reservations
        WHERE created_at >= ?
          AND status IN ('pending','approved')
        """,
        (since_iso,),
    ).fetchall()

    totals: dict[int, int] = {}
    for row in rows:
        start = parse_datetime(row["start_time"])
        end = parse_datetime(row["end_time"])
        minutes = max(int((end - start).total_seconds() // 60), 0)
        car_id = int(row["car_id"])
        totals[car_id] = totals.get(car_id, 0) + minutes
    return totals


def user_car_preferences(conn: Any, user_id: int, limit: int = 10) -> Counter[int]:
    rows = conn.execute(
        """
        SELECT car_id
        FROM reservations
        WHERE created_by_id=?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return Counter(int(row["car_id"]) for row in rows)


def active_trip_count(conn: Any) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM reservations
        WHERE status='approved'
          AND checked_out_at IS NOT NULL
          AND returned_at IS NULL
        """
    ).fetchone()
    return int(row["n"])


def pending_request_count(conn: Any) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM reservations WHERE status='pending'").fetchone()
    return int(row["n"])


def busiest_car_label(conn: Any) -> str | None:
    rows = conn.execute(
        """
        SELECT c.plate_number, c.model, COUNT(*) AS n
        FROM reservations r
        JOIN cars c ON c.id = r.car_id
        WHERE r.status IN ('pending','approved')
        GROUP BY c.id, c.plate_number, c.model
        ORDER BY n DESC, c.id
        LIMIT 1
        """
    ).fetchall()
    if not rows:
        return None
    row = rows[0]
    return f"{row['plate_number']} · {row['model']}"
