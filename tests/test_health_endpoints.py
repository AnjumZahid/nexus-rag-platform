# tests/test_health_endpoints.py

from fastapi.testclient import TestClient

from backend.app.api.app import create_app
from backend.app.api.dependencies import (
    get_db_session,
)
from backend.app.rate_limiting.service import (
    get_redis_client,
)


class FakeDatabaseSession:
    """Healthy database-session replacement."""

    async def execute(
        self,
        *args,
        **kwargs,
    ) -> object:
        return object()


class FailingDatabaseSession:
    """Unavailable database-session replacement."""

    async def execute(
        self,
        *args,
        **kwargs,
    ) -> object:
        raise ConnectionError(
            "Simulated database failure."
        )


class FakeRedisClient:
    """Healthy Redis-client replacement."""

    async def ping(self) -> bool:
        return True


async def healthy_db_session():
    yield FakeDatabaseSession()


async def failing_db_session():
    yield FailingDatabaseSession()


def fake_redis_client() -> FakeRedisClient:
    return FakeRedisClient()


def main() -> None:
    app = create_app()

    app.dependency_overrides[
        get_db_session
    ] = healthy_db_session

    app.dependency_overrides[
        get_redis_client
    ] = fake_redis_client

    try:
        with TestClient(app) as client:
            live_response = client.get(
                "/api/v1/health/live"
            )

            assert live_response.status_code == 200
            assert (
                live_response.json()["status"]
                == "alive"
            )

            ready_response = client.get(
                "/api/v1/health/ready"
            )

            assert ready_response.status_code == 200

            ready_body = ready_response.json()

            assert (
                ready_body["status"]
                == "ready"
            )

            assert (
                ready_body["checks"]["database"][
                    "status"
                ]
                == "ok"
            )

            assert (
                ready_body["checks"]["redis"][
                    "status"
                ]
                == "ok"
            )

            app.dependency_overrides[
                get_db_session
            ] = failing_db_session

            unavailable_response = client.get(
                "/api/v1/health/ready"
            )

            assert (
                unavailable_response.status_code
                == 503
            )

            unavailable_body = (
                unavailable_response.json()
            )

            assert (
                unavailable_body["status"]
                == "not_ready"
            )

            assert (
                unavailable_body["checks"][
                    "database"
                ]["status"]
                == "unavailable"
            )

            print(
                "\n=== HEALTH ENDPOINT TEST ==="
            )
            print(
                "Liveness endpoint confirmed."
            )
            print(
                "Healthy readiness confirmed."
            )
            print(
                "MySQL readiness confirmed."
            )
            print(
                "Redis readiness confirmed."
            )
            print(
                "Unavailable dependency "
                "response confirmed."
            )
            print(
                "Health endpoint test "
                "passed successfully."
            )

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    main()

# uv run python -m tests.test_health_endpoints