from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import APIResponse
from app.schemas.health import HealthResponse


router = APIRouter()


@router.get("/health", response_model=APIResponse[HealthResponse])
def health_check() -> APIResponse[HealthResponse]:
    settings = get_settings()
    return APIResponse(
        data=HealthResponse(
            service=settings.project_name,
            version=settings.app_version,
            environment=settings.app_env,
        )
    )
