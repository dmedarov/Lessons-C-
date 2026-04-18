from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from db import get_conn
from schemas import NotificationResponse
from security import AuthContext, get_auth_context

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_notification(row) -> NotificationResponse:
    return NotificationResponse(
        id=int(row["id"]),
        kind=str(row["kind"]),
        title=str(row["title"]),
        body=str(row["body"]),
        reservation_id=row["reservation_id"],
        read_at=row["read_at"],
        created_at=str(row["created_at"]),
    )


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=200),
    auth: AuthContext = Depends(get_auth_context),
) -> list[NotificationResponse]:
    where = "user_id=?"
    params: list = [auth.user_id]
    if unread_only:
        where += " AND read_at IS NULL"
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM notifications WHERE {where} ORDER BY id DESC LIMIT ?",
            tuple([*params, limit]),
        ).fetchall()
    return [_to_notification(row) for row in rows]


@router.post("/read-all")
def read_all_notifications(auth: AuthContext = Depends(get_auth_context)) -> dict[str, int]:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE user_id=? AND read_at IS NULL",
            (auth.user_id,),
        )
    return {"updated": cur.rowcount}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def read_notification(notification_id: int, auth: AuthContext = Depends(get_auth_context)) -> NotificationResponse:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE id=? AND user_id=?",
            (notification_id, auth.user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")

        conn.execute(
            "UPDATE notifications SET read_at=CURRENT_TIMESTAMP WHERE id=?",
            (notification_id,),
        )
        updated = conn.execute(
            "SELECT * FROM notifications WHERE id=? AND user_id=?",
            (notification_id, auth.user_id),
        ).fetchone()
    return _to_notification(updated)
