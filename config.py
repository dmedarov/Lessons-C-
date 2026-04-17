from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: str
    secret_key: str
    token_ttl_seconds: int
    base_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        secret = os.getenv("SECRET_KEY")
        if not secret:
            if os.getenv("APP_ENV", "dev") != "dev":
                raise RuntimeError("SECRET_KEY env var is required outside dev")
            secret = secrets.token_urlsafe(32)

        return cls(
            db_path=os.getenv("DB_PATH", "/data/fleet.db"),
            secret_key=secret,
            token_ttl_seconds=int(os.getenv("TOKEN_TTL_SECONDS", "3600")),
            base_dir=Path(__file__).resolve().parent,
        )


settings = Settings.from_env()
