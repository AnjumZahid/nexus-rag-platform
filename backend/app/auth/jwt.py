## Replace file: `backend/app/auth/jwt.py`

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from uuid import uuid4

import jwt
from jwt import (
    ExpiredSignatureError,
    InvalidTokenError,
)

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    AuthenticationError,
)


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: str
    organization_id: str
    token_id: str
    token_type: str
    issued_at: int
    expires_at: int


@dataclass(frozen=True, slots=True)
class RefreshTokenClaims:
    user_id: str
    organization_id: str
    token_id: str
    token_type: str
    issued_at: int
    expires_at: int


class JWTService:
    """Create and validate access and refresh JWTs."""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        issuer: str,
        audience: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
        leeway_seconds: int = 0,
    ) -> None:
        if len(secret_key) < 32:
            raise ValueError(
                "JWT secret key must contain at least "
                "32 characters."
            )

        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.access_token_expire_minutes = (
            access_token_expire_minutes
        )
        self.refresh_token_expire_days = (
            refresh_token_expire_days
        )
        self.leeway_seconds = leeway_seconds

    def _create_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        normalized_user_id = user_id.strip()
        normalized_organization_id = (
            organization_id.strip()
        )

        if not normalized_user_id:
            raise ValueError(
                "user_id cannot be empty."
            )

        if not normalized_organization_id:
            raise ValueError(
                "organization_id cannot be empty."
            )

        now = datetime.now(timezone.utc)

        payload = {
            "sub": normalized_user_id,
            "organization_id": (
                normalized_organization_id
            ),
            "type": token_type,
            "jti": uuid4().hex,
            "iat": now,
            "exp": now + expires_delta,
            "iss": self.issuer,
            "aud": self.audience,
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def create_access_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        return self._create_token(
            user_id=user_id,
            organization_id=organization_id,
            token_type="access",
            expires_delta=(
                expires_delta
                or timedelta(
                    minutes=(
                        self.access_token_expire_minutes
                    )
                )
            ),
        )

    def create_refresh_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        return self._create_token(
            user_id=user_id,
            organization_id=organization_id,
            token_type="refresh",
            expires_delta=(
                expires_delta
                or timedelta(
                    days=(
                        self.refresh_token_expire_days
                    )
                )
            ),
        )

    def _decode_token(
        self,
        *,
        token: str,
        expected_type: str,
    ) -> dict:
        normalized_token = token.strip()

        if not normalized_token:
            raise AuthenticationError(
                message="The token is missing."
            )

        try:
            payload = jwt.decode(
                normalized_token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                leeway=self.leeway_seconds,
                options={
                    "require": [
                        "sub",
                        "organization_id",
                        "type",
                        "jti",
                        "iat",
                        "exp",
                        "iss",
                        "aud",
                    ]
                },
            )

        except ExpiredSignatureError:
            raise AuthenticationError(
                message="The token has expired."
            ) from None

        except InvalidTokenError:
            raise AuthenticationError(
                message="The token is invalid."
            ) from None

        if payload.get("type") != expected_type:
            raise AuthenticationError(
                message=(
                    f"The token is not a valid "
                    f"{expected_type} token."
                )
            )

        for claim_name in (
            "sub",
            "organization_id",
            "jti",
        ):
            claim_value = payload.get(claim_name)

            if (
                not isinstance(claim_value, str)
                or not claim_value
            ):
                raise AuthenticationError(
                    message=(
                        f"The token claim "
                        f"{claim_name} is invalid."
                    )
                )

        if not isinstance(payload.get("iat"), int):
            raise AuthenticationError(
                message="The token issue time is invalid."
            )

        if not isinstance(payload.get("exp"), int):
            raise AuthenticationError(
                message=(
                    "The token expiration is invalid."
                )
            )

        return payload

    def decode_access_token(
        self,
        token: str,
    ) -> AccessTokenClaims:
        payload = self._decode_token(
            token=token,
            expected_type="access",
        )

        return AccessTokenClaims(
            user_id=payload["sub"],
            organization_id=(
                payload["organization_id"]
            ),
            token_id=payload["jti"],
            token_type=payload["type"],
            issued_at=payload["iat"],
            expires_at=payload["exp"],
        )

    def decode_refresh_token(
        self,
        token: str,
    ) -> RefreshTokenClaims:
        payload = self._decode_token(
            token=token,
            expected_type="refresh",
        )

        return RefreshTokenClaims(
            user_id=payload["sub"],
            organization_id=(
                payload["organization_id"]
            ),
            token_id=payload["jti"],
            token_type=payload["type"],
            issued_at=payload["iat"],
            expires_at=payload["exp"],
        )


@lru_cache
def get_jwt_service() -> JWTService:
    return JWTService(
        secret_key=(
            settings.auth_jwt_secret_key
            .get_secret_value()
        ),
        algorithm=settings.auth_jwt_algorithm,
        issuer=settings.auth_jwt_issuer,
        audience=settings.auth_jwt_audience,
        access_token_expire_minutes=(
            settings
            .auth_access_token_expire_minutes
        ),
        refresh_token_expire_days=(
            settings.auth_refresh_token_expire_days
        ),
        leeway_seconds=(
            settings.auth_jwt_leeway_seconds
        ),
    )
