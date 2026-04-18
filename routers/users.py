from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from db import get_conn, transaction
from notifications_service import create_notification, dispatch_outbound_notifications
from schemas import AdminHandoffPayload, AdminHandoffResponse, PasswordChangePayload, UserCreatePayload, UserResponse
from security import AuthContext, get_auth_context, hash_password, require_admin, verify_password

router = APIRouter(prefix="/users", tags=["users"])


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


@router.get("", response_model=list[UserResponse])
def list_users(_: AuthContext = Depends(require_admin)) -> list[UserResponse]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, display_name, role, active, created_at FROM users ORDER BY id"
        ).fetchall()
    return [_to_user_response(row) for row in rows]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreatePayload, auth: AuthContext = Depends(require_admin)) -> UserResponse:
    username = payload.username.strip().lower()
    display_name = payload.display_name.strip()
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        try:
            if conn.backend == "postgres":
                row = conn.execute(
                    """
                    INSERT INTO users(username, display_name, password_hash, role, created_at)
                    VALUES(?, ?, ?, ?, ?)
                    RETURNING id, username, display_name, role, active, created_at
                    """,
                    (username, display_name, hash_password(payload.password), payload.role, now),
                ).fetchone()
            else:
                user_id = conn.execute(
                    """
                    INSERT INTO users(username, display_name, password_hash, role, created_at)
                    VALUES(?, ?, ?, ?, ?)
                    """,
                    (username, display_name, hash_password(payload.password), payload.role, now),
                ).lastrowid
                row = conn.execute(
                    "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
                    (user_id,),
                ).fetchone()
        except Exception as exc:
            if _is_integrity_error(exc):
                raise HTTPException(status_code=409, detail="Username already exists") from exc
            raise
        _log_user_action(conn, auth.user_id, int(row["id"]), "created", f"role={payload.role}")

    return _to_user_response(row)


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


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(user_id: int, auth: AuthContext = Depends(require_admin)) -> UserResponse:
    if user_id == auth.user_id:
        admins = 0
        with get_conn() as conn:
            admins = conn.execute(
                "SELECT COUNT(*) AS n FROM users WHERE role='fleet_admin' AND active=1"
            ).fetchone()["n"]
        if admins <= 1:
            raise HTTPException(status_code=409, detail="Cannot deactivate the last active fleet_admin")

    with get_conn() as conn:
        cur = conn.execute("UPDATE users SET active=0 WHERE id=? AND active=1", (user_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found or already inactive")
        row = conn.execute(
            "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
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
            "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        _log_user_action(conn, auth.user_id, user_id, "activated", None)
    return _to_user_response(row)


@router.post("/{user_id}/handoff-admin", response_model=AdminHandoffResponse)
def handoff_admin(
    user_id: int,
    payload: AdminHandoffPayload,
    auth: AuthContext = Depends(require_admin),
) -> AdminHandoffResponse:
    if user_id == auth.user_id:
        raise HTTPException(status_code=409, detail="Choose another active user for admin handoff")

    notification_ids: list[int] = []
    with get_conn() as conn, transaction(conn):
        current_admin = conn.execute(
            "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
            (auth.user_id,),
        ).fetchone()
        target = conn.execute(
            "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
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
            "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
            (auth.user_id,),
        ).fetchone()
        updated_target = conn.execute(
            "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
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

    dispatch_outbound_notifications(notification_ids)
    return response
