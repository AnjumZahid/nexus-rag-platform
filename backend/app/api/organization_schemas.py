from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)

from backend.app.auth.roles import OrganizationRole


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    current_role: OrganizationRole


class CreateOrganizationMemberRequest(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=255,
    )

    email: EmailStr

    password: str = Field(
        min_length=12,
        max_length=128,
    )

    role: OrganizationRole = (
        OrganizationRole.MEMBER
    )


class UpdateOrganizationMemberRoleRequest(
    BaseModel
):
    role: OrganizationRole


class OrganizationMemberResponse(BaseModel):
    membership_id: str
    user_id: str
    email: EmailStr
    full_name: str
    role: OrganizationRole
    is_active: bool
    created_at: datetime


class OrganizationMemberListResponse(BaseModel):
    members: list[OrganizationMemberResponse]
    total: int