from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import bootstrap_tokens
from config import settings
from db import get_conn, init_db
from routers import auth as auth_router
from routers import cars as cars_router
from routers import notifications as notifications_router
from routers import reservations as reservations_router
from routers import users as users_router


def _admin_exists_on_startup() -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM users WHERE role='fleet_admin' AND active=1 LIMIT 1"
        ).fetchone()
    return bool(row)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # In production, provision + log a one-shot bootstrap token if no admin
    # yet exists. No-op in dev and no-op once the admin is bootstrapped.
    bootstrap_tokens.announce_if_needed(_admin_exists_on_startup())
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Corporate Car Pool Reservation", version="1.0.0", lifespan=lifespan)
    if settings.cors_allow_origins:
        wildcard_origins = "*" in settings.cors_allow_origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_allow_origins),
            allow_credentials=not wildcard_origins,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.mount("/static", StaticFiles(directory=settings.base_dir / "static"), name="static")
    app.include_router(auth_router.router)
    app.include_router(cars_router.router)
    app.include_router(notifications_router.router)
    app.include_router(reservations_router.router)
    app.include_router(users_router.router)

    @app.get("/", include_in_schema=False)
    def ui() -> FileResponse:
        return FileResponse(settings.base_dir / "templates" / "index.html")

    @app.get("/admin", include_in_schema=False)
    def admin_ui() -> FileResponse:
        return FileResponse(settings.base_dir / "templates" / "admin.html")

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
