from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class OrganizationMembershipRecord(Base):
    """
    Connect a user to an organization with a role.

    A user may eventually belong to more than one
    organization.
    """

    __tablename__ = (
        "organization_membership_records"
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name=(
                "uq_organization_membership_"
                "organization_user"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "organization_records.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "user_records.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="member",
        server_default="member",
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        default=True,
        server_default=text("1"),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )