from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production_readiness import (  # noqa: E402
    error_messages,
    evaluate_env_readiness,
    load_env,
    restore_drill_readiness,
    warning_messages,
)


def restore_drill_messages(env: dict[str, str], *, now: datetime | None = None) -> tuple[list[str], list[str]]:
    check = restore_drill_readiness(env, strict=True, now=now or datetime.now(timezone.utc))
    errors: list[str] = []
    warnings: list[str] = []
    if check.status == "fail":
        errors.append(check.message)
    elif check.status == "warn":
        warnings.append(check.message)

    try:
        marker_path = Path(os.getenv("RESTORE_DRILL_MARKER", env.get("RESTORE_DRILL_MARKER", ".fleetflow/restore-drill-ok.json")))
        if marker_path.exists():
            marker = json.loads(marker_path.read_text())
            backup_path = marker.get("backup_path")
            if isinstance(backup_path, str) and backup_path and not Path(backup_path).exists():
                warnings.append(
                    "Restore drill evidence points to a backup file that is no longer on this machine; "
                    "confirm the production backup is stored in the protected backup location."
                )
    except Exception:
        pass
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
