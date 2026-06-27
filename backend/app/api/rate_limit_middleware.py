
# backend/app/api/rate_limit_middleware.py

from collections.abc import Collection

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)

from backend.app.rate_limiting.exceptions import (
    RateLimitBackendError,
)
from backend.app.rate_limiting.service import (
    RateLimitDecision,
    get_rate_limiter,
)


class RedisRateLimitMiddleware:
    """Apply a general per-IP API request limit."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limit: int,
        window_seconds: int,
        excluded_paths: Collection[str] = (),
    ) -> None:
        if limit < 1:
            raise ValueError(
                "Rate-limit value must be at least 1."
            )

        if window_seconds < 1:
            raise ValueError(
                "Rate-limit window must be at least 1 second."
            )

        self.app = app
        self.limit = limit
        self.window_seconds = window_seconds
        self.excluded_paths = frozenset(
            excluded_paths
        )

    @staticmethod
    def _identifier(
        scope: Scope,
    ) -> str:
        """Return the direct client IP address."""

        client = scope.get("client")

        if not client:
            return "unknown-client"

        return str(client[0])

    @staticmethod
    def _rate_limit_headers(
        decision: RateLimitDecision,
        *,
        global_headers: bool,
    ) -> dict[str, str]:
        """Build rate-limit response headers."""

        if global_headers:
            return {
                "X-RateLimit-Global-Limit": str(
                    decision.limit
                ),
                "X-RateLimit-Global-Remaining": str(
                    decision.remaining
                ),
                "X-RateLimit-Global-Reset": str(
                    decision.reset_after
                ),
            }

        return {
            "X-RateLimit-Limit": str(
                decision.limit
            ),
            "X-RateLimit-Remaining": str(
                decision.remaining
            ),
            "X-RateLimit-Reset": str(
                decision.reset_after
            ),
        }

    async def _send_backend_error(
        self,
        *,
        scope: Scope,
        receive: Receive,
        send: Send,
        exc: RateLimitBackendError,
    ) -> None:
        """Return a structured Redis failure response."""

        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": (
                        exc.details or None
                    ),
                }
            },
        )

        await response(
            scope,
            receive,
            send,
        )

    async def _send_rate_limit_error(
        self,
        *,
        scope: Scope,
        receive: Receive,
        send: Send,
        decision: RateLimitDecision,
    ) -> None:
        """Return a structured general 429 response."""

        headers = {
            "Retry-After": str(
                decision.retry_after
            ),
            **self._rate_limit_headers(
                decision,
                global_headers=False,
            ),
            **self._rate_limit_headers(
                decision,
                global_headers=True,
            ),
        }

        response = JSONResponse(
            status_code=429,
            headers=headers,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": (
                        "Too many requests. "
                        "Please try again later."
                    ),
                    "details": {
                        "scope": "general",
                        "limit": decision.limit,
                        "remaining": (
                            decision.remaining
                        ),
                        "retry_after": (
                            decision.retry_after
                        ),
                        "reset_after": (
                            decision.reset_after
                        ),
                    },
                }
            },
        )

        await response(
            scope,
            receive,
            send,
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Process one ASGI request."""

        if scope["type"] != "http":
            await self.app(
                scope,
                receive,
                send,
            )
            return

        path = str(
            scope.get("path", "")
        )

        method = str(
            scope.get("method", "")
        ).upper()

        if (
            method == "OPTIONS"
            or path in self.excluded_paths
        ):
            await self.app(
                scope,
                receive,
                send,
            )
            return

        try:
            decision = (
                await get_rate_limiter().check(
                    scope="general",
                    identifier=self._identifier(
                        scope
                    ),
                    limit=self.limit,
                    window_seconds=(
                        self.window_seconds
                    ),
                )
            )

        except RateLimitBackendError as exc:
            await self._send_backend_error(
                scope=scope,
                receive=receive,
                send=send,
                exc=exc,
            )
            return

        if not decision.allowed:
            await self._send_rate_limit_error(
                scope=scope,
                receive=receive,
                send=send,
                decision=decision,
            )
            return

        async def send_wrapper(
            message: Message,
        ) -> None:
            if (
                message["type"]
                == "http.response.start"
            ):
                response_headers = MutableHeaders(
                    scope=message
                )

                global_headers = (
                    self._rate_limit_headers(
                        decision,
                        global_headers=True,
                    )
                )

                for (
                    header_name,
                    header_value,
                ) in global_headers.items():
                    response_headers[
                        header_name
                    ] = header_value

            await send(message)

        await self.app(
            scope,
            receive,
            send_wrapper,
        )
