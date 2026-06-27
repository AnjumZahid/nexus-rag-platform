from enum import StrEnum


class OrganizationRole(StrEnum):
    """Roles available inside an organization."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ORGANIZATION_ROLES = frozenset(
    role.value for role in OrganizationRole
)


DOCUMENT_WRITE_ROLES = frozenset(
    {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
    }
)


DOCUMENT_READ_ROLES = frozenset(
    {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
        OrganizationRole.VIEWER,
    }
)


MEMBER_MANAGEMENT_ROLES = frozenset(
    {
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
    }
)