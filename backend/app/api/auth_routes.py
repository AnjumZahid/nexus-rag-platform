
## New file: `backend/app/api/auth_routes.py`


from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.auth_schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.app.api.dependencies import (
    RequestIdentity,
    get_db_session,
    get_request_identity,
)
from backend.app.auth import (
    get_jwt_service,
    password_service,
)
from backend.app.auth.service import AuthService
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)

from backend.app.core.config import settings
from backend.app.rate_limiting.dependencies import (
    require_ip_rate_limit,
)

from fastapi import Depends

from backend.app.core.config import settings
from backend.app.rate_limiting.dependencies import (
    require_ip_rate_limit,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

register_rate_limit = require_ip_rate_limit(
    scope="auth-register",
    limit=(
        settings.rate_limit_register_requests
    ),
    window_seconds=(
        settings
        .rate_limit_register_window_seconds
    ),
)

login_rate_limit = require_ip_rate_limit(
    scope="auth-login",
    limit=settings.rate_limit_login_requests,
    window_seconds=(
        settings.rate_limit_login_window_seconds
    ),
)

refresh_rate_limit = require_ip_rate_limit(
    scope="auth-refresh",
    limit=(
        settings.rate_limit_refresh_requests
    ),
    window_seconds=(
        settings.rate_limit_refresh_window_seconds
    ),
)


def build_auth_service(
    session: AsyncSession,
) -> AuthService:
    return AuthService(
        session=session,
        repository=AuthRepository(session),
        password_service=password_service,
        jwt_service=get_jwt_service(),
    )


def build_token_response(
    *,
    user,
    tokens,
) -> TokenResponse:
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.access_expires_in,
        user=UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        ),
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(register_rate_limit),
    ],
)
async def register(
    request: RegisterRequest,
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> TokenResponse:
    user, tokens = await build_auth_service(
        session
    ).register(
        organization_name=(
            request.organization_name
        ),
        full_name=request.full_name,
        email=str(request.email),
        password=request.password,
    )

    return build_token_response(
        user=user,
        tokens=tokens,
    )




@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[
        Depends(login_rate_limit),
    ],
)

async def login(
    request: LoginRequest,
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> TokenResponse:
    user, tokens = await build_auth_service(
        session
    ).login(
        email=str(request.email),
        password=request.password,
    )

    return build_token_response(
        user=user,
        tokens=tokens,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[
        Depends(refresh_rate_limit),
    ],
)
async def refresh(
    request: RefreshRequest,
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> TokenResponse:
    user, tokens = await build_auth_service(
        session
    ).refresh(
        refresh_token=request.refresh_token,
    )

    return build_token_response(
        user=user,
        tokens=tokens,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    request: LogoutRequest,
    identity: Annotated[
        RequestIdentity,
        Depends(get_request_identity),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> Response:
    await build_auth_service(session).logout(
        refresh_token=request.refresh_token,
        user_id=identity.user_id,
        organization_id=identity.organization_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    identity: Annotated[
        RequestIdentity,
        Depends(get_request_identity),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> UserResponse:
    user = await build_auth_service(
        session
    ).get_current_user(
        user_id=identity.user_id,
        organization_id=identity.organization_id,
    )

    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )
