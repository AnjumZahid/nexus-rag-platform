import asyncio
from uuid import uuid4

from sqlalchemy import delete

from backend.app.auth import (
    get_jwt_service,
    password_service,
)
from backend.app.auth.roles import OrganizationRole
from backend.app.auth.service import AuthService
from backend.app.core.exceptions import (
    AuthorizationError,
)
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
from backend.app.organizations.service import (
    OrganizationService,
)


async def main() -> None:
    suffix = uuid4().hex[:10]

    session_factory = get_session_factory()

    organization_id: str | None = None

    try:
        async with session_factory() as session:
            auth_repository = AuthRepository(session)

            owner, _ = await AuthService(
                session=session,
                repository=auth_repository,
                password_service=password_service,
                jwt_service=get_jwt_service(),
            ).register(
                organization_name=(
                    f"Role Test {suffix}"
                ),
                full_name="Role Test Owner",
                email=(
                    f"owner-{suffix}@example.com"
                ),
                password=(
                    "Strong-Owner-Password-123!"
                ),
            )

            organization_id = owner.organization_id

            organization_service = (
                OrganizationService(
                    session=session,
                    membership_repository=(
                        MembershipRepository(session)
                    ),
                    auth_repository=auth_repository,
                    password_service=password_service,
                )
            )

            member = (
                await organization_service.create_member(
                    actor_user_id=owner.id,
                    organization_id=organization_id,
                    full_name="Test Member",
                    email=(
                        f"member-{suffix}@example.com"
                    ),
                    password=(
                        "Strong-Member-Password-123!"
                    ),
                    role=OrganizationRole.MEMBER,
                )
            )

            assert (
                member.role
                == OrganizationRole.MEMBER.value
            )

            members = (
                await organization_service.list_members(
                    actor_user_id=owner.id,
                    organization_id=organization_id,
                )
            )

            assert len(members) == 2

            updated_member = (
                await organization_service
                .update_member_role(
                    actor_user_id=owner.id,
                    organization_id=organization_id,
                    membership_id=(
                        member.membership_id
                    ),
                    role=OrganizationRole.VIEWER,
                )
            )

            assert (
                updated_member.role
                == OrganizationRole.VIEWER.value
            )

            self_deactivation_rejected = False

            owner_membership = (
                await MembershipRepository(session)
                .get_active_membership(
                    user_id=owner.id,
                    organization_id=organization_id,
                )
            )

            assert owner_membership is not None

            try:
                await organization_service\
                    .deactivate_member(
                        actor_user_id=owner.id,
                        organization_id=organization_id,
                        membership_id=(
                            owner_membership.id
                        ),
                    )
            except AuthorizationError:
                self_deactivation_rejected = True

            assert self_deactivation_rejected is True

            await organization_service.deactivate_member(
                actor_user_id=owner.id,
                organization_id=organization_id,
                membership_id=member.membership_id,
            )

            inactive_membership = (
                await MembershipRepository(session)
                .get_active_membership(
                    user_id=member.user_id,
                    organization_id=organization_id,
                )
            )

            assert inactive_membership is None

            print(
                "\n=== ROLE AUTHORIZATION TEST ==="
            )
            print("Owner registration confirmed.")
            print("Member creation confirmed.")
            print("Member listing confirmed.")
            print("Role update confirmed.")
            print(
                "Owner self-deactivation rejected."
            )
            print(
                "Member deactivation confirmed."
            )
            print(
                "Role authorization test "
                "passed successfully."
            )

    finally:
        if organization_id is not None:
            async with session_factory() as cleanup:
                await cleanup.execute(
                    delete(
                        RefreshTokenRecord
                    ).where(
                        RefreshTokenRecord
                        .organization_id
                        == organization_id
                    )
                )

                await cleanup.execute(
                    delete(
                        OrganizationMembershipRecord
                    ).where(
                        OrganizationMembershipRecord
                        .organization_id
                        == organization_id
                    )
                )

                await cleanup.execute(
                    delete(UserRecord).where(
                        UserRecord.organization_id
                        == organization_id
                    )
                )

                await cleanup.execute(
                    delete(
                        OrganizationRecord
                    ).where(
                        OrganizationRecord.id
                        == organization_id
                    )
                )

                await cleanup.commit()

                print(
                    "Temporary role-test records "
                    "deleted."
                )

        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())