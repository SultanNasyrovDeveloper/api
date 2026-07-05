from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from minager.settings import ApplicationConfig
from minager.user.models import Model

alembic_config = context.config

if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)


# Allow test fixtures (or CI) to inject a URL by setting it programmatically
# on the config object before calling alembic.command.upgrade().
# If no URL has been set yet, fall back to the application settings.
if not alembic_config.get_main_option('sqlalchemy.url'):
    app_settings = ApplicationConfig()
    alembic_config.set_main_option('sqlalchemy.url', app_settings.main_db.to_str(scheme='postgresql+psycopg'))
target_metadata = [Model.metadata]


def run_migrations_offline() -> None:
    """Run alembic in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = alembic_config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run alembic in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        alembic_config.get_section(alembic_config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
