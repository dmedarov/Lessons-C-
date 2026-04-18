from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from db import get_conn, transaction
from notifications_service import create_notification, dispatch_outbound_notifications
from schemas import (
    AdminHandoffPayload,
    AdminHandoffResponse,
    AdminPasswordResetPayload,
    PasswordChangePayload,
    UserAuditResponse,
    UserCreatePayload,
    UserResponse,
    UserRoleChangePayload,
)
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


def _active_admin_count(conn) -> int:
    return int(
        conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role='fleet_admin' AND active=1"
        ).fetchone()["n"]
    )


def _load_user(conn, user_id: int):
    row = conn.execute(
        "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return row


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
