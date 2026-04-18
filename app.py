from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from db import init_db
from routers import auth as auth_router
from routers import cars as cars_router
from routers import notifications as notifications_router
from routers import reservations as reservations_router
from routers import users as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Corporate Car Pool Reservation", version="1.0.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=settings.base_dir / "static"), name="static")
    app.include_router(auth_router.router)
    app.include_router(cars_router.router)
    app.include_router(notifications_router.router)
    app.include_router(reservations_router.router)
    app.include_router(users_router.router)

    @app.get("/", include_in_schema=False)
    def ui() -> FileResponse:
        return FileResponse(settings.base_dir / "templates" / "index.html")

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
