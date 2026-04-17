from __future__ import annotations

from fastapi import APIRouter, HTTPException

from config import settings
from db import get_conn
from schemas import LoginPayload, LoginResponse
from security import issue_token, verify_password

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginPayload) -> LoginResponse:
    username = payload.username.strip().lower()
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
