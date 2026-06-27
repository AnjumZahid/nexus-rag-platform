from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.auth import (
    UserRecord,
)
from backend.app.database.models.membership import (
    OrganizationMembershipRecord,
)


class MembershipRepository:
    """Database operations for organization memberships."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_membership(
        self,
        *,
        user_id: str,
        organization_id: str,
        role: str,
    ) -> OrganizationMembershipRecord:
        membership = OrganizationMembershipRecord(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
            is_active=True,
        )

        self.session.add(membership)
        await self.session.flush()

        return membership

    async def get_membership(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> OrganizationMembershipRecord | None:
        result = await self.session.execute(
            select(
                OrganizationMembershipRecord
            ).where(
                OrganizationMembershipRecord.user_id
                == user_id,
                OrganizationMembershipRecord
                .organization_id
                == organization_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_active_membership(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> OrganizationMembershipRecord | None:
        result = await self.session.execute(
            select(
                OrganizationMembershipRecord
            ).where(
                OrganizationMembershipRecord.user_id
                == user_id,
                OrganizationMembershipRecord
                .organization_id
                == organization_id,
                OrganizationMembershipRecord.is_active
                .is_(True),
            )
        )

        return result.scalar_one_or_none()

    async def get_membership_for_update(
        self,
        *,
        membership_id: str,
        organization_id: str,
    ) -> OrganizationMembershipRecord | None:
        result = await self.session.execute(
            select(
                OrganizationMembershipRecord
            )
            .where(
                OrganizationMembershipRecord.id
                == membership_id,
                OrganizationMembershipRecord
                .organization_id
                == organization_id,
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def list_user_memberships(
        self,
        *,
        user_id: str,
    ) -> list[OrganizationMembershipRecord]:
        result = await self.session.execute(
            select(
                OrganizationMembershipRecord
            )
            .where(
                OrganizationMembershipRecord.user_id
                == user_id,
                OrganizationMembershipRecord.is_active
                .is_(True),
            )
            .order_by(
                OrganizationMembershipRecord.created_at
            )
        )

        return list(result.scalars().all())

    async def list_organization_members(
        self,
        *,
        organization_id: str,
    ) -> list[
        tuple[
            OrganizationMembershipRecord,
            UserRecord,
        ]
    ]:
        result = await self.session.execute(
            select(
                OrganizationMembershipRecord,
                UserRecord,
            )
            .join(
                UserRecord,
                UserRecord.id
                == OrganizationMembershipRecord.user_id,
            )
            .where(
                OrganizationMembershipRecord
                .organization_id
                == organization_id
            )
            .order_by(
                OrganizationMembershipRecord.created_at
            )
        )

        return [
            (membership, user)
            for membership, user in result.all()
        ]

    async def set_role(
        self,
        *,
        membership: OrganizationMembershipRecord,
        role: str,
    ) -> None:
        membership.role = role
        await self.session.flush()

    async def deactivate_membership(
        self,
        *,
        membership: OrganizationMembershipRecord,
        deactivated_at: datetime,
    ) -> None:
        membership.is_active = False
        membership.updated_at = deactivated_at

        await self.session.flush()