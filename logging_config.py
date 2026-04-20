from __future__ import annotations

import json
import logging
import sys
from typing import Any

ACCESS_LOGGER_NAME = "fleetflow.access"
_ACCESS_HANDLER_MARKER = "_fleetflow_access_handler"


def configure_access_logger() -> None:
    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if any(getattr(handler, _ACCESS_HANDLER_MARKER, False) for handler in logger.handlers):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    setattr(handler, _ACCESS_HANDLER_MARKER, True)
    logger.addHandler(handler)


def use_json_logs(app_env: str, log_format: str) -> bool:
    selected = log_format.strip().lower()
    if selected == "json":
        return True
    if selected == "text":
        return False
    return app_env != "dev"


def build_access_log(
    *,
    request_id: str,
    method: str,
    path: str,
    route: str,
    status_code: int,
    latency_ms: float,
    app_env: str,
    client_host: str | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event": "http_request",
        "request_id": request_id,
        "method": method,
        "path": path,
        "route": route,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "app_env": app_env,
    }
    if client_host:
        event["client_host"] = client_host
    return event


def format_access_log(event: dict[str, Any], *, json_logs: bool) -> str:
    if json_logs:
        return json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return (
        "http_request "
        f"request_id={event['request_id']} "
        f"method={event['method']} "
        f"path={event['path']} "
        f"route={event['route']} "
        f"status={event['status_code']} "
        f"latency_ms={event['latency_ms']}"
    )


def emit_access_log(event: dict[str, Any], *, app_env: str, log_format: str) -> None:
    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    logger.info(format_access_log(event, json_logs=use_json_logs(app_env, log_format)))
