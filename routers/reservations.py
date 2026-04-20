from __future__ import annotations

import csv
import io
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from db import PostgresConnectionAdapter, SQLiteConnectionAdapter, get_conn, transaction
from fleet_intelligence.service import suggest_best_car
from fleet_intelligence.schemas import SuggestedAssignment
from notifications_service import create_notification, create_notifications, dispatch_outbound_notifications
from schemas import (
    BulkDecisionItem,
    BulkDecisionPayload,
    BulkDecisionResponse,
    DecisionPayload,
    LifecycleNotePayload,
    ReservationCreate,
    ReservationPreferencesResponse,
    ReservationStatus,
)
from security import (
    AuthContext,
    get_auth_context,
    is_operational_role,
    require_admin,
    require_approver,
    require_employee,
    require_reception,
)

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


def _active_role_ids(conn: DbConn, roles: tuple[str, ...]) -> list[int]:
    placeholders = ",".join("?" for _ in roles)
    rows = conn.execute(
        f"SELECT id FROM users WHERE role IN ({placeholders}) AND active=1 ORDER BY id",
        roles,
    ).fetchall()
    return [int(row["id"]) for row in rows]


def _active_admin_ids(conn: DbConn) -> list[int]:
    return _active_role_ids(conn, ("fleet_admin",))


def _active_decision_recipient_ids(conn: DbConn) -> list[int]:
    return _active_role_ids(conn, ("fleet_admin", "fleet_approver"))


def _active_reception_recipient_ids(conn: DbConn) -> list[int]:
    return _active_role_ids(conn, ("fleet_admin", "fleet_reception"))


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


def _reservation_filter_clauses(
    *,
    car_id: Optional[int],
    mine: bool,
    user_id: int,
    start: Optional[datetime],
    end: Optional[datetime],
    search: Optional[str],
) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if car_id is not None:
        clauses.append("r.car_id = ?")
        params.append(car_id)
    if mine:
        clauses.append("r.created_by_id = ?")
        params.append(user_id)
    if start is not None:
        clauses.append("r.end_time > ?")
        params.append(_to_utc_iso(start))
    if end is not None:
        clauses.append("r.start_time < ?")
        params.append(_to_utc_iso(end))
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        clauses.append(
            """
            (
                LOWER(c.plate_number) LIKE ?
             OR LOWER(COALESCE(c.model, '')) LIKE ?
             OR LOWER(COALESCE(r.employee_name, '')) LIKE ?
             OR LOWER(COALESCE(r.purpose, '')) LIKE ?
            )
            """
        )
        params.extend([term, term, term, term])
    return clauses, params


def _reservation_conflict_rows(conn: DbConn, car_id: int, start_iso: str, end_iso: str) -> list[Any]:
    return conn.execute(
        """
        SELECT
            id, car_id, created_by_id, employee_name, start_time, end_time,
            purpose, status, checked_out_at, returned_at
        FROM reservations
        WHERE car_id = ?
          AND (
                status = 'pending'
             OR (status = 'approved' AND returned_at IS NULL)
          )
          AND start_time < ?
          AND end_time > ?
        ORDER BY start_time
        """,
        (car_id, end_iso, start_iso),
    ).fetchall()


def _blackout_conflict_rows(conn: DbConn, car_id: int, start_iso: str, end_iso: str) -> list[Any]:
    return conn.execute(
        """
        SELECT id, car_id, kind, start_time, end_time, reason
        FROM car_blackouts
        WHERE car_id = ?
          AND active = 1
          AND start_time < ?
          AND end_time > ?
        ORDER BY start_time
        """,
        (car_id, end_iso, start_iso),
    ).fetchall()


def _round_up_to_quarter_hour(value: datetime) -> datetime:
    timestamp = int(value.timestamp())
    rounded = ((timestamp + 899) // 900) * 900
    return datetime.fromtimestamp(rounded, tz=timezone.utc)


def _parse_datetime(value: Any) -> datetime:
    text = str(value)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _assignment_to_suggestion(assignment: SuggestedAssignment, duration_minutes: int) -> dict[str, Any]:
    return {
        "car_id": assignment.car_id,
        "plate_number": assignment.plate_number,
        "model": assignment.model,
        "start_time": assignment.start_time,
        "end_time": assignment.end_time,
        "duration_minutes": duration_minutes,
        "purpose": "Бърза заявка от FleetFlow",
        "score": assignment.score,
        "reason_code": assignment.reason_code,
        "reason_text": assignment.reason_text,
        "scoring": assignment.scoring,
    }


def _find_suggested_slot(conn: DbConn, user_id: int, duration_minutes: int = 120) -> dict[str, Any]:
    cars = conn.execute(
        "SELECT id, plate_number, model FROM cars WHERE active=1 ORDER BY id"
    ).fetchall()
    if not cars:
        raise HTTPException(status_code=409, detail="No active cars available")

    duration = timedelta(minutes=duration_minutes)
    first_start = _round_up_to_quarter_hour(datetime.now(timezone.utc) + timedelta(minutes=30))
    search_steps = 7 * 24 * 2  # 7 days in 30-minute increments.

    for step in range(search_steps):
        start = first_start + timedelta(minutes=step * 30)
        end = start + duration
        assignment = suggest_best_car(conn, user_id=user_id, start=start, end=end)
        if assignment:
            return _assignment_to_suggestion(assignment, duration_minutes)

    raise HTTPException(status_code=409, detail="No free slot found in the next 7 days")


def _record_car_assignment(
    conn: DbConn,
    *,
    reservation_id: int,
    car_id: int,
    assignment_mode: str,
    score: float,
    reason_code: str,
    reason_text: str,
) -> None:
    conn.execute(
        """
        INSERT INTO car_assignments(
            reservation_id, car_id, assignment_mode, score, reason_code,
            reason_text, created_at
        )
        VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        (
            reservation_id,
            car_id,
            assignment_mode,
            score,
            reason_code,
            reason_text,
            _utcnow_iso(),
        ),
    )


def _create_reservation(
    payload: ReservationCreate,
    background_tasks: BackgroundTasks,
    auth: AuthContext,
    *,
    assignment_mode: str = "manual",
    assignment_score: float = 0,
    assignment_reason_code: str = "manual_selection",
    assignment_reason_text: str = "Колата е избрана ръчно от потребителя.",
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

        if _reservation_conflict_rows(conn, payload.car_id, start_iso, end_iso):
            raise HTTPException(status_code=409, detail="Car is already reserved for part of this period")

        if _blackout_conflict_rows(conn, payload.car_id, start_iso, end_iso):
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
        _record_car_assignment(
            conn,
            reservation_id=reservation_id,
            car_id=payload.car_id,
            assignment_mode=assignment_mode,
            score=assignment_score,
            reason_code=assignment_reason_code,
            reason_text=assignment_reason_text,
        )

        admin_ids = [admin_id for admin_id in _active_decision_recipient_ids(conn) if admin_id != auth.user_id]
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

    if notification_ids:
        background_tasks.add_task(dispatch_outbound_notifications, notification_ids)
    return response


@router.post("", status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_employee),
) -> dict[str, Any]:
    return _create_reservation(payload, background_tasks, auth)


@router.get("/conflicts")
def reservation_conflicts(
    car_id: int = Query(..., ge=1),
    start: datetime = Query(...),
    end: datetime = Query(...),
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    if end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")

    start_iso = _to_utc_iso(start)
    end_iso = _to_utc_iso(end)

    with get_conn() as conn:
        car = conn.execute("SELECT id FROM cars WHERE id=?", (car_id,)).fetchone()
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")

        reservation_items = []
        for row in _reservation_conflict_rows(conn, car_id, start_iso, end_iso):
            item = {
                "type": "reservation",
                "id": int(row["id"]),
                "car_id": int(row["car_id"]),
                "start_time": str(row["start_time"]),
                "end_time": str(row["end_time"]),
                "status": _presentation_status(row),
            }
            if is_operational_role(auth.role):
                item["employee_name"] = str(row["employee_name"])
                item["purpose"] = row["purpose"]
            reservation_items.append(item)

        blackout_items = [
            {
                "type": "blackout",
                "id": int(row["id"]),
                "car_id": int(row["car_id"]),
                "kind": str(row["kind"]),
                "start_time": str(row["start_time"]),
                "end_time": str(row["end_time"]),
                "reason": row["reason"] if is_operational_role(auth.role) else None,
            }
            for row in _blackout_conflict_rows(conn, car_id, start_iso, end_iso)
        ]

    items = sorted(reservation_items + blackout_items, key=lambda item: item["start_time"])
    return {"items": items, "total": len(items)}


@router.get("/suggest")
def suggest_reservation(
    duration_minutes: int = Query(default=120, ge=15, le=480),
    auth: AuthContext = Depends(require_employee),
) -> dict[str, Any]:
    with get_conn() as conn:
        return _find_suggested_slot(conn, auth.user_id, duration_minutes)


@router.get("/suggest-best-car")
def suggest_best_car_for_slot(
    start: datetime = Query(...),
    end: datetime = Query(...),
    auth: AuthContext = Depends(require_employee),
) -> dict[str, Any]:
    if end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")
    if start <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="start must be in the future")

    with get_conn() as conn:
        assignment = suggest_best_car(conn, user_id=auth.user_id, start=start, end=end)
    if not assignment:
        raise HTTPException(status_code=409, detail="No active car is available for this slot")
    return assignment.model_dump()


@router.post("/quick-book", status_code=status.HTTP_201_CREATED)
def quick_book(
    background_tasks: BackgroundTasks,
    duration_minutes: int = Query(default=120, ge=15, le=480),
    auth: AuthContext = Depends(require_employee),
) -> dict[str, Any]:
    with get_conn() as conn:
        suggestion = _find_suggested_slot(conn, auth.user_id, duration_minutes)
    payload = ReservationCreate(
        car_id=int(suggestion["car_id"]),
        start_time=datetime.fromisoformat(str(suggestion["start_time"])),
        end_time=datetime.fromisoformat(str(suggestion["end_time"])),
        purpose=str(suggestion["purpose"]),
    )
    response = _create_reservation(
        payload,
        background_tasks,
        auth,
        assignment_mode="quick_book",
        assignment_score=float(suggestion.get("score", 0)),
        assignment_reason_code=str(suggestion.get("reason_code", "quick_book")),
        assignment_reason_text=str(suggestion.get("reason_text", "FleetFlow избра кола за бърза заявка.")),
    )
    response["quick_suggestion"] = suggestion
    return response


@router.get("/preferences", response_model=ReservationPreferencesResponse)
def reservation_preferences(auth: AuthContext = Depends(require_employee)) -> ReservationPreferencesResponse:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.car_id, r.start_time, r.end_time, c.plate_number, c.model
            FROM reservations r
            JOIN cars c ON c.id = r.car_id
            WHERE r.created_by_id=? AND c.active=1
            ORDER BY r.created_at DESC
            LIMIT 10
            """,
            (auth.user_id,),
        ).fetchall()

    if not rows:
        return ReservationPreferencesResponse(available=False, sample_size=0)

    car_counts = Counter(int(row["car_id"]) for row in rows)
    hour_counts: Counter[int] = Counter()
    duration_counts: Counter[int] = Counter()
    car_meta = {int(row["car_id"]): row for row in rows}

    for row in rows:
        start = _parse_datetime(row["start_time"])
        end = _parse_datetime(row["end_time"])
        duration = max(int((end - start).total_seconds() // 60), 15)
        hour_counts[start.hour] += 1
        duration_counts[duration] += 1

    car_id = car_counts.most_common(1)[0][0]
    car = car_meta[car_id]
    return ReservationPreferencesResponse(
        available=True,
        car_id=car_id,
        plate_number=str(car["plate_number"]),
        model=str(car["model"]),
        start_hour=hour_counts.most_common(1)[0][0],
        duration_minutes=duration_counts.most_common(1)[0][0],
        sample_size=len(rows),
    )


def _decide(
    reservation_id: int,
    new_status: str,
    auth: AuthContext,
    reason: Optional[str],
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
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

    if notification_ids:
        background_tasks.add_task(dispatch_outbound_notifications, notification_ids)
    return response


@router.post("/{reservation_id}/approve")
def approve(
    reservation_id: int,
    payload: DecisionPayload,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_approver),
) -> dict[str, Any]:
    return _decide(reservation_id, "approved", auth, payload.reason, background_tasks)


@router.post("/{reservation_id}/reject")
def reject(
    reservation_id: int,
    payload: DecisionPayload,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_approver),
) -> dict[str, Any]:
    return _decide(reservation_id, "rejected", auth, payload.reason, background_tasks)


def _bulk_decide(
    new_status: str,
    payload: BulkDecisionPayload,
    auth: AuthContext,
    background_tasks: BackgroundTasks,
) -> BulkDecisionResponse:
    """Process a batch of pending reservations in a single DB session.

    Each ID is handled independently — a conflict on one doesn't abort the
    rest. Every successful transition is logged to `audit_log`, creates an
    in-app notification for the requester, and the outbound fan-out is
    scheduled once at the end (not N times)."""
    results: list[BulkDecisionItem] = []
    notification_ids: list[int] = []
    now = _utcnow_iso()
    # De-duplicate while preserving order (admin might send `[1, 2, 1]`).
    seen: set[int] = set()
    unique_ids = [i for i in payload.ids if not (i in seen or seen.add(i))]

    with get_conn() as conn, transaction(conn):
        for reservation_id in unique_ids:
            cur = conn.execute(
                """
                UPDATE reservations
                SET status=?, decision_reason=?, decided_by_id=?, updated_at=?
                WHERE id=? AND status='pending'
                """,
                (new_status, payload.reason, auth.user_id, now, reservation_id),
            )
            if cur.rowcount == 0:
                existing = conn.execute(
                    "SELECT status FROM reservations WHERE id=?", (reservation_id,)
                ).fetchone()
                if not existing:
                    results.append(
                        BulkDecisionItem(id=reservation_id, status="skipped", error="not_found")
                    )
                else:
                    results.append(
                        BulkDecisionItem(
                            id=reservation_id,
                            status="skipped",
                            error=f"already_{existing['status']}",
                        )
                    )
                continue

            row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
            _log(conn, reservation_id, auth.user_id, new_status, payload.reason)
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
            results.append(
                BulkDecisionItem(
                    id=reservation_id,
                    status="approved" if new_status == "approved" else "rejected",
                )
            )

    if notification_ids:
        background_tasks.add_task(dispatch_outbound_notifications, notification_ids)

    succeeded = sum(1 for r in results if r.status != "skipped")
    return BulkDecisionResponse(
        results=results,
        succeeded=succeeded,
        failed=len(results) - succeeded,
    )


@router.post("/bulk-approve", response_model=BulkDecisionResponse)
def bulk_approve(
    payload: BulkDecisionPayload,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_approver),
) -> BulkDecisionResponse:
    return _bulk_decide("approved", payload, auth, background_tasks)


@router.post("/bulk-reject", response_model=BulkDecisionResponse)
def bulk_reject(
    payload: BulkDecisionPayload,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_approver),
) -> BulkDecisionResponse:
    return _bulk_decide("rejected", payload, auth, background_tasks)


def _load_reservation_for_transition(conn: DbConn, reservation_id: int) -> Any:
    row = conn.execute("SELECT * FROM reservations WHERE id=?", (reservation_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return row


@router.post("/{reservation_id}/start")
def start_trip(
    reservation_id: int,
    payload: LifecycleNotePayload,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_reception),
) -> dict[str, Any]:
    now = _utcnow_iso()
    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        row = _load_reservation_for_transition(conn, reservation_id)
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

        targets = [user_id for user_id in _active_reception_recipient_ids(conn) if user_id != auth.user_id]
        if int(row["created_by_id"]) != auth.user_id:
            targets.append(int(row["created_by_id"]))
        targets = list(dict.fromkeys(targets))
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

    if notification_ids:
        background_tasks.add_task(dispatch_outbound_notifications, notification_ids)
    return response


@router.post("/{reservation_id}/return")
def return_trip(
    reservation_id: int,
    payload: LifecycleNotePayload,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_reception),
) -> dict[str, Any]:
    now = _utcnow_iso()
    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        row = _load_reservation_for_transition(conn, reservation_id)
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

        targets = [user_id for user_id in _active_reception_recipient_ids(conn) if user_id != auth.user_id]
        if int(row["created_by_id"]) != auth.user_id:
            targets.append(int(row["created_by_id"]))
        targets = list(dict.fromkeys(targets))
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

    if notification_ids:
        background_tasks.add_task(dispatch_outbound_notifications, notification_ids)
    return response


@router.post("/{reservation_id}/cancel")
def cancel(
    reservation_id: int,
    background_tasks: BackgroundTasks,
    payload: Optional[LifecycleNotePayload] = None,
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
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
        _log(conn, reservation_id, auth.user_id, "cancelled", payload.note if payload else None)

        targets: list[int] = []
        if auth.role == "fleet_admin":
            if int(row["created_by_id"]) != auth.user_id:
                targets.append(int(row["created_by_id"]))
        else:
            targets.extend([admin_id for admin_id in _active_decision_recipient_ids(conn) if admin_id != auth.user_id])
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

    if notification_ids:
        background_tasks.add_task(dispatch_outbound_notifications, notification_ids)
    return response


@router.get("")
def list_reservations(
    car_id: Optional[int] = None,
    status_filter: Optional[ReservationStatus] = Query(default=None, alias="status_filter"),
    mine: bool = False,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    search: Optional[str] = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    auth: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    if start and end and end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")

    clauses, params = _reservation_filter_clauses(
        car_id=car_id,
        mine=mine or not is_operational_role(auth.role),
        user_id=auth.user_id,
        start=start,
        end=end,
        search=search,
    )
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT
            r.*,
            COALESCE(decider.display_name, NULL) AS decided_by_name,
            requester.gsm_number AS requester_gsm_number
        FROM reservations r
        JOIN cars c ON c.id = r.car_id
        LEFT JOIN users decider ON decider.id = r.decided_by_id
        LEFT JOIN users requester ON requester.id = r.created_by_id
        {where}
        ORDER BY r.start_time
    """

    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    items = [_serialize_reservation(row) for row in rows]
    if status_filter is not None:
        items = [item for item in items if item["status"] == status_filter]

    total = len(items)
    paged = items[offset : offset + limit]
    return {"items": paged, "total": total, "limit": limit, "offset": offset}


_CSV_COLUMNS = [
    "id",
    "car_id",
    "plate_number",
    "employee_id",
    "employee_name",
    "start_time",
    "end_time",
    "status",
    "purpose",
    "checked_out_at",
    "returned_at",
    "decision_reason",
    "decided_by_id",
    "created_at",
    "updated_at",
]


def _stream_reservations_csv(
    rows: list[Any], plates: dict[int, str]
) -> Iterator[bytes]:
    # UTF-8 BOM so Excel opens Cyrillic correctly.
    yield b"\xef\xbb\xbf"
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_COLUMNS)
    yield buffer.getvalue().encode("utf-8")
    buffer.seek(0)
    buffer.truncate()

    for row in rows:
        payload = _serialize_reservation(row)
        writer.writerow(
            [
                payload.get("id", ""),
                payload.get("car_id", ""),
                plates.get(int(payload["car_id"]), "") if payload.get("car_id") else "",
                payload.get("created_by_id", ""),
                payload.get("employee_name", "") or "",
                payload.get("start_time", "") or "",
                payload.get("end_time", "") or "",
                payload.get("status", "") or "",
                payload.get("purpose", "") or "",
                payload.get("checked_out_at", "") or "",
                payload.get("returned_at", "") or "",
                payload.get("decision_reason", "") or "",
                payload.get("decided_by_id", "") or "",
                payload.get("created_at", "") or "",
                payload.get("updated_at", "") or "",
            ]
        )
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate()


@router.get("/export.csv")
def export_reservations_csv(
    car_id: Optional[int] = None,
    status_filter: Optional[ReservationStatus] = Query(default=None, alias="status_filter"),
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    search: Optional[str] = Query(default=None, max_length=120),
    _: AuthContext = Depends(require_admin),
) -> StreamingResponse:
    """Admin-only CSV export of reservations with optional car / status / date filters."""
    if start and end and end <= start:
        raise HTTPException(status_code=400, detail="end must be after start")

    clauses, params = _reservation_filter_clauses(
        car_id=car_id,
        mine=False,
        user_id=0,
        start=start,
        end=end,
        search=search,
    )
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT r.*
        FROM reservations r
        JOIN cars c ON c.id = r.car_id
        {where}
        ORDER BY r.start_time
    """

    with get_conn() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        plate_rows = conn.execute("SELECT id, plate_number FROM cars").fetchall()

    plates = {int(row["id"]): str(row["plate_number"]) for row in plate_rows}

    if status_filter is not None:
        rows = [row for row in rows if _presentation_status(row) == status_filter]

    filename = f"reservations-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        _stream_reservations_csv(rows, plates),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
