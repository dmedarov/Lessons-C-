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

        return cls(
            db_path=os.getenv("DB_PATH", "/data/fleet.db"),
            database_url=os.getenv("DATABASE_URL"),
            secret_key=secret,
            token_ttl_seconds=int(os.getenv("TOKEN_TTL_SECONDS", "3600")),
            base_dir=Path(__file__).resolve().parent,
            app_env=app_env,
        )


settings = Settings.from_env()
