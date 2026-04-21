from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status

from db import get_conn, transaction
from notifications_service import create_notification, dispatch_outbound_notifications
from schemas import (
    AdminHandoffPayload,
    AdminHandoffResponse,
    AdminPasswordResetPayload,
    EmployeeImportItem,
    EmployeeImportPayload,
    EmployeeImportResponse,
    PasswordChangePayload,
    UserContactUpdatePayload,
    UserAuditResponse,
    UserCreatePayload,
    UserResponse,
    UserRoleChangePayload,
)
from security import AuthContext, get_auth_context, hash_password, require_admin, verify_password

router = APIRouter(prefix="/users", tags=["users"])

_TRANSLITERATION = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sht",
        "ъ": "a",
        "ь": "y",
        "ю": "yu",
        "я": "ya",
    }
)


def _employee_username(display_name: str) -> str:
    lowered = display_name.lower().translate(_TRANSLITERATION)
    slug = re.sub(r"[^a-z0-9]+", ".", lowered).strip(".")
    return slug[:64].strip(".") or "employee"


def _unique_username(conn, base: str, current_id: int | None = None) -> str:
    username = base if len(base) >= 3 else f"{base}.user"
    username = username[:64].strip(".")
    suffix = 2
    while True:
        row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not row or int(row["id"]) == current_id:
            return username
        tail = f".{suffix}"
        username = f"{base[:64 - len(tail)].strip('.')}{tail}"
        suffix += 1


def _parse_employee_import_rows(text: str) -> tuple[list[dict[str, str | None]], list[str]]:
    rows: list[dict[str, str | None]] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = [part.strip() for part in (raw.split("\t") if "\t" in raw else re.split(r";|,", raw))]
        lowered = raw.lower()
        if "име" in lowered and ("фамилия" in lowered or "телефон" in lowered):
            continue

        first = last = gsm_number = ""
        if len(parts) >= 4:
            first = parts[0]
            last = parts[2] or parts[1]
            gsm_number = parts[3]
        else:
            tokens = raw.split()
            if len(tokens) >= 2:
                if tokens[-1].startswith("+") or tokens[-1].replace(" ", "").isdigit():
                    gsm_number = tokens[-1]
                    tokens = tokens[:-1]
                first = tokens[0]
                last = tokens[-1] if len(tokens) > 1 else ""

        if not first or not last:
            skipped.append(raw)
            continue
        display_name = f"{first} {last}".strip()
        key = display_name.casefold()
        if key in seen:
            skipped.append(f"{display_name} duplicate")
            continue
        seen.add(key)
        if len(display_name) > 120 or len(gsm_number) > 32:
            skipped.append(display_name)
            continue
        rows.append({"display_name": display_name, "gsm_number": gsm_number or None})
    return rows, skipped


def _is_integrity_error(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    try:
        from psycopg import IntegrityError as PostgresIntegrityError
    except ImportError:
        return False
    return isinstance(exc, PostgresIntegrityError)


def _to_user_response(row) -> UserResponse:
    return UserResponse(
        id=int(row["id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]),
        role=row["role"],
        active=bool(row["active"]),
        email=row["email"] or None,
        gsm_number=row["gsm_number"] or None,
        created_at=str(row["created_at"]),
    )


def _log_user_action(conn, actor_id: int, target_user_id: int, action: str, reason: str | None) -> None:
    conn.execute(
        """
        INSERT INTO user_audit_log(actor_id, target_user_id, action, reason, at)
        VALUES(?, ?, ?, ?, ?)
        """,
        (actor_id, target_user_id, action, reason, datetime.now(timezone.utc).isoformat()),
    )


def _active_admin_count(conn) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role='fleet_admin' AND active=1"
        ).fetchone()["n"]
    )


def _load_user(conn, user_id: int):
    row = conn.execute(
        "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return row


@router.get("", response_model=list[UserResponse])
def list_users(_: AuthContext = Depends(require_admin)) -> list[UserResponse]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users ORDER BY id"
        ).fetchall()
    return [_to_user_response(row) for row in rows]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreatePayload, auth: AuthContext = Depends(require_admin)) -> UserResponse:
    username = payload.username.strip().lower()
    display_name = payload.display_name.strip()
    email = payload.email.strip() if payload.email else None
    gsm_number = payload.gsm_number.strip() if payload.gsm_number else None
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        try:
            if conn.backend == "postgres":
                row = conn.execute(
                    """
                    INSERT INTO users(username, display_name, password_hash, role, email, gsm_number, created_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    RETURNING id, username, display_name, role, active, email, gsm_number, created_at
                    """,
                    (username, display_name, hash_password(payload.password), payload.role, email, gsm_number, now),
                ).fetchone()
            else:
                user_id = conn.execute(
                    """
                    INSERT INTO users(username, display_name, password_hash, role, email, gsm_number, created_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?)
                    """,
                    (username, display_name, hash_password(payload.password), payload.role, email, gsm_number, now),
                ).lastrowid
                row = conn.execute(
                    "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
                    (user_id,),
                ).fetchone()
        except Exception as exc:
            if _is_integrity_error(exc):
                raise HTTPException(status_code=409, detail="Username already exists") from exc
            raise
        _log_user_action(conn, auth.user_id, int(row["id"]), "created", f"role={payload.role}")

    return _to_user_response(row)


@router.post("/import-employees", response_model=EmployeeImportResponse)
def import_employees(payload: EmployeeImportPayload, auth: AuthContext = Depends(require_admin)) -> EmployeeImportResponse:
    rows, skipped_rows = _parse_employee_import_rows(payload.text)
    imported: list[EmployeeImportItem] = []
    created = 0
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    with get_conn() as conn, transaction(conn):
        for item in rows:
            display_name = str(item["display_name"])
            gsm_number = item["gsm_number"]
            base_username = _employee_username(display_name)
            current = conn.execute(
                """
                SELECT id, username, display_name, role, active, email, gsm_number, created_at
                FROM users
                WHERE display_name=? OR username=?
                ORDER BY CASE WHEN display_name=? THEN 0 ELSE 1 END, id
                LIMIT 1
                """,
                (display_name, base_username, display_name),
            ).fetchone()

            if current:
                user_id = int(current["id"])
                username = _unique_username(conn, base_username, user_id)
                if payload.reset_existing_passwords:
                    conn.execute(
                        """
                        UPDATE users
                        SET username=?, display_name=?, password_hash=?, role='employee', active=1, gsm_number=?
                        WHERE id=?
                        """,
                        (username, display_name, hash_password(payload.password), gsm_number, user_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE users
                        SET username=?, display_name=?, role='employee', active=1, gsm_number=?
                        WHERE id=?
                        """,
                        (username, display_name, gsm_number, user_id),
                    )
                _log_user_action(conn, auth.user_id, user_id, "employee_import_updated", "bulk employee import")
                action = "updated"
                updated += 1
            else:
                username = _unique_username(conn, base_username)
                if conn.backend == "postgres":
                    inserted = conn.execute(
                        """
                        INSERT INTO users(username, display_name, password_hash, role, active, email, gsm_number, created_at)
                        VALUES(?, ?, ?, 'employee', 1, NULL, ?, ?)
                        RETURNING id
                        """,
                        (username, display_name, hash_password(payload.password), gsm_number, now),
                    ).fetchone()
                    user_id = int(inserted["id"])
                else:
                    user_id = int(
                        conn.execute(
                            """
                            INSERT INTO users(username, display_name, password_hash, role, active, email, gsm_number, created_at)
                            VALUES(?, ?, ?, 'employee', 1, NULL, ?, ?)
                            """,
                            (username, display_name, hash_password(payload.password), gsm_number, now),
                        ).lastrowid
                    )
                _log_user_action(conn, auth.user_id, user_id, "employee_import_created", "bulk employee import")
                action = "created"
                created += 1

            row = _load_user(conn, user_id)
            imported.append(
                EmployeeImportItem(
                    id=int(row["id"]),
                    username=str(row["username"]),
                    display_name=str(row["display_name"]),
                    gsm_number=row["gsm_number"] or None,
                    action=action,
                )
            )

    return EmployeeImportResponse(
        created=created,
        updated=updated,
        skipped=len(skipped_rows),
        skipped_rows=skipped_rows,
        items=imported,
    )


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def change_my_password(payload: PasswordChangePayload, auth: AuthContext = Depends(get_auth_context)):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id=?",
            (auth.user_id,),
        ).fetchone()
        if not row or not verify_password(payload.current_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password is invalid")

        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(payload.new_password), auth.user_id),
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{user_id}/contact", response_model=UserResponse)
def update_user_contact(
    user_id: int,
    payload: UserContactUpdatePayload,
    auth: AuthContext = Depends(require_admin),
) -> UserResponse:
    email = payload.email.strip() if payload.email else None
    gsm_number = payload.gsm_number.strip() if payload.gsm_number else None
    reason = payload.reason.strip() if payload.reason else None

    with get_conn() as conn, transaction(conn):
        _load_user(conn, user_id)
        conn.execute(
            "UPDATE users SET email=?, gsm_number=? WHERE id=?",
            (email, gsm_number, user_id),
        )
        _log_user_action(conn, auth.user_id, user_id, "contact_updated", reason or "contact update")
        updated = _load_user(conn, user_id)

    return _to_user_response(updated)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def reset_user_password(
    user_id: int,
    payload: AdminPasswordResetPayload,
    auth: AuthContext = Depends(require_admin),
) -> Response:
    with get_conn() as conn, transaction(conn):
        target = _load_user(conn, user_id)
        if not target["active"]:
            raise HTTPException(status_code=409, detail="Cannot reset password for an inactive user")

        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(payload.new_password), user_id),
        )
        _log_user_action(conn, auth.user_id, user_id, "password_reset", payload.reason)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    payload: UserRoleChangePayload,
    auth: AuthContext = Depends(require_admin),
) -> UserResponse:
    with get_conn() as conn, transaction(conn):
        target = _load_user(conn, user_id)
        old_role = str(target["role"])
        if old_role == payload.role:
            return _to_user_response(target)

        if old_role == "fleet_admin" and payload.role != "fleet_admin" and target["active"] and _active_admin_count(conn) <= 1:
            raise HTTPException(status_code=409, detail="Cannot demote the last active fleet_admin")

        conn.execute("UPDATE users SET role=? WHERE id=?", (payload.role, user_id))
        _log_user_action(
            conn,
            auth.user_id,
            user_id,
            "role_changed",
            payload.reason or f"{old_role}->{payload.role}",
        )
        updated = _load_user(conn, user_id)

    return _to_user_response(updated)


@router.get("/{user_id}/audit", response_model=list[UserAuditResponse])
def user_audit(
    user_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: AuthContext = Depends(require_admin),
) -> list[UserAuditResponse]:
    with get_conn() as conn:
        _load_user(conn, user_id)
        rows = conn.execute(
            """
            SELECT
                log.id,
                log.actor_id,
                COALESCE(actor.display_name, 'Unknown actor') AS actor_display_name,
                log.target_user_id,
                log.action,
                log.reason,
                log.at
            FROM user_audit_log log
            LEFT JOIN users actor ON actor.id = log.actor_id
            WHERE log.target_user_id=?
            ORDER BY log.at DESC, log.id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset),
        ).fetchall()

    return [
        UserAuditResponse(
            id=int(row["id"]),
            actor_id=int(row["actor_id"]),
            actor_display_name=str(row["actor_display_name"]),
            target_user_id=int(row["target_user_id"]),
            action=str(row["action"]),
            reason=row["reason"],
            at=str(row["at"]),
        )
        for row in rows
    ]


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: int, auth: AuthContext = Depends(require_admin)) -> UserResponse:
    if user_id == auth.user_id:
        with get_conn() as conn:
            if _active_admin_count(conn) <= 1:
                raise HTTPException(status_code=409, detail="Cannot deactivate the last active fleet_admin")
    else:
        with get_conn() as conn:
            target = conn.execute("SELECT role, active FROM users WHERE id=?", (user_id,)).fetchone()
            if target and target["role"] == "fleet_admin" and target["active"] and _active_admin_count(conn) <= 1:
                raise HTTPException(status_code=409, detail="Cannot deactivate the last active fleet_admin")

    with get_conn() as conn:
        cur = conn.execute("UPDATE users SET active=0 WHERE id=? AND active=1", (user_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found or already inactive")
        row = conn.execute(
            "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        _log_user_action(conn, auth.user_id, user_id, "deactivated", None)
    return _to_user_response(row)


@router.post("/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: int, auth: AuthContext = Depends(require_admin)) -> UserResponse:
    with get_conn() as conn:
        cur = conn.execute("UPDATE users SET active=1 WHERE id=? AND active=0", (user_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found or already active")
        row = conn.execute(
            "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        _log_user_action(conn, auth.user_id, user_id, "activated", None)
    return _to_user_response(row)


@router.post("/{user_id}/handoff-admin", response_model=AdminHandoffResponse)
def handoff_admin(
    user_id: int,
    payload: AdminHandoffPayload,
    background_tasks: BackgroundTasks,
    auth: AuthContext = Depends(require_admin),
) -> AdminHandoffResponse:
    if user_id == auth.user_id:
        raise HTTPException(status_code=409, detail="Choose another active user for admin handoff")

    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        current_admin = conn.execute(
            "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
            (auth.user_id,),
        ).fetchone()
        target = conn.execute(
            "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Target user not found")
        if not target["active"]:
            raise HTTPException(status_code=409, detail="Target user must be active for admin handoff")

        if target["role"] != "fleet_admin":
            conn.execute("UPDATE users SET role='fleet_admin' WHERE id=?", (user_id,))
        if payload.demote_self:
            conn.execute("UPDATE users SET role='employee' WHERE id=?", (auth.user_id,))

        updated_previous = conn.execute(
            "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
            (auth.user_id,),
        ).fetchone()
        updated_target = conn.execute(
            "SELECT id, username, display_name, role, active, email, gsm_number, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()

        _log_user_action(
            conn,
            auth.user_id,
            user_id,
            "handoff_admin",
            payload.reason or ("demote_self=true" if payload.demote_self else "demote_self=false"),
        )
        notification_ids.append(
            create_notification(
                conn,
                user_id=user_id,
                kind="admin_handoff",
                title="Получи административен достъп",
                body=f"{auth.display_name} ти прехвърли admin отговорността.",
            )
        )
        response = AdminHandoffResponse(
            previous_admin=_to_user_response(updated_previous),
            next_admin=_to_user_response(updated_target),
            demote_self=payload.demote_self,
        )

    if notification_ids:
        background_tasks.add_task(dispatch_outbound_notifications, notification_ids)
    return response
