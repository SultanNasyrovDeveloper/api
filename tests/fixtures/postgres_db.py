from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from alembic import command as alembic_command
from minager import settings
from minager.app import app
from minager.core.settings.db import DBConnectionConfig
from minager.dependencies import get_postgres_session


def _alembic_ini_path() -> str:
    return str(Path(settings.config.base_path).parent / 'alembic.ini')


@pytest.fixture(scope='session')
def postgres_test_config() -> DBConnectionConfig:
    test_config = settings.config.postgres.test
    if not test_config:
        raise ValueError('Unable to locate postgres database configuration for tests.')
    return test_config


@pytest.fixture(scope='session', autouse=True)
def postgres_db_setup(
    postgres_test_config: DBConnectionConfig,
) -> Generator[None, None, None]:
    db_name = postgres_test_config.name
    admin_url = postgres_test_config.to_str(scheme='postgresql+psycopg', path='/postgres')
    sync_url = postgres_test_config.to_str(scheme='postgresql+psycopg')
    admin_engine = create_engine(admin_url, isolation_level='AUTOCOMMIT')
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    admin_engine.dispose()

    alembic_cfg = AlembicConfig(_alembic_ini_path())
    alembic_cfg.set_main_option('sqlalchemy.url', sync_url)
    alembic_command.upgrade(alembic_cfg, 'head')

    yield

    admin_engine = create_engine(admin_url, isolation_level='AUTOCOMMIT')
    with admin_engine.connect() as conn:
        conn.execute(
            text(
                'SELECT pg_terminate_backend(pid) FROM pg_stat_activity'
                f" WHERE datname = '{db_name}' AND pid <> pg_backend_pid()"
            )
        )
        conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    admin_engine.dispose()


@pytest_asyncio.fixture(scope='session')
async def pg_engine(postgres_test_config: DBConnectionConfig, postgres_db_setup: None):
    engine = create_async_engine(postgres_test_config.to_str(), echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def pg_connection(pg_engine) -> AsyncGenerator:
    async with pg_engine.connect() as conn:
        await conn.begin()  # outer transaction — never committed
        yield conn
        await conn.rollback()  # rollback everything the test wrote


@pytest_asyncio.fixture()
async def pg_session(pg_connection) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(
        bind=pg_connection,
        expire_on_commit=False,
        join_transaction_mode='create_savepoint',  # session.commit() → SAVEPOINT / RELEASE SAVEPOINT
    )
    yield session
    await session.close()


@pytest_asyncio.fixture(autouse=True)
async def override_postgres_session(pg_session: AsyncSession) -> AsyncGenerator[None, None]:
    async def get_test_session():
        yield pg_session

    app.dependency_overrides[get_postgres_session] = get_test_session
    yield
    app.dependency_overrides.pop(get_postgres_session, None)
