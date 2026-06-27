
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from backend.app.core.config import settings
from backend.app.core.exceptions import ConfigurationError
from backend.app.database.base import Base

# These imports register the models inside Base.metadata.
from backend.app.database.models import (  # noqa: F401
    DocumentChunkRecord,
    DocumentRecord,
    OrganizationRecord,
    RefreshTokenRecord,
    UserRecord,
    OrganizationMembershipRecord,
)


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def get_database_url() -> str:
    """Read the async MySQL URL from application settings."""

    if settings.database_url is None:
        raise ConfigurationError(
            message="DATABASE_URL is missing from the environment."
        )

    return settings.database_url.get_secret_value()


def run_migrations_offline() -> None:
    """
    Generate SQL without opening a database connection.
    """

    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using the provided synchronous connection wrapper."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and execute migrations."""

    engine = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,
    )

    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations against the connected MySQL database."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
