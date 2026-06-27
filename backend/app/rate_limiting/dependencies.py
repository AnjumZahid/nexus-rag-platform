
# backend/app/rate_limiting/dependencies.py

from collections.abc import (
    Awaitable,
    Callable,
)
from typing import Annotated

from fastapi import (
    Depends,
    Request,
    Response,
)

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_organization_access,
)
from backend.app.rate_limiting.exceptions import (
    RateLimitExceededError,
)
from backend.app.rate_limiting.service import (
    RateLimitDecision,
    get_rate_limiter,
)


RateLimitDependency = Callable[
    ...,
    Awaitable[None],
]


def _client_identifier(
    request: Request,
) -> str:
    """Return the direct client IP address."""

    client = request.client

    if client is None:
        return "unknown-client"

    return str(client.host)


def _apply_headers(
    response: Response,
    decision: RateLimitDecision,
) -> None:
    """Attach endpoint-specific rate-limit headers."""

    response.headers[
        "X-RateLimit-Limit"
    ] = str(decision.limit)

    response.headers[
        "X-RateLimit-Remaining"
    ] = str(decision.remaining)

    response.headers[
        "X-RateLimit-Reset"
    ] = str(decision.reset_after)


def _raise_if_blocked(
    *,
    scope: str,
    decision: RateLimitDecision,
) -> None:
    """Raise a structured 429 error when blocked."""

    if decision.allowed:
        return

    raise RateLimitExceededError(
        scope=scope,
        limit=decision.limit,
        remaining=decision.remaining,
        retry_after=decision.retry_after,
        reset_after=decision.reset_after,
    )


def require_ip_rate_limit(
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> RateLimitDependency:
    """
    Create an IP-based rate-limit dependency.

    This is suitable for unauthenticated endpoints such
    as registration, login, and token refresh.
    """

    async def dependency(
        request: Request,
        response: Response,
    ) -> None:
        decision = await get_rate_limiter().check(
            scope=scope,
            identifier=_client_identifier(
                request
            ),
            limit=limit,
            window_seconds=window_seconds,
        )

        _apply_headers(
            response,
            decision,
        )

        _raise_if_blocked(
            scope=scope,
            decision=decision,
        )

    return dependency


def require_user_rate_limit(
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> RateLimitDependency:
    """
    Create an organization-and-user rate limit.

    The identifier comes from the validated JWT and active
    organization membership, not from client input.
    """

    async def dependency(
        response: Response,
        access: Annotated[
            OrganizationAccess,
            Depends(get_organization_access),
        ],
    ) -> None:
        identifier = (
            f"{access.organization_id}:"
            f"{access.user_id}"
        )

        decision = await get_rate_limiter().check(
            scope=scope,
            identifier=identifier,
            limit=limit,
            window_seconds=window_seconds,
        )

        _apply_headers(
            response,
            decision,
        )

        _raise_if_blocked(
            scope=scope,
            decision=decision,
        )

    return dependency
