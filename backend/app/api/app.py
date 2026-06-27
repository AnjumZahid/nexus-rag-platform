
# backend/app/api/app.py

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.httpsredirect import (
    HTTPSRedirectMiddleware,
)
from starlette.middleware.trustedhost import (
    TrustedHostMiddleware,
)

from backend.app.api.auth_routes import (
    router as auth_router,
)
from backend.app.api.dependencies import (
    close_shared_providers,
)
from backend.app.api.document_management_routes import (
    router as document_management_router,
)
from backend.app.api.middleware import (
    RequestSecurityMiddleware,
)
from backend.app.api.organization_routes import (
    router as organization_router,
)
from backend.app.api.rate_limit_middleware import (
    RedisRateLimitMiddleware,
)
from backend.app.api.routes import router
from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.database.session import (
    close_database_connection,
)
from backend.app.rate_limiting.exceptions import (
    RateLimitExceededError,
)
from backend.app.rate_limiting.service import (
    close_rate_limiter,
)

from backend.app.api.health_routes import (
    router as health_router,
)


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """Manage process-wide application resources."""

    try:
        yield

    finally:
        close_shared_providers()
        await close_rate_limiter()
        await close_database_connection()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    @app.exception_handler(
        RateLimitExceededError
    )
    async def rate_limit_exceeded_handler(
        request: Request,
        exc: RateLimitExceededError,
    ) -> JSONResponse:
        """Return a structured 429 response."""

        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content=jsonable_encoder(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": (
                            exc.details or None
                        ),
                    }
                }
            ),
        )

    @app.exception_handler(AppError)
    async def handle_app_error(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        """Return a structured application error."""

        headers: dict[str, str] | None = None

        if exc.status_code == 401:
            headers = {
                "WWW-Authenticate": "Bearer",
            }

        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content=jsonable_encoder(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": (
                            exc.details or None
                        ),
                    }
                }
            ),
        )

    # General Redis-backed rate limiting.
    #
    # This is registered before RequestSecurityMiddleware
    # so the request-security middleware wraps rate-limit
    # responses and adds request/security headers to them.
    app.add_middleware(
        RedisRateLimitMiddleware,
        limit=(
            settings.rate_limit_general_requests
        ),
        window_seconds=(
            settings
            .rate_limit_general_window_seconds
        ),
        excluded_paths={
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
            "/api/v1/health/live",
            "/api/v1/health/ready",
            },
        )

    # Request IDs, timing, security headers, and logging.
    app.add_middleware(
        RequestSecurityMiddleware,
        enable_hsts=(
            settings.security_enable_hsts
        ),
        hsts_max_age_seconds=(
            settings.security_hsts_max_age_seconds
        ),
    )

    # Keep disabled during local HTTP development.
    if settings.security_force_https:
        app.add_middleware(
            HTTPSRedirectMiddleware
        )

    # Reject unexpected Host headers.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_hosts,
        www_redirect=False,
    )

    # Browser cross-origin policy.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            settings.cors_allowed_origins
        ),
        allow_credentials=(
            settings.cors_allow_credentials
        ),
        allow_methods=[
            "GET",
            "POST",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "X-Request-ID",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time-Ms",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "X-RateLimit-Global-Limit",
            "X-RateLimit-Global-Remaining",
            "X-RateLimit-Global-Reset",
            "Retry-After",
        ],
        max_age=600,
    )

    app.include_router(
        router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        auth_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        organization_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        document_management_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        health_router,
        prefix=settings.api_prefix,
    )

    return app
