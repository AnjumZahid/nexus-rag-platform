# backend/app/api/health_routes.py

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_db_session,
)
from backend.app.api.health_schemas import (
    DependencyHealthResponse,
    LivenessResponse,
    ReadinessChecksResponse,
    ReadinessResponse,
)
from backend.app.core.config import settings
from backend.app.rate_limiting.service import (
    get_redis_client,
)
from backend.app.services.health_service import (
    HealthService,
)


router = APIRouter(
    prefix="/health",
    tags=["System"],
)


@router.get(
    "/live",
    response_model=LivenessResponse,
)
async def liveness_check() -> LivenessResponse:
    """
    Confirm that the FastAPI process is running.

    This endpoint does not check external services.
    """

    return LivenessResponse(
        status="alive",
        application=settings.app_name,
        environment=settings.app_environment,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": (
                "One or more required dependencies "
                "are unavailable."
            ),
        },
    },
)
async def readiness_check(
    response: Response,
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
    redis_client: Annotated[
        Redis,
        Depends(get_redis_client),
    ],
) -> ReadinessResponse:
    """
    Confirm that required infrastructure is available.
    """

    result = await HealthService().check_readiness(
        session=session,
        redis_client=redis_client,
        redis_required=settings.rate_limit_enabled,
    )

    if not result.ready:
        response.status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return ReadinessResponse(
        status=(
            "ready"
            if result.ready
            else "not_ready"
        ),
        checks=ReadinessChecksResponse(
            database=DependencyHealthResponse(
                status=result.database.status
            ),
            redis=DependencyHealthResponse(
                status=result.redis.status
            ),
        ),
    )