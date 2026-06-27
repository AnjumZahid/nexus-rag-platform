import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.jwt import JWTService
from backend.app.auth.passwords import PasswordService
from backend.app.core.config import settings
from backend.app.core.exceptions import (
    AuthenticationError,
    ConflictError,
)
from backend.app.database.models.auth import (
    UserRecord,
)
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)

from backend.app.auth.roles import OrganizationRole

from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    access_expires_in: int


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: str
    organization_id: str
    email: str
    full_name: str
    role: str
    is_active: bool


class AuthService:
    """Registration, login, refresh and logout."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: AuthRepository,
        password_service: PasswordService,
        jwt_service: JWTService,
    ) -> None:
        self.session = session
        self.repository = repository
        self.password_service = password_service
        self.jwt_service = jwt_service

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(
            timezone.utc
        ).replace(tzinfo=None)

    @staticmethod
    def _hash_refresh_token(
        token: str,
    ) -> str:
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _normalize_email(
        email: str,
    ) -> str:
        return email.strip().casefold()

    @staticmethod
    def _normalize_required_text(
        value: str,
        *,
        field_name: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    @staticmethod
    def _organization_slug(
        organization_name: str,
    ) -> str:
        base = re.sub(
            r"[^a-z0-9]+",
            "-",
            organization_name.casefold(),
        ).strip("-")

        if not base:
            base = "organization"

        return f"{base[:90]}-{uuid4().hex[:8]}"

    @staticmethod
    def _public_user(
        user: UserRecord,
    ) -> AuthenticatedUser:
        return AuthenticatedUser(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        )

    async def _issue_token_pair(
        self,
        user: UserRecord,
    ) -> TokenPair:
        access_token = (
            self.jwt_service.create_access_token(
                user_id=user.id,
                organization_id=(
                    user.organization_id
                ),
            )
        )

        refresh_token = (
            self.jwt_service.create_refresh_token(
                user_id=user.id,
                organization_id=(
                    user.organization_id
                ),
            )
        )

        claims = (
            self.jwt_service.decode_refresh_token(
                refresh_token
            )
        )

        expires_at = datetime.fromtimestamp(
            claims.expires_at,
            tz=timezone.utc,
        ).replace(tzinfo=None)

        await self.repository.create_refresh_token(
            user_id=user.id,
            organization_id=user.organization_id,
            token_id=claims.token_id,
            token_hash=self._hash_refresh_token(
                refresh_token
            ),
            expires_at=expires_at,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            access_expires_in=(
                settings
                .auth_access_token_expire_minutes
                * 60
            ),
        )

    async def register(
        self,
        *,
        organization_name: str,
        full_name: str,
        email: str,
        password: str,
    ) -> tuple[AuthenticatedUser, TokenPair]:
        organization_name = (
            self._normalize_required_text(
                organization_name,
                field_name="organization_name",
            )
        )

        full_name = self._normalize_required_text(
            full_name,
            field_name="full_name",
        )

        email = self._normalize_email(email)

        existing_user = (
            await self.repository.get_user_by_email(
                email
            )
        )

        if existing_user is not None:
            raise ConflictError(
                message=(
                    "An account with this email "
                    "already exists."
                )
            )

        password_hash = (
            self.password_service.hash_password(
                password
            )
        )

        try:
            organization = (
                await self.repository
                .create_organization(
                    name=organization_name,
                    slug=self._organization_slug(
                        organization_name
                    ),
                )
            )

            user = await self.repository.create_user(
                organization_id=organization.id,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=OrganizationRole.OWNER.value,
            )

            await self.repository.create_membership(
                user_id=user.id,
                organization_id=organization.id,
                role=OrganizationRole.OWNER.value,
            )

            tokens = await self._issue_token_pair(
                user
            )

            await self.session.commit()

            return self._public_user(user), tokens

        except IntegrityError:
            await self.session.rollback()

            raise ConflictError(
                message=(
                    "An account with this email "
                    "already exists."
                )
            ) from None

        except Exception:
            await self.session.rollback()
            raise

    async def login(
        self,
        *,
        email: str,
        password: str,
    ) -> tuple[AuthenticatedUser, TokenPair]:
        email = self._normalize_email(email)

        user = await self.repository.get_user_by_email(
            email
        )

        valid_password = (
            user is not None
            and self.password_service.verify_password(
                password=password,
                password_hash=user.password_hash,
            )
        )

        if not valid_password:
            raise AuthenticationError(
                message="Invalid email or password."
            )

        assert user is not None

        if not user.is_active:
            raise AuthenticationError(
                message="This account is inactive."
            )
        
        membership = await MembershipRepository(
            self.session
        ).get_active_membership(
            user_id=user.id,
            organization_id=user.organization_id,
        )

        if membership is None:
            raise AuthenticationError(
                message=(
                    "Your organization membership "
                    "is inactive."
                )
            )

        try:
            tokens = await self._issue_token_pair(
                user
            )

            await self.session.commit()

            return self._public_user(user), tokens

        except Exception:
            await self.session.rollback()
            raise

    async def refresh(
        self,
        *,
        refresh_token: str,
    ) -> tuple[AuthenticatedUser, TokenPair]:
        claims = (
            self.jwt_service.decode_refresh_token(
                refresh_token
            )
        )

        now = self._utc_now()

        try:
            record = (
                await self.repository
                .get_active_refresh_token_for_update(
                    token_hash=(
                        self._hash_refresh_token(
                            refresh_token
                        )
                    ),
                    now=now,
                )
            )

            if (
                record is None
                or record.token_id != claims.token_id
                or record.user_id != claims.user_id
                or record.organization_id
                != claims.organization_id
            ):
                raise AuthenticationError(
                    message=(
                        "The refresh token is invalid "
                        "or has already been used."
                    )
                )

            user = (
                await self.repository.get_user_by_id(
                    claims.user_id
                )
            )

            if user is None or not user.is_active:
                raise AuthenticationError(
                    message=(
                        "The user account is unavailable."
                    )
                )

            if (
                user.organization_id
                != claims.organization_id
            ):
                raise AuthenticationError(
                    message=(
                        "The refresh token organization "
                        "is invalid."
                    )
                )

            await self.repository.revoke_refresh_token(
                record=record,
                revoked_at=now,
            )

            tokens = await self._issue_token_pair(
                user
            )

            await self.session.commit()

            return self._public_user(user), tokens

        except Exception:
            await self.session.rollback()
            raise

    async def logout(
        self,
        *,
        refresh_token: str,
        user_id: str,
        organization_id: str,
    ) -> None:
        claims = (
            self.jwt_service.decode_refresh_token(
                refresh_token
            )
        )

        if (
            claims.user_id != user_id
            or claims.organization_id
            != organization_id
        ):
            raise AuthenticationError(
                message=(
                    "The refresh token does not "
                    "belong to this user."
                )
            )

        now = self._utc_now()

        try:
            record = (
                await self.repository
                .get_active_refresh_token_for_update(
                    token_hash=(
                        self._hash_refresh_token(
                            refresh_token
                        )
                    ),
                    now=now,
                )
            )

            if record is not None:
                await self.repository.revoke_refresh_token(
                    record=record,
                    revoked_at=now,
                )

            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise

    async def get_current_user(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> AuthenticatedUser:
        user = await self.repository.get_user_by_id(
            user_id
        )

        if (
            user is None
            or user.organization_id
            != organization_id
            or not user.is_active
        ):
            raise AuthenticationError(
                message=(
                    "The authenticated user "
                    "was not found."
                )
            )
        
        membership = await MembershipRepository(
            self.session
        ).get_active_membership(
            user_id=user.id,
            organization_id=organization_id,
        )

        if membership is None:
            raise AuthenticationError(
                message=(
                    "The organization membership "
                    "is inactive."
                )
            )

        return self._public_user(user)