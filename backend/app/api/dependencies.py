from collections.abc import AsyncIterator
from dataclasses import dataclass

# from typing import Annotated
# from fastapi import Header

from typing import Annotated

from fastapi import Security
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from backend.app.auth import get_jwt_service
from backend.app.core.exceptions import AuthenticationError

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_session_factory
from backend.app.embeddings.base import BaseEmbeddingProvider
from backend.app.embeddings.factory import (
    get_embedding_provider,
)
from backend.app.llms.base import BaseLLMProvider
from backend.app.llms.factory import get_llm_provider

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.roles import OrganizationRole
from backend.app.core.exceptions import (
    AuthorizationError,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)


_embedding_provider: BaseEmbeddingProvider | None = None
_llm_provider: BaseLLMProvider | None = None



@dataclass(frozen=True, slots=True)
class RequestIdentity:
    """Authenticated request identity."""

    organization_id: str
    user_id: str
    token_id: str


bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description=(
        "Enter a signed JWT access token."
    ),
)

@dataclass(frozen=True, slots=True)
class OrganizationAccess:
    """Verified access to the current organization."""

    organization_id: str
    user_id: str
    membership_id: str
    role: str


def get_request_identity(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(bearer_scheme),
    ],
) -> RequestIdentity:
    """Build request identity from a verified JWT."""

    if credentials is None:
        raise AuthenticationError(
            message=(
                "An Authorization Bearer token "
                "is required."
            )
        )

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError(
            message=(
                "The Authorization scheme must "
                "be Bearer."
            )
        )

    claims = get_jwt_service().decode_access_token(
        credentials.credentials
    )

    return RequestIdentity(
        organization_id=claims.organization_id,
        user_id=claims.user_id,
        token_id=claims.token_id,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide one database session per request."""

    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session

async def get_organization_access(
    identity: Annotated[
        RequestIdentity,
        Depends(get_request_identity),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> OrganizationAccess:
    """Require an active organization membership."""

    membership = await MembershipRepository(
        session
    ).get_active_membership(
        user_id=identity.user_id,
        organization_id=identity.organization_id,
    )

    if membership is None:
        raise AuthorizationError(
            message=(
                "An active organization membership "
                "is required."
            )
        )

    return OrganizationAccess(
        organization_id=identity.organization_id,
        user_id=identity.user_id,
        membership_id=membership.id,
        role=membership.role,
    )


def get_shared_embedding_provider() -> BaseEmbeddingProvider:
    """Return the process-wide embedding provider."""

    global _embedding_provider

    if _embedding_provider is None:
        _embedding_provider = get_embedding_provider()

    return _embedding_provider


def get_shared_llm_provider() -> BaseLLMProvider:
    """Return the process-wide LLM provider."""

    global _llm_provider

    if _llm_provider is None:
        _llm_provider = get_llm_provider()

    return _llm_provider


def close_shared_providers() -> None:
    """Close cached providers during application shutdown."""

    global _embedding_provider
    global _llm_provider

    for provider in (
        _embedding_provider,
        _llm_provider,
    ):
        if provider is None:
            continue

        close_method = getattr(
            provider,
            "close",
            None,
        )

        if callable(close_method):
            close_method()

    _embedding_provider = None
    _llm_provider = None

def require_organization_roles(
    *allowed_roles: OrganizationRole,
):
    """Build a dependency requiring selected roles."""

    allowed_values = frozenset(
        role.value for role in allowed_roles
    )

    async def dependency(
        access: Annotated[
            OrganizationAccess,
            Depends(get_organization_access),
        ],
    ) -> OrganizationAccess:
        if access.role not in allowed_values:
            raise AuthorizationError(
                message=(
                    "Your organization role does not "
                    "permit this action."
                )
            )

        return access

    return dependency