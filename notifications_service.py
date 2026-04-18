from __future__ import annotations

import json
import smtplib
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Optional

from config import settings
from db import get_conn


@dataclass(frozen=True)
class NotificationEnvelope:
    notification_id: int
    kind: str
    title: str
    body: str
    created_at: str
    reservation_id: int | None
    username: str
    display_name: str


def create_notification(
    conn,
    *,
    user_id: int,
    kind: str,
    title: str,
    body: str,
    reservation_id: int | None = None,
) -> int:
    result = conn.execute(
        """
        INSERT INTO notifications(user_id, kind, title, body, reservation_id, created_at)
        VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (user_id, kind, title, body, reservation_id),
    )
    if conn.backend == "postgres":
        row = conn.execute(
            """
            SELECT id
            FROM notifications
            WHERE user_id=? AND kind=? AND title=? AND body=? AND reservation_id IS NOT DISTINCT FROM ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, kind, title, body, reservation_id),
        ).fetchone()
        return int(row["id"])
    return int(result.lastrowid)


def create_notifications(
    conn,
    user_ids: list[int],
    *,
    kind: str,
    title: str,
    body: str,
    reservation_id: int | None = None,
) -> list[int]:
    notification_ids: list[int] = []
    for user_id in sorted(set(user_ids)):
        notification_ids.append(
            create_notification(
                conn,
                user_id=user_id,
                kind=kind,
                title=title,
                body=body,
                reservation_id=reservation_id,
            )
        )
    return notification_ids


def _load_notification(notification_id: int) -> NotificationEnvelope | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT n.id, n.kind, n.title, n.body, n.created_at, n.reservation_id,
                   u.username, u.display_name
            FROM notifications n
            JOIN users u ON u.id = n.user_id
            WHERE n.id=?
            """,
            (notification_id,),
        ).fetchone()
    if not row:
        return None
    return NotificationEnvelope(
        notification_id=int(row["id"]),
        kind=str(row["kind"]),
        title=str(row["title"]),
        body=str(row["body"]),
        created_at=str(row["created_at"]),
        reservation_id=row["reservation_id"],
        username=str(row["username"]),
        display_name=str(row["display_name"]),
    )


def _log_delivery(notification_id: int, channel: str, status: str, detail: Optional[str]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO notification_deliveries(notification_id, channel, status, detail, delivered_at)
            VALUES(?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (notification_id, channel, status, detail),
        )


def _post_json(url: str, payload: dict[str, Any]) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=settings.notification_timeout_seconds) as response:
        status_code = getattr(response, "status", 200)
        if status_code >= 400:
            raise RuntimeError(f"HTTP {status_code}")


def _send_slack(envelope: NotificationEnvelope) -> None:
    if not settings.slack_webhook_url:
        return
    _post_json(
        settings.slack_webhook_url,
        {
            "text": f"{envelope.title}\n{envelope.body}\nUser: {envelope.display_name}",
        },
    )


def _send_teams(envelope: NotificationEnvelope) -> None:
    if not settings.teams_webhook_url:
        return
    facts = [{"name": "User", "value": envelope.display_name}]
    if envelope.reservation_id is not None:
        facts.append({"name": "Reservation", "value": f"#{envelope.reservation_id}"})
    _post_json(
        settings.teams_webhook_url,
        {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": envelope.title,
            "themeColor": "2563EB",
            "title": envelope.title,
            "sections": [{"text": envelope.body, "facts": facts}],
        },
    )


def _send_email(envelope: NotificationEnvelope) -> None:
    if not settings.smtp_host or not settings.smtp_from_email or not settings.smtp_to_email:
        return

    message = EmailMessage()
    message["Subject"] = f"[FleetFlow] {envelope.title}"
    message["From"] = settings.smtp_from_email
    message["To"] = settings.smtp_to_email
    message.set_content(
        "\n".join(
            [
                envelope.title,
                "",
                envelope.body,
                "",
                f"User: {envelope.display_name} ({envelope.username})",
                f"Notification ID: {envelope.notification_id}",
                f"Created at: {envelope.created_at}",
            ]
        )
    )

    timeout = settings.notification_timeout_seconds
    if settings.smtp_use_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout) as server:
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)


def dispatch_outbound_notifications(notification_ids: list[int]) -> None:
    for notification_id in notification_ids:
        envelope = _load_notification(notification_id)
        if not envelope:
            continue

        for channel, handler, configured in [
            ("email", _send_email, bool(settings.smtp_host and settings.smtp_from_email and settings.smtp_to_email)),
            ("slack", _send_slack, bool(settings.slack_webhook_url)),
            ("teams", _send_teams, bool(settings.teams_webhook_url)),
        ]:
            if not configured:
                continue
            try:
                handler(envelope)
            except (OSError, smtplib.SMTPException, urllib.error.URLError, RuntimeError) as exc:
                _log_delivery(notification_id, channel, "failed", str(exc))
            else:
                _log_delivery(notification_id, channel, "sent", None)
