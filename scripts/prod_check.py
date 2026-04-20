from __future__ import annotations

import sys
from pathlib import Path


PLACEHOLDER_VALUES = {
    "",
    "replace-with-a-long-random-secret",
    "replace-with-a-strong-db-password",
    "fleetflow-dev-password",
}


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    env_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".env")
    if not env_path.exists():
        print(f"ERROR: {env_path} does not exist. Run `make setup` first.")
        return 1

    env = load_env(env_path)
    errors: list[str] = []
    warnings: list[str] = []

    app_env = env.get("APP_ENV", "")
    secret_key = env.get("SECRET_KEY", "")
    postgres_password = env.get("POSTGRES_PASSWORD", "")
    database_url = env.get("DATABASE_URL", "")
    cors = env.get("CORS_ALLOW_ORIGINS", "")
    dev_seed = env.get("DEV_SEED_DEMO_DATA", "")

    if app_env != "prod":
        errors.append("APP_ENV must be prod for production.")
    if secret_key in PLACEHOLDER_VALUES or len(secret_key) < 32:
        errors.append("SECRET_KEY must be generated and at least 32 characters.")
    if postgres_password in PLACEHOLDER_VALUES or len(postgres_password) < 16:
        errors.append("POSTGRES_PASSWORD must be generated and not use a dev/default value.")
    if (
        not database_url
        or "fleetflow-dev-password" in database_url
        or "replace-with-a-strong-db-password" in database_url
    ):
        errors.append("DATABASE_URL must contain the generated production database password.")
    elif postgres_password and postgres_password not in database_url:
        errors.append("DATABASE_URL password does not match POSTGRES_PASSWORD.")
    if not cors or cors == "*" or "example.com" in cors:
        errors.append("CORS_ALLOW_ORIGINS must be the real production origin, not wildcard/example.")
    if dev_seed.lower() != "false":
        errors.append("DEV_SEED_DEMO_DATA must be false in production.")

    if not env.get("NETFLEET_API_KEY"):
        warnings.append("NETFLEET_API_KEY is empty; live GPS can still be configured later from Admin UI.")

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
