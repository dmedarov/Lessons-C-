from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict

from config import settings
from db import get_conn

NETFLEET_API_KEY_SETTING = "netfleet_api_key"


class NetFleetConfigStatus(TypedDict):
    configured: bool
    source: Literal["database", "environment", "none"]
    updated_at: str | None
    updated_by_id: int | None


def _netfleet_setting_row() -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT setting_value, updated_at, updated_by_id
            FROM app_settings
            WHERE setting_key=?
            """,
            (NETFLEET_API_KEY_SETTING,),
        ).fetchone()
    return dict(row) if row else None


def get_netfleet_api_key() -> str | None:
    row = _netfleet_setting_row()
    if row and str(row["setting_value"]).strip():
        return str(row["setting_value"]).strip()
    return settings.netfleet_api_key


def get_netfleet_config_status() -> NetFleetConfigStatus:
    row = _netfleet_setting_row()
    if row and str(row["setting_value"]).strip():
        return {
            "configured": True,
            "source": "database",
            "updated_at": row["updated_at"],
            "updated_by_id": int(row["updated_by_id"]) if row["updated_by_id"] is not None else None,
        }
    if settings.netfleet_api_key:
        return {
            "configured": True,
            "source": "environment",
            "updated_at": None,
            "updated_by_id": None,
        }
    return {
        "configured": False,
        "source": "none",
        "updated_at": None,
        "updated_by_id": None,
    }


def set_netfleet_api_key(api_key: str, actor_id: int) -> NetFleetConfigStatus:
    value = api_key.strip()
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT setting_key FROM app_settings WHERE setting_key=?",
            (NETFLEET_API_KEY_SETTING,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE app_settings
                SET setting_value=?, updated_at=?, updated_by_id=?
                WHERE setting_key=?
                """,
                (value, now, actor_id, NETFLEET_API_KEY_SETTING),
            )
        else:
            conn.execute(
                """
                INSERT INTO app_settings(setting_key, setting_value, updated_at, updated_by_id)
                VALUES(?, ?, ?, ?)
                """,
                (NETFLEET_API_KEY_SETTING, value, now, actor_id),
            )
    return get_netfleet_config_status()
