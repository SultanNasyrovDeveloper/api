from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command as alembic_command
from minager import settings
from minager.auth.models import User, UserProfile
from minager.core.settings.db import DBConnectionConfig


def _alembic_ini_path() -> str:
    return str(Path(settings.config.base_path).parent / 'alembic.ini')


@pytest.fixture(scope='session')
def postgres_original_config() -> DBConnectionConfig:
    return settings.config.main_db


@pytest.fixture(scope='session', autouse=True)
def postgres_test_config(
    postgres_original_config: DBConnectionConfig,
) -> Generator[DBConnectionConfig, None, None]:

    test_config = postgres_original_config.test
    test_engine = create_async_engine(test_config.to_str(), echo=False)
    test_session = async_sessionmaker(test_engine, expire_on_commit=False)

    original_engine = settings.main_db_engine
    original_session = settings.main_db
    settings.main_db_engine = test_engine
    settings.main_db = test_session
    settings.config.main_db = test_config

    yield settings.config.main_db

    settings.main_db = original_session
    settings.main_db_engine = original_engine
    settings.config.main_db = postgres_original_config


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


@pytest_asyncio.fixture(autouse=True)
async def postgres_db(postgres_db_setup: None) -> AsyncGenerator[None, None]:
    yield
    async with settings.main_db() as session:
        await session.execute(sa_delete(UserProfile))
        await session.execute(sa_delete(User))
        await session.commit()
