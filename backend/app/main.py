from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.connections import router as connections_router
from app.api.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.sync import router as sync_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.middleware.rate_limit import RateLimitMiddleware, RateLimitRule
from app.middleware.request_id import RequestIDMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        RateLimitMiddleware,
        enabled=settings.rate_limit_enabled,
        rules=(
            RateLimitRule(
                name="garmin_connection",
                method="POST",
                path="/connections/garmin",
                max_requests=settings.garmin_connection_rate_limit_max_requests,
                window_seconds=settings.garmin_connection_rate_limit_window_seconds,
            ),
            RateLimitRule(
                name="manual_sync",
                method="POST",
                path="/sync/manual",
                max_requests=settings.manual_sync_rate_limit_max_requests,
                window_seconds=settings.manual_sync_rate_limit_window_seconds,
            ),
            RateLimitRule(
                name="ai_insight_generation",
                method="POST",
                path="/coach/insights/generate",
                max_requests=settings.ai_insight_rate_limit_max_requests,
                window_seconds=settings.ai_insight_rate_limit_window_seconds,
            ),
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=settings.backend_cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.include_router(connections_router)
    app.include_router(dashboard_router)
    app.include_router(health_router)
    app.include_router(sync_router)
    return app


app = create_app()
