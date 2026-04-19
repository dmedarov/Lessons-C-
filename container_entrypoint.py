import os

import uvicorn
from alembic import command
from alembic.config import Config


def run_migrations() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")


if __name__ == "__main__":
    if os.getenv("RUN_MIGRATIONS", "").lower() in {"1", "true", "yes"}:
        run_migrations()

    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,
    )
