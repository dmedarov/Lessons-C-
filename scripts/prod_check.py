from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production_readiness import error_messages, load_env, warning_messages, evaluate_env_readiness  # noqa: E402


def main() -> int:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".env")
    if not env_path.exists():
        print(f"ERROR: {env_path} does not exist. Run `make setup` first.")
        return 1

    checks = evaluate_env_readiness(load_env(env_path))
    errors = error_messages(checks)
    warnings = warning_messages(checks)

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("OK: production environment looks ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
