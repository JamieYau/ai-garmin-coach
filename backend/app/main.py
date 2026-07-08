from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.connections import router as connections_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=settings.backend_cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(connections_router)
    app.include_router(dashboard_router)
    app.include_router(health_router)
    return app


app = create_app()
