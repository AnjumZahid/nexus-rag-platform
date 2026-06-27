from datetime import timedelta

from backend.app.auth.jwt import JWTService
from backend.app.core.exceptions import (
    AuthenticationError,
)


TEST_SECRET = (
    "test-secret-key-that-is-longer-than-"
    "thirty-two-characters-123456789"
)


def build_service(
    *,
    issuer: str = "test-issuer",
    audience: str = "test-audience",
) -> JWTService:
    return JWTService(
    secret_key=TEST_SECRET,
    algorithm="HS256",
    issuer=issuer,
    audience=audience,
    access_token_expire_minutes=60,
    refresh_token_expire_days=30,
    leeway_seconds=0,
)


def assert_authentication_error(
    callback,
) -> None:
    error_detected = False

    try:
        callback()
    except AuthenticationError:
        error_detected = True

    assert error_detected is True


def main() -> None:
    service = build_service()

    valid_token = service.create_access_token(
        user_id="user-123",
        organization_id="org-456",
    )

    claims = service.decode_access_token(
        valid_token
    )

    assert claims.user_id == "user-123"
    assert claims.organization_id == "org-456"
    assert claims.token_type == "access"
    assert claims.token_id

    expired_token = service.create_access_token(
        user_id="user-123",
        organization_id="org-456",
        expires_delta=timedelta(seconds=-1),
    )

    assert_authentication_error(
        lambda: service.decode_access_token(
            expired_token
        )
    )

    wrong_audience_service = build_service(
        audience="different-audience"
    )

    wrong_audience_token = (
        wrong_audience_service.create_access_token(
            user_id="user-123",
            organization_id="org-456",
        )
    )

    assert_authentication_error(
        lambda: service.decode_access_token(
            wrong_audience_token
        )
    )

    wrong_issuer_service = build_service(
        issuer="different-issuer"
    )

    wrong_issuer_token = (
        wrong_issuer_service.create_access_token(
            user_id="user-123",
            organization_id="org-456",
        )
    )

    assert_authentication_error(
        lambda: service.decode_access_token(
            wrong_issuer_token
        )
    )

    assert_authentication_error(
        lambda: service.decode_access_token(
            "not-a-valid-jwt"
        )
    )

    print("\n=== JWT AUTHENTICATION TEST ===")
    print("Valid token confirmed.")
    print("User claim confirmed.")
    print("Organization claim confirmed.")
    print("Expired token rejected.")
    print("Wrong audience rejected.")
    print("Wrong issuer rejected.")
    print("Invalid signature/token rejected.")
    print(
        "JWT authentication test "
        "passed successfully."
    )


if __name__ == "__main__":
    main()


# uv run python -m tests.test_jwt_auth
# uv run python -m tests.test_api_endpoints
