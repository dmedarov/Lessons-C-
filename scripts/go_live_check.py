from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production_readiness import error_messages, evaluate_env_readiness, load_env, warning_messages  # noqa: E402

DEFAULT_MARKER_PATH = Path(".fleetflow/restore-drill-ok.json")
DEFAULT_RESTORE_DRILL_MAX_AGE_HOURS = 168


def _parse_utc_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _int_from_env(env: dict[str, str], key: str, default: int) -> int:
    raw = os.getenv(key, env.get(key, str(default)))
    try:
        return int(raw)
    except ValueError:
        return default


def _marker_path(env: dict[str, str]) -> Path:
    raw = os.getenv("RESTORE_DRILL_MARKER", env.get("RESTORE_DRILL_MARKER", str(DEFAULT_MARKER_PATH)))
    return Path(raw)


def restore_drill_messages(env: dict[str, str], *, now: datetime | None = None) -> tuple[list[str], list[str]]:
    now = now or datetime.now(timezone.utc)
    marker_path = _marker_path(env)
    max_age_hours = _int_from_env(env, "RESTORE_DRILL_MAX_AGE_HOURS", DEFAULT_RESTORE_DRILL_MAX_AGE_HOURS)
    errors: list[str] = []
    warnings: list[str] = []

    if not marker_path.exists():
        errors.append(
            "Restore drill evidence is missing. Run `make prod-backup` and "
            "`make prod-restore-drill BACKUP=backups/fleetflow-....dump` before go-live."
        )
        return errors, warnings

    try:
        marker: dict[str, Any] = json.loads(marker_path.read_text())
    except json.JSONDecodeError:
        errors.append(f"Restore drill evidence is not valid JSON: {marker_path}")
        return errors, warnings

    if marker.get("succeeded") is not True:
        errors.append("Restore drill evidence does not show a successful restore.")

    checked_at = marker.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at:
        errors.append("Restore drill evidence is missing checked_at.")
    else:
        try:
            checked_at_dt = _parse_utc_datetime(checked_at)
        except ValueError:
            errors.append("Restore drill evidence has an invalid checked_at timestamp.")
        else:
            age_hours = (now - checked_at_dt).total_seconds() / 3600
            if age_hours < -1:
                errors.append("Restore drill evidence timestamp is in the future.")
            elif max_age_hours > 0 and age_hours > max_age_hours:
                errors.append(
                    f"Restore drill evidence is older than {max_age_hours} hours. "
                    "Run a fresh backup/restore drill before go-live."
                )

    backup_path = marker.get("backup_path")
    if isinstance(backup_path, str) and backup_path and not Path(backup_path).exists():
        warnings.append(
            "Restore drill evidence points to a backup file that is no longer on this machine; "
            "confirm the production backup is stored in the protected backup location."
        )

    return errors, warnings


def main() -> int:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".env")
    if not env_path.exists():
        print(f"ERROR: {env_path} does not exist. Run `make setup` first.")
        return 1

    env = load_env(env_path)
    checks = evaluate_env_readiness(env)
    errors = error_messages(checks)
    warnings = warning_messages(checks)

    restore_errors, restore_warnings = restore_drill_messages(env)
    errors.extend(restore_errors)
    warnings.extend(restore_warnings)

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("OK: go-live preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
