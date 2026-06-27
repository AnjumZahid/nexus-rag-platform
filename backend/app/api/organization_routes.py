from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_db_session,
    get_organization_access,
    require_organization_roles,
)
from backend.app.api.organization_schemas import (
    CreateOrganizationMemberRequest,
    OrganizationMemberListResponse,
    OrganizationMemberResponse,
    OrganizationResponse,
    UpdateOrganizationMemberRoleRequest,
)
from backend.app.auth import password_service
from backend.app.auth.roles import OrganizationRole
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)
from backend.app.organizations.service import (
    OrganizationMember,
    OrganizationService,
)


router = APIRouter(
    prefix="/organizations/current",
    tags=["Organizations"],
)


require_member_management = (
    require_organization_roles(
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    )
)


def build_organization_service(
    session: AsyncSession,
) -> OrganizationService:
    return OrganizationService(
        session=session,
        membership_repository=(
            MembershipRepository(session)
        ),
        auth_repository=AuthRepository(session),
        password_service=password_service,
    )


def build_member_response(
    member: OrganizationMember,
) -> OrganizationMemberResponse:
    return OrganizationMemberResponse(
        membership_id=member.membership_id,
        user_id=member.user_id,
        email=member.email,
        full_name=member.full_name,
        role=OrganizationRole(member.role),
        is_active=member.is_active,
        created_at=member.created_at,
    )


@router.get(
    "",
    response_model=OrganizationResponse,
)
async def get_current_organization(
    access: Annotated[
        OrganizationAccess,
        Depends(get_organization_access),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> OrganizationResponse:
    organization = await build_organization_service(
        session
    ).get_current_organization(
        actor_user_id=access.user_id,
        organization_id=access.organization_id,
    )

    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        current_role=OrganizationRole(
            organization.current_role
        ),
    )


@router.get(
    "/members",
    response_model=OrganizationMemberListResponse,
)
async def list_members(
    access: Annotated[
        OrganizationAccess,
        Depends(require_member_management),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> OrganizationMemberListResponse:
    members = await build_organization_service(
        session
    ).list_members(
        actor_user_id=access.user_id,
        organization_id=access.organization_id,
    )

    return OrganizationMemberListResponse(
        members=[
            build_member_response(member)
            for member in members
        ],
        total=len(members),
    )


@router.post(
    "/members",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_member(
    request: CreateOrganizationMemberRequest,
    access: Annotated[
        OrganizationAccess,
        Depends(require_member_management),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> OrganizationMemberResponse:
    member = await build_organization_service(
        session
    ).create_member(
        actor_user_id=access.user_id,
        organization_id=access.organization_id,
        full_name=request.full_name,
        email=str(request.email),
        password=request.password,
        role=request.role,
    )

    return build_member_response(member)


@router.patch(
    "/members/{membership_id}/role",
    response_model=OrganizationMemberResponse,
)
async def update_member_role(
    membership_id: str,
    request: UpdateOrganizationMemberRoleRequest,
    access: Annotated[
        OrganizationAccess,
        Depends(require_member_management),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> OrganizationMemberResponse:
    member = await build_organization_service(
        session
    ).update_member_role(
        actor_user_id=access.user_id,
        organization_id=access.organization_id,
        membership_id=membership_id,
        role=request.role,
    )

    return build_member_response(member)


@router.delete(
    "/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deactivate_member(
    membership_id: str,
    access: Annotated[
        OrganizationAccess,
        Depends(require_member_management),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db_session),
    ],
) -> Response:
    await build_organization_service(
        session
    ).deactivate_member(
        actor_user_id=access.user_id,
        organization_id=access.organization_id,
        membership_id=membership_id,
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )