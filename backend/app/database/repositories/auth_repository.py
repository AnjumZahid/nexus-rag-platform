## New file: `backend/app/database/repositories/auth_repository.py`

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.auth import (
    OrganizationRecord,
    RefreshTokenRecord,
    UserRecord,
)

from backend.app.database.models.membership import (
    OrganizationMembershipRecord,
)


class AuthRepository:
    """Database operations for authentication."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_user_by_email(
        self,
        email: str,
    ) -> UserRecord | None:
        result = await self.session.execute(
            select(UserRecord).where(
                UserRecord.email == email
            )
        )

        return result.scalar_one_or_none()

    async def get_user_by_id(
        self,
        user_id: str,
    ) -> UserRecord | None:
        return await self.session.get(
            UserRecord,
            user_id,
        )
    
    async def get_organization_by_id(
        self,
        organization_id: str,
    ) -> OrganizationRecord | None:
        return await self.session.get(
            OrganizationRecord,
            organization_id,
        )
    

    async def create_organization(
        self,
        *,
        name: str,
        slug: str,
    ) -> OrganizationRecord:
        organization = OrganizationRecord(
            name=name,
            slug=slug,
        )

        self.session.add(organization)
        await self.session.flush()

        return organization

    async def create_user(
        self,
        *,
        organization_id: str,
        email: str,
        password_hash: str,
        full_name: str,
        role: str = "owner",
    ) -> UserRecord:
        user = UserRecord(
            organization_id=organization_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=True,
        )

        self.session.add(user)
        await self.session.flush()

        return user
    
    async def create_membership(
        self,
        *,
        user_id: str,
        organization_id: str,
        role: str,
    ) -> OrganizationMembershipRecord:
        """Create a user's organization membership."""

        membership = OrganizationMembershipRecord(
            user_id=user_id,
            organization_id=organization_id,
            role=role,
            is_active=True,
        )

        self.session.add(membership)
        await self.session.flush()

        return membership

    async def create_refresh_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        token_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshTokenRecord:
        record = RefreshTokenRecord(
            user_id=user_id,
            organization_id=organization_id,
            token_id=token_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self.session.add(record)
        await self.session.flush()

        return record

    async def get_active_refresh_token_for_update(
        self,
        *,
        token_hash: str,
        now: datetime,
    ) -> RefreshTokenRecord | None:
        result = await self.session.execute(
            select(RefreshTokenRecord)
            .where(
                RefreshTokenRecord.token_hash
                == token_hash,
                RefreshTokenRecord.revoked_at.is_(
                    None
                ),
                RefreshTokenRecord.expires_at
                > now,
            )
            .with_for_update()
        )

        return result.scalar_one_or_none()

    async def revoke_refresh_token(
        self,
        *,
        record: RefreshTokenRecord,
        revoked_at: datetime,
    ) -> None:
        record.revoked_at = revoked_at
        await self.session.flush()


    

