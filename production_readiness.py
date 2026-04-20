from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ReadinessStatus = Literal["pass", "warn", "fail"]

PLACEHOLDER_VALUES = {
    "",
    "replace-with-a-long-random-secret",
    "replace-with-a-strong-db-password",
    "fleetflow-dev-password",
}


@dataclass(frozen=True)
class ReadinessCheck:
    id: str
    label: str
    status: ReadinessStatus
    message: str
    ui_detail: str
    required: bool = True


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _check(
    check_id: str,
    label: str,
    ok: bool,
    ok_message: str,
    fail_message: str,
    ok_ui: str,
    fail_ui: str,
    *,
    required: bool = True,
) -> ReadinessCheck:
    return ReadinessCheck(
        id=check_id,
        label=label,
        status="pass" if ok else "fail",
        message=ok_message if ok else fail_message,
        ui_detail=ok_ui if ok else fail_ui,
        required=required,
    )


def _warn(
    check_id: str,
    label: str,
    message: str,
    ui_detail: str,
    *,
    required: bool = False,
) -> ReadinessCheck:
    return ReadinessCheck(
        id=check_id,
        label=label,
        status="warn",
        message=message,
        ui_detail=ui_detail,
        required=required,
    )


def _pass(check_id: str, label: str, message: str, ui_detail: str, *, required: bool = True) -> ReadinessCheck:
    return ReadinessCheck(
        id=check_id,
        label=label,
        status="pass",
        message=message,
        ui_detail=ui_detail,
        required=required,
    )


def evaluate_env_readiness(env: dict[str, str], *, include_netfleet: bool = True) -> list[ReadinessCheck]:
    app_env = env.get("APP_ENV", "")
    secret_key = env.get("SECRET_KEY", "")
    postgres_password = env.get("POSTGRES_PASSWORD", "")
    database_url = env.get("DATABASE_URL", "")
    postgres_image = env.get("POSTGRES_IMAGE", "postgres:16")
    cors = env.get("CORS_ALLOW_ORIGINS", "")
    dev_seed = env.get("DEV_SEED_DEMO_DATA", "")

    checks = [
        _check(
            "app_env",
            "Production mode",
            app_env == "prod",
            "APP_ENV is prod.",
            "APP_ENV must be prod for production.",
            "Приложението е в production режим.",
            "Задай APP_ENV=prod преди live.",
        ),
        _check(
            "secret_key",
            "Application secret",
            secret_key not in PLACEHOLDER_VALUES and len(secret_key) >= 32,
            "SECRET_KEY is generated.",
            "SECRET_KEY must be generated and at least 32 characters.",
            "SECRET_KEY е генериран и достатъчно дълъг.",
            "Генерирай нов SECRET_KEY чрез make setup.",
        ),
        _check(
            "postgres_password",
            "Database password",
            postgres_password not in PLACEHOLDER_VALUES and len(postgres_password) >= 16,
            "POSTGRES_PASSWORD is generated.",
            "POSTGRES_PASSWORD must be generated and not use a dev/default value.",
            "Паролата за PostgreSQL е генерирана.",
            "POSTGRES_PASSWORD трябва да е генерирана, не dev/default стойност.",
        ),
        _check(
            "database_url",
            "Database URL",
            bool(database_url)
            and database_url.startswith(("postgresql://", "postgres://"))
            and "fleetflow-dev-password" not in database_url
            and "replace-with-a-strong-db-password" not in database_url,
            "DATABASE_URL points to PostgreSQL.",
            "DATABASE_URL must contain the generated production database password.",
            "DATABASE_URL сочи към PostgreSQL production връзка.",
            "DATABASE_URL трябва да сочи към PostgreSQL с генерираната парола.",
        ),
        _check(
            "postgres_image",
            "PostgreSQL image",
            ":latest" not in postgres_image and not postgres_image.endswith("latest"),
            "POSTGRES_IMAGE is pinned to a major version.",
            "POSTGRES_IMAGE must be pinned to a major version, not latest.",
            "PostgreSQL image е pin-нат към major версия.",
            "Не използвай PostgreSQL latest в production; pin-ни major версия.",
        ),
        _check(
            "cors",
            "CORS origin",
            bool(cors) and cors != "*" and "example.com" not in cors,
            "CORS_ALLOW_ORIGINS uses a real origin.",
            "CORS_ALLOW_ORIGINS must be the real production origin, not wildcard/example.",
            "CORS е ограничен до реален production origin.",
            "Задай реалния домейн в CORS_ALLOW_ORIGINS, без wildcard/example.",
        ),
        _check(
            "dev_seed",
            "Demo seed",
            dev_seed.lower() == "false",
            "DEV_SEED_DEMO_DATA is false.",
            "DEV_SEED_DEMO_DATA must be false in production.",
            "Demo seed е изключен.",
            "Изключи DEV_SEED_DEMO_DATA=false преди live.",
        ),
    ]

    if postgres_password and database_url and postgres_password not in database_url:
        checks.append(
            ReadinessCheck(
                id="database_password_match",
                label="Database password match",
                status="fail",
                message="DATABASE_URL password does not match POSTGRES_PASSWORD.",
                ui_detail="DATABASE_URL и POSTGRES_PASSWORD не са консистентни.",
            )
        )

    if include_netfleet:
        if env.get("NETFLEET_API_KEY"):
            checks.append(
                _pass(
                    "netfleet",
                    "NetFleet GPS",
                    "NETFLEET_API_KEY is configured.",
                    "NetFleet ключът е наличен в runtime средата.",
                    required=False,
                )
            )
        else:
            checks.append(
                _warn(
                    "netfleet",
                    "NetFleet GPS",
                    "NETFLEET_API_KEY is empty; live GPS can still be configured later from Admin UI.",
                    "Live GPS може да се включи по-късно от Admin UI.",
                )
            )

    return checks


def runtime_env() -> dict[str, str]:
    from config import settings

    return {
        "APP_ENV": settings.app_env,
        "SECRET_KEY": settings.secret_key,
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "DATABASE_URL": settings.database_url or "",
        "CORS_ALLOW_ORIGINS": ",".join(settings.cors_allow_origins),
        "DEV_SEED_DEMO_DATA": "true" if settings.dev_seed_demo_data else "false",
        "NETFLEET_API_KEY": settings.netfleet_api_key or "",
    }


def evaluate_runtime_readiness() -> dict:
    from app_settings import get_netfleet_config_status
    from config import settings
    from db import get_conn

    checks = evaluate_env_readiness(runtime_env(), include_netfleet=False)

    try:
        with get_conn() as conn:
            conn.execute("SELECT 1").fetchone()
            active_admins = int(
                conn.execute(
                    "SELECT COUNT(*) AS n FROM users WHERE role='fleet_admin' AND active=1"
                ).fetchone()["n"]
            )
        checks.append(
            _pass(
                "database_connection",
                "Database connection",
                "Database connection is healthy.",
                "Базата данни отговаря успешно.",
            )
        )
        checks.append(
            _check(
                "active_admin",
                "Active admin",
                active_admins > 0,
                "At least one active fleet_admin exists.",
                "At least one active fleet_admin is required.",
                "Има поне един активен администратор.",
                "Създай или активирай поне един fleet_admin.",
            )
        )
    except Exception:
        checks.append(
            ReadinessCheck(
                id="database_connection",
                label="Database connection",
                status="fail",
                message="Database connection failed.",
                ui_detail="Базата данни не отговори успешно.",
            )
        )

    netfleet = get_netfleet_config_status()
    if netfleet["configured"]:
        checks.append(
            _pass(
                "netfleet",
                "NetFleet GPS",
                "NetFleet API key is configured.",
                "NetFleet GPS е конфигуриран за live координати.",
                required=False,
            )
        )
    else:
        checks.append(
            _warn(
                "netfleet",
                "NetFleet GPS",
                "NETFLEET_API_KEY is empty; live GPS can still be configured later from Admin UI.",
                "Live GPS още не е включен. Може да се добави еднократно от Admin UI.",
            )
        )

    outbound_configured = any(
        [
            settings.smtp_host and settings.smtp_from_email and settings.smtp_to_email,
            settings.slack_webhook_url,
            settings.teams_webhook_url,
        ]
    )
    checks.append(
        _pass(
            "notifications",
            "Outbound notifications",
            "At least one outbound notification channel is configured.",
            "Има конфигуриран outbound канал за известия.",
            required=False,
        )
        if outbound_configured
        else _warn(
            "notifications",
            "Outbound notifications",
            "No outbound notification channel is configured.",
            "Няма SMTP/Slack/Teams канал. In-app нотификациите работят, но външни известия няма.",
        )
    )

    ready = all(check.status != "fail" for check in checks if check.required)
    return {
        "ready": ready,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "app_env": settings.app_env,
        "database_backend": settings.db_backend,
        "items": [
            {
                "id": check.id,
                "label": check.label,
                "status": check.status,
                "detail": check.ui_detail,
                "required": check.required,
            }
            for check in checks
        ],
    }


def error_messages(checks: list[ReadinessCheck]) -> list[str]:
    return [check.message for check in checks if check.status == "fail" and check.required]


def warning_messages(checks: list[ReadinessCheck]) -> list[str]:
    return [check.message for check in checks if check.status == "warn"]
