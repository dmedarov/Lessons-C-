from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from config import settings
from db import get_conn
from rate_limit import RateLimitRule, client_ip, limiter
from schemas import BootstrapAdminPayload, LoginPayload, LoginResponse, SetupStatusResponse, UserResponse
from security import AuthContext, get_auth_context, hash_password, issue_token, verify_password

router = APIRouter(tags=["auth"])


def _is_integrity_error(exc: Exception) -> bool:
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    try:
        from psycopg import IntegrityError as PostgresIntegrityError
    except ImportError:
        return False
    return isinstance(exc, PostgresIntegrityError)


def _admin_exists() -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE role='fleet_admin' AND active=1 LIMIT 1"
        ).fetchone()
    return bool(row)


def _to_user_response(row) -> UserResponse:
    return UserResponse(
        id=int(row["id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]),
        role=row["role"],
        active=bool(row["active"]),
        created_at=str(row["created_at"]),
    )


@router.get("/auth/setup-status", response_model=SetupStatusResponse)
def setup_status() -> SetupStatusResponse:
    return SetupStatusResponse(has_admin=_admin_exists())


@router.post("/auth/bootstrap-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: BootstrapAdminPayload, request: Request) -> UserResponse:
    limiter.check(
        f"bootstrap:{client_ip(request)}",
        RateLimitRule(settings.bootstrap_rate_limit_attempts, settings.bootstrap_rate_limit_window_seconds),
    )
    if _admin_exists():
        raise HTTPException(status_code=409, detail="An active fleet_admin already exists")

    username = payload.username.strip().lower()
    display_name = payload.display_name.strip()
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        try:
            if conn.backend == "postgres":
                row = conn.execute(
                    """
                    INSERT INTO users(username, display_name, password_hash, role, created_at)
                    VALUES(?, ?, ?, 'fleet_admin', ?)
                    RETURNING id, username, display_name, role, active, created_at
                    """,
                    (username, display_name, hash_password(payload.password), now),
                ).fetchone()
            else:
                user_id = conn.execute(
                    """
                    INSERT INTO users(username, display_name, password_hash, role, created_at)
                    VALUES(?, ?, ?, 'fleet_admin', ?)
                    """,
                    (username, display_name, hash_password(payload.password), now),
                ).lastrowid
                row = conn.execute(
                    "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
                    (user_id,),
                ).fetchone()
        except Exception as exc:
            if _is_integrity_error(exc):
                raise HTTPException(status_code=409, detail="Username already exists") from exc
            raise

    return _to_user_response(row)


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginPayload, request: Request) -> LoginResponse:
    username = payload.username.strip().lower()
    limiter.check(
        f"login:{client_ip(request)}:{username}",
        RateLimitRule(settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds),
    )
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, display_name, password_hash, role, active FROM users WHERE username=?",
            (username,),
        ).fetchone()

    if not row or not row["active"] or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = issue_token(
        user_id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        role=row["role"],
    )
    return LoginResponse(
        access_token=token,
        user=row["display_name"],
        role=row["role"],
        expires_in=settings.token_ttl_seconds,
    )


@router.get("/auth/me", response_model=UserResponse)
def me(auth: AuthContext = Depends(get_auth_context)) -> UserResponse:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, display_name, role, active, created_at FROM users WHERE id=?",
            (auth.user_id,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_user_response(row)
