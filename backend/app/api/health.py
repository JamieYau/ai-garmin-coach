from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.db.session import check_database_ready

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/ready")
def ready(response: Response) -> dict[str, str]:
    database_ready, database_status = check_database_ready()
    if not database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if database_ready else "not_ready",
        "database": database_status,
    }
