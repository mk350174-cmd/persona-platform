import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so autogenerate detects schema changes
from api.db import Base  # noqa: E402
target_metadata = Base.metadata

# Override URL from env var (DATABASE_URL wins over alembic.ini)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./persona_store.db")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

_IS_SQLITE = DATABASE_URL.startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_IS_SQLITE,  # SQLite needs batch mode for ALTER TABLE
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connect_args = {"check_same_thread": False} if _IS_SQLITE else {}
    connectable = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_IS_SQLITE,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
