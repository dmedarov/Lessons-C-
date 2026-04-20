from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from config import settings


@dataclass(frozen=True)
class NetFleetTelemetry:
    configured: bool
    items: list[dict[str, Any]]


def _normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    plate = str(event.get("plateNumber") or "").strip().upper()
    return {
        "device_id": event.get("deviceId"),
        "plate_number": plate,
        "latitude": event.get("latitude"),
        "longitude": event.get("longitude"),
        "speed": event.get("speed"),
        "azimuth": event.get("azimuth"),
        "altitude": event.get("altitude"),
        "power_voltage": event.get("powerVoltage"),
        "satellites": event.get("satellites"),
        "utc_time": event.get("utcTime"),
        "current_mileage": event.get("currentMileage"),
        "current_work_hours": event.get("currentWorkHours"),
    }


def fetch_latest_gps_events(api_key: str | None = None) -> NetFleetTelemetry:
    effective_api_key = api_key or settings.netfleet_api_key
    if not effective_api_key:
        return NetFleetTelemetry(configured=False, items=[])

    url = f"{settings.netfleet_base_url.rstrip('/')}/api/company/latest-gps-events"
    request = urllib.request.Request(
        url,
        headers={
            "api-key": effective_api_key,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.netfleet_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError("NetFleet telemetry request failed") from exc

    if not isinstance(payload, list):
        raise RuntimeError("NetFleet telemetry response is not a list")

    return NetFleetTelemetry(
        configured=True,
        items=[_normalize_event(item) for item in payload if isinstance(item, dict)],
    )
