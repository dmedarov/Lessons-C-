from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


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

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

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
