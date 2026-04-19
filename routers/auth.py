from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status

import bootstrap_tokens
from config import settings
from db import get_conn, transaction
from rate_limit import RateLimitRule, client_ip, limiter
from schemas import BootstrapAdminPayload, LoginPayload, LoginResponse, SetupStatusResponse, UserResponse
from security import AuthContext, get_auth_context, hash_password, issue_token, verify_password

router = APIRouter(tags=["auth"])

REFRESH_COOKIE_NAME = "fleetflow_refresh"


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


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _refresh_cookie_secure() -> bool:
    return settings.app_env != "dev"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        token,
        max_age=settings.refresh_token_ttl_seconds,
        httponly=True,
        secure=_refresh_cookie_secure(),
        samesite="strict",
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/", samesite="strict")


def _issue_access_token(row) -> str:
    return issue_token(
        user_id=int(row["id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]),
        role=row["role"],
    )


def _store_refresh_token(user_id: int, request: Request) -> str:
    token = _new_refresh_token()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
    user_agent = request.headers.get("user-agent")
    ip = client_ip(request)

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO refresh_tokens(user_id, token_hash, issued_at, expires_at, user_agent, ip)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (user_id, _hash_refresh_token(token), now.isoformat(), expires_at.isoformat(), user_agent, ip),
        )
    return token


def _revoke_refresh_hash(token_hash: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE refresh_tokens SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
            (now, token_hash),
        )


def _revoke_active_refresh_tokens_for_user(conn, user_id: int, revoked_at: str) -> None:
    conn.execute(
        "UPDATE refresh_tokens SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
        (revoked_at, user_id),
    )


def _rotate_refresh_token(raw_token: str, request: Request) -> tuple[dict, str]:
    token_hash = _hash_refresh_token(raw_token)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    error_detail: str | None = None
    user_row = None
    new_token = ""

    with get_conn() as conn:
        with transaction(conn):
            row = conn.execute(
                """
                SELECT
                    rt.id,
                    rt.user_id,
                    rt.expires_at,
                    rt.revoked_at,
                    u.username,
                    u.display_name,
                    u.role,
                    u.active
                FROM refresh_tokens rt
                JOIN users u ON u.id = rt.user_id
                WHERE rt.token_hash=?
                """,
                (token_hash,),
            ).fetchone()

            if not row:
                error_detail = "Invalid refresh token"
            elif row["revoked_at"] or str(row["expires_at"]) <= now_iso:
                # Replay protection: using an already-rotated token invalidates
                # the remaining refresh tokens for the same user.
                _revoke_active_refresh_tokens_for_user(conn, row["user_id"], now_iso)
                error_detail = "Refresh token expired or revoked"
            elif not row["active"]:
                _revoke_active_refresh_tokens_for_user(conn, row["user_id"], now_iso)
                error_detail = "User is inactive or no longer exists"
            else:
                updated = conn.execute(
                    "UPDATE refresh_tokens SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
                    (now_iso, row["id"]),
                )
                if updated.rowcount != 1:
                    _revoke_active_refresh_tokens_for_user(conn, row["user_id"], now_iso)
                    error_detail = "Refresh token expired or revoked"
                else:
                    new_token = _new_refresh_token()
                    expires_at = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
                    user_agent = request.headers.get("user-agent")
                    ip = client_ip(request)
                    conn.execute(
                        """
                        INSERT INTO refresh_tokens(user_id, token_hash, issued_at, expires_at, user_agent, ip)
                        VALUES(?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row["user_id"],
                            _hash_refresh_token(new_token),
                            now_iso,
                            expires_at.isoformat(),
                            user_agent,
                            ip,
                        ),
                    )
                    user_row = row

    if error_detail:
        raise HTTPException(status_code=401, detail=error_detail)
    if user_row is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return user_row, new_token


@router.get("/auth/setup-status", response_model=SetupStatusResponse)
def setup_status() -> SetupStatusResponse:
    return SetupStatusResponse(has_admin=_admin_exists())


@router.post("/auth/bootstrap-admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(
    payload: BootstrapAdminPayload,
    request: Request,
    x_bootstrap_token: Optional[str] = Header(default=None, alias="X-Bootstrap-Token"),
) -> UserResponse:
    limiter.check(
        f"bootstrap:{client_ip(request)}",
        RateLimitRule(settings.bootstrap_rate_limit_attempts, settings.bootstrap_rate_limit_window_seconds),
    )
    # In production, gate the endpoint behind a one-shot token logged at
    # startup. Dev stays permissive so the local smoke flow is unchanged.
    if bootstrap_tokens.is_enforced():
        bootstrap_tokens.verify_and_consume(x_bootstrap_token)
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

    # Success — drop the one-shot token so a second call can't reuse it via a
    # race. `verify_and_consume` already marked it consumed, but clearing the
    # record turns a subtle 403 into a clean "no token provisioned" state.
    if bootstrap_tokens.is_enforced():
        bootstrap_tokens.clear()
    return _to_user_response(row)


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginPayload, request: Request, response: Response) -> LoginResponse:
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

    token = _issue_access_token(row)
    refresh_token = _store_refresh_token(int(row["id"]), request)
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(
        access_token=token,
        user=row["display_name"],
        role=row["role"],
        expires_in=settings.token_ttl_seconds,
    )


@router.post("/auth/refresh", response_model=LoginResponse)
def refresh_session(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> LoginResponse:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    row, new_refresh_token = _rotate_refresh_token(refresh_token, request)
    _set_refresh_cookie(response, new_refresh_token)
    token = _issue_access_token(row)
    return LoginResponse(
        access_token=token,
        user=row["display_name"],
        role=row["role"],
        expires_in=settings.token_ttl_seconds,
    )


@router.post("/auth/logout")
def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> dict[str, str]:
    if refresh_token:
        _revoke_refresh_hash(_hash_refresh_token(refresh_token))
    _clear_refresh_cookie(response)
    return {"status": "ok"}


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
