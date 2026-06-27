import re
from time import perf_counter
from uuid import uuid4

import structlog
from starlette.datastructures import (
    Headers,
    MutableHeaders,
)
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)


logger = structlog.get_logger(__name__)


_REQUEST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]{8,128}$"
)


class RequestSecurityMiddleware:
    """
    Add request tracing, safe security headers,
    request timing, and structured request logging.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        enable_hsts: bool = False,
        hsts_max_age_seconds: int = 31_536_000,
    ) -> None:
        self.app = app
        self.enable_hsts = enable_hsts
        self.hsts_max_age_seconds = (
            hsts_max_age_seconds
        )

    @staticmethod
    def _request_id(
        scope: Scope,
    ) -> str:
        headers = Headers(scope=scope)

        supplied_request_id = headers.get(
            "x-request-id"
        )

        if (
            supplied_request_id
            and _REQUEST_ID_PATTERN.fullmatch(
                supplied_request_id
            )
        ):
            return supplied_request_id

        return uuid4().hex

    @staticmethod
    def _client_ip(
        scope: Scope,
    ) -> str | None:
        client = scope.get("client")

        if not client:
            return None

        return str(client[0])

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(
                scope,
                receive,
                send,
            )
            return

        request_id = self._request_id(scope)

        state = scope.setdefault(
            "state",
            {},
        )

        state["request_id"] = request_id

        method = str(
            scope.get("method", "")
        )

        path = str(
            scope.get("path", "")
        )

        scheme = str(
            scope.get("scheme", "http")
        )

        client_ip = self._client_ip(scope)

        started_at = perf_counter()

        response_status = 500

        async def send_wrapper(
            message: Message,
        ) -> None:
            nonlocal response_status

            if (
                message["type"]
                == "http.response.start"
            ):
                response_status = int(
                    message["status"]
                )

                duration_ms = (
                    perf_counter() - started_at
                ) * 1000

                response_headers = MutableHeaders(
                    scope=message
                )

                response_headers[
                    "X-Request-ID"
                ] = request_id

                response_headers[
                    "X-Process-Time-Ms"
                ] = f"{duration_ms:.2f}"

                response_headers[
                    "X-Content-Type-Options"
                ] = "nosniff"

                response_headers[
                    "X-Frame-Options"
                ] = "DENY"

                response_headers[
                    "Referrer-Policy"
                ] = "no-referrer"

                response_headers[
                    "Permissions-Policy"
                ] = (
                    "camera=(), "
                    "microphone=(), "
                    "geolocation=()"
                )

                if path.startswith(
                    "/api/v1/auth"
                ):
                    response_headers[
                        "Cache-Control"
                    ] = "no-store"

                if (
                    self.enable_hsts
                    and scheme == "https"
                ):
                    response_headers[
                        "Strict-Transport-Security"
                    ] = (
                        f"max-age="
                        f"{self.hsts_max_age_seconds}; "
                        "includeSubDomains"
                    )

            await send(message)

        try:
            await self.app(
                scope,
                receive,
                send_wrapper,
            )

        except Exception as exc:
            duration_ms = (
                perf_counter() - started_at
            ) * 1000

            logger.error(
                "http_request_failed",
                request_id=request_id,
                method=method,
                path=path,
                client_ip=client_ip,
                duration_ms=round(
                    duration_ms,
                    2,
                ),
                error_type=type(exc).__name__,
            )

            raise

        else:
            duration_ms = (
                perf_counter() - started_at
            ) * 1000

            logger.info(
                "http_request_completed",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response_status,
                client_ip=client_ip,
                duration_ms=round(
                    duration_ms,
                    2,
                ),
            )