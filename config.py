from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: str
    database_url: str | None
    secret_key: str
    token_ttl_seconds: int
    base_dir: Path
    app_env: str
    notification_timeout_seconds: int
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_from_email: str | None
    smtp_to_email: str | None
    smtp_use_tls: bool
    slack_webhook_url: str | None
    teams_webhook_url: str | None
    cors_allow_origins: tuple[str, ...]

    @property
    def db_backend(self) -> str:
        return "postgres" if self.database_url else "sqlite"

    @classmethod
    def from_env(cls) -> "Settings":
        app_env = os.getenv("APP_ENV", "dev")
        secret = os.getenv("SECRET_KEY")
        if not secret:
            if app_env != "dev":
                raise RuntimeError("SECRET_KEY env var is required outside dev")
            secret = secrets.token_urlsafe(32)

        cors_raw = os.getenv("CORS_ALLOW_ORIGINS")
        if cors_raw is None:
            cors_raw = "*" if app_env == "dev" else ""
        cors_allow_origins = tuple(origin.strip() for origin in cors_raw.split(",") if origin.strip())

        return cls(
            db_path=os.getenv("DB_PATH", "/data/fleet.db"),
            database_url=os.getenv("DATABASE_URL"),
            secret_key=secret,
            token_ttl_seconds=int(os.getenv("TOKEN_TTL_SECONDS", "3600")),
            base_dir=Path(__file__).resolve().parent,
            app_env=app_env,
            notification_timeout_seconds=int(os.getenv("NOTIFICATION_TIMEOUT_SECONDS", "5")),
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL"),
            smtp_to_email=os.getenv("SMTP_TO_EMAIL"),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() != "false",
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            teams_webhook_url=os.getenv("TEAMS_WEBHOOK_URL"),
            cors_allow_origins=cors_allow_origins,
        )


settings = Settings.from_env()
