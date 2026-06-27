import asyncio
from uuid import uuid4

from sqlalchemy import delete

from backend.app.auth import (
    get_jwt_service,
    password_service,
)
from backend.app.auth.roles import OrganizationRole
from backend.app.auth.service import AuthService
from backend.app.database.models.auth import (
    OrganizationRecord,
    RefreshTokenRecord,
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
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)


async def main() -> None:
    suffix = uuid4().hex[:10]

    email = (
        f"membership-{suffix}@example.com"
    )

    password = (
        "Strong-Membership-Password-123!"
    )

    session_factory = get_session_factory()

    created_user_id: str | None = None

    created_organization_id: str | None = None

    try:
        async with session_factory() as session:
            auth_service = AuthService(
                session=session,
                repository=AuthRepository(session),
                password_service=password_service,
                jwt_service=get_jwt_service(),
            )

            user, tokens = await auth_service.register(
                organization_name=(
                    f"Membership Test {suffix}"
                ),
                full_name="Membership Owner",
                email=email,
                password=password,
            )

            created_user_id = user.id

            created_organization_id = (
                user.organization_id
            )

            membership_repository = (
                MembershipRepository(session)
            )

            membership = (
                await membership_repository
                .get_active_membership(
                    user_id=user.id,
                    organization_id=(
                        user.organization_id
                    ),
                )
            )

            assert membership is not None

            assert membership.user_id == user.id

            assert (
                membership.organization_id
                == user.organization_id
            )

            assert (
                membership.role
                == OrganizationRole.OWNER.value
            )

            assert membership.is_active is True

            assert tokens.access_token

            user_memberships = (
                await membership_repository
                .list_user_memberships(
                    user_id=user.id
                )
            )

            assert len(user_memberships) == 1

            assert (
                user_memberships[0].id
                == membership.id
            )

            print(
                "\n=== MEMBERSHIP FOUNDATION TEST ==="
            )
            print(
                "Organization registration confirmed."
            )
            print(
                "Owner user registration confirmed."
            )
            print(
                "Owner membership creation confirmed."
            )
            print(
                "Active membership lookup confirmed."
            )
            print(
                "User membership listing confirmed."
            )
            print(
                "Membership foundation test "
                "passed successfully."
            )

    finally:
        if created_organization_id is not None:
            async with session_factory() as cleanup:
                await cleanup.execute(
                    delete(
                        RefreshTokenRecord
                    ).where(
                        RefreshTokenRecord
                        .organization_id
                        == created_organization_id
                    )
                )

                await cleanup.execute(
                    delete(
                        OrganizationMembershipRecord
                    ).where(
                        OrganizationMembershipRecord
                        .organization_id
                        == created_organization_id
                    )
                )

                if created_user_id is not None:
                    await cleanup.execute(
                        delete(UserRecord).where(
                            UserRecord.id
                            == created_user_id
                        )
                    )

                await cleanup.execute(
                    delete(
                        OrganizationRecord
                    ).where(
                        OrganizationRecord.id
                        == created_organization_id
                    )
                )

                await cleanup.commit()

                print(
                    "Temporary membership records "
                    "deleted."
                )

        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())

# uv run python -m tests.test_membership_foundation