from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import PasswordService
from backend.app.auth.roles import OrganizationRole
from backend.app.core.exceptions import (
    AuthorizationError,
    ConflictError,
)
from backend.app.database.models.auth import (
    OrganizationRecord,
    UserRecord,
)
from backend.app.database.models.membership import (
    OrganizationMembershipRecord,
)
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)


@dataclass(frozen=True, slots=True)
class OrganizationSummary:
    id: str
    name: str
    slug: str
    current_role: str


@dataclass(frozen=True, slots=True)
class OrganizationMember:
    membership_id: str
    user_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class OrganizationService:
    """Organization membership management."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        membership_repository: MembershipRepository,
        auth_repository: AuthRepository,
        password_service: PasswordService,
    ) -> None:
        self.session = session
        self.membership_repository = (
            membership_repository
        )
        self.auth_repository = auth_repository
        self.password_service = password_service

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(
            timezone.utc
        ).replace(tzinfo=None)

    @staticmethod
    def _public_member(
        membership: OrganizationMembershipRecord,
        user: UserRecord,
    ) -> OrganizationMember:
        return OrganizationMember(
            membership_id=membership.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            is_active=membership.is_active,
            created_at=membership.created_at,
        )

    async def _require_actor(
        self,
        *,
        actor_user_id: str,
        organization_id: str,
    ) -> OrganizationMembershipRecord:
        membership = (
            await self.membership_repository
            .get_active_membership(
                user_id=actor_user_id,
                organization_id=organization_id,
            )
        )

        if membership is None:
            raise AuthorizationError(
                message=(
                    "An active organization membership "
                    "is required."
                )
            )

        return membership

    async def get_current_organization(
        self,
        *,
        actor_user_id: str,
        organization_id: str,
    ) -> OrganizationSummary:
        actor = await self._require_actor(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
        )

        organization = (
            await self.auth_repository
            .get_organization_by_id(
                organization_id
            )
        )

        if organization is None:
            raise AuthorizationError(
                message="The organization was not found."
            )

        return OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            current_role=actor.role,
        )

    async def list_members(
        self,
        *,
        actor_user_id: str,
        organization_id: str,
    ) -> list[OrganizationMember]:
        actor = await self._require_actor(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
        )

        if actor.role not in {
            OrganizationRole.OWNER.value,
            OrganizationRole.ADMIN.value,
        }:
            raise AuthorizationError(
                message=(
                    "Only owners and administrators "
                    "can list organization members."
                )
            )

        rows = (
            await self.membership_repository
            .list_organization_members(
                organization_id=organization_id
            )
        )

        return [
            self._public_member(membership, user)
            for membership, user in rows
        ]

    async def create_member(
        self,
        *,
        actor_user_id: str,
        organization_id: str,
        full_name: str,
        email: str,
        password: str,
        role: OrganizationRole,
    ) -> OrganizationMember:
        actor = await self._require_actor(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
        )

        if actor.role not in {
            OrganizationRole.OWNER.value,
            OrganizationRole.ADMIN.value,
        }:
            raise AuthorizationError(
                message=(
                    "Only owners and administrators "
                    "can create members."
                )
            )

        if role == OrganizationRole.OWNER:
            raise AuthorizationError(
                message=(
                    "New owners cannot be created "
                    "through this endpoint."
                )
            )

        if (
            actor.role == OrganizationRole.ADMIN.value
            and role == OrganizationRole.ADMIN
        ):
            raise AuthorizationError(
                message=(
                    "Administrators cannot create "
                    "other administrators."
                )
            )

        normalized_email = email.strip().casefold()
        normalized_name = full_name.strip()

        if not normalized_name:
            raise ValueError(
                "full_name cannot be empty."
            )

        existing_user = (
            await self.auth_repository
            .get_user_by_email(normalized_email)
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
            user = await self.auth_repository.create_user(
                organization_id=organization_id,
                email=normalized_email,
                password_hash=password_hash,
                full_name=normalized_name,
                role=role.value,
            )

            membership = (
                await self.membership_repository
                .create_membership(
                    user_id=user.id,
                    organization_id=organization_id,
                    role=role.value,
                )
            )

            await self.session.flush()
            await self.session.refresh(membership)

            member_response = self._public_member(
                membership,
                user,
            )

            await self.session.commit()

            return member_response

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

    async def update_member_role(
        self,
        *,
        actor_user_id: str,
        organization_id: str,
        membership_id: str,
        role: OrganizationRole,
    ) -> OrganizationMember:
        actor = await self._require_actor(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
        )

        if actor.role not in {
            OrganizationRole.OWNER.value,
            OrganizationRole.ADMIN.value,
        }:
            raise AuthorizationError(
                message=(
                    "Only owners and administrators "
                    "can update roles."
                )
            )

        if role == OrganizationRole.OWNER:
            raise AuthorizationError(
                message=(
                    "The owner role cannot be assigned "
                    "through this endpoint."
                )
            )

        try:
            target = (
                await self.membership_repository
                .get_membership_for_update(
                    membership_id=membership_id,
                    organization_id=organization_id,
                )
            )

            if target is None:
                raise AuthorizationError(
                    message="The membership was not found."
                )

            if target.user_id == actor_user_id:
                raise AuthorizationError(
                    message=(
                        "You cannot change your own role."
                    )
                )

            if target.role == OrganizationRole.OWNER.value:
                raise AuthorizationError(
                    message=(
                        "The organization owner role "
                        "cannot be changed."
                    )
                )

            if actor.role == OrganizationRole.ADMIN.value:
                if target.role == OrganizationRole.ADMIN.value:
                    raise AuthorizationError(
                        message=(
                            "Administrators cannot modify "
                            "other administrators."
                        )
                    )

                if role == OrganizationRole.ADMIN:
                    raise AuthorizationError(
                        message=(
                            "Administrators cannot assign "
                            "the administrator role."
                        )
                    )

            await self.membership_repository.set_role(
                membership=target,
                role=role.value,
            )

            user = await self.auth_repository.get_user_by_id(
                target.user_id
            )

            if user is None:
                raise AuthorizationError(
                    message="The member account was not found."
                )

            if user.organization_id == organization_id:
                user.role = role.value

            await self.session.commit()

            return self._public_member(target, user)

        except Exception:
            await self.session.rollback()
            raise

    async def deactivate_member(
        self,
        *,
        actor_user_id: str,
        organization_id: str,
        membership_id: str,
    ) -> None:
        actor = await self._require_actor(
            actor_user_id=actor_user_id,
            organization_id=organization_id,
        )

        if actor.role not in {
            OrganizationRole.OWNER.value,
            OrganizationRole.ADMIN.value,
        }:
            raise AuthorizationError(
                message=(
                    "Only owners and administrators "
                    "can deactivate members."
                )
            )

        try:
            target = (
                await self.membership_repository
                .get_membership_for_update(
                    membership_id=membership_id,
                    organization_id=organization_id,
                )
            )

            if target is None:
                raise AuthorizationError(
                    message="The membership was not found."
                )

            if target.user_id == actor_user_id:
                raise AuthorizationError(
                    message=(
                        "You cannot deactivate your own "
                        "membership."
                    )
                )

            if target.role == OrganizationRole.OWNER.value:
                raise AuthorizationError(
                    message=(
                        "The organization owner cannot "
                        "be deactivated."
                    )
                )

            if (
                actor.role == OrganizationRole.ADMIN.value
                and target.role
                == OrganizationRole.ADMIN.value
            ):
                raise AuthorizationError(
                    message=(
                        "Administrators cannot deactivate "
                        "other administrators."
                    )
                )

            await self.membership_repository\
                .deactivate_membership(
                    membership=target,
                    deactivated_at=self._utc_now(),
                )

            await self.session.commit()

        except Exception:
            await self.session.rollback()
            raise