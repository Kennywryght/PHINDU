"""
Alembic environment. Reads DATABASE_URL and model metadata from the app so
migrations always match the actual schema.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make `app` importable regardless of where alembic is invoked from ──
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ── Load app config + Base.metadata (which pulls in ALL models) ──
from app.core.config import DATABASE_URL          # noqa: E402
from app.db.session import Base                   # noqa: E402
import app.db.models  # noqa: F401,E402  (imports ALL models so metadata is complete)

# ── Alembic config object ──
config = context.config

# Inject DATABASE_URL from app config into Alembic's runtime config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# ── Logging setup from alembic.ini ──
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Metadata for autogenerate ──
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False}
        if DATABASE_URL.startswith("sqlite")
        else {},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # required for SQLite ALTERs
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()