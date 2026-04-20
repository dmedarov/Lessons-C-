from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any


def fetch_json(base_url: str, path: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{path} is not reachable: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path} did not return JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} returned unexpected JSON")
    return data


def main() -> int:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
    checks = [
        ("/health", lambda data: data.get("status") == "ok", "health is not ok"),
        ("/health/ready", lambda data: data.get("status") == "ready", "readiness is not ready"),
        ("/auth/setup-status", lambda data: data.get("has_admin") is True, "no active admin exists"),
        (
            "/public/overview",
            lambda data: {"active_cars", "pending_requests", "active_trips", "available_cars"} <= set(data),
            "public overview is incomplete",
        ),
    ]

    for path, predicate, message in checks:
        data = fetch_json(base_url, path)
        if not predicate(data):
            print(f"ERROR: {path}: {message}")
            return 1
        print(f"OK: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
