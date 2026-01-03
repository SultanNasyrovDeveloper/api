import jwt
import pytest
from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from alembic.config import Config
from minager.app import app
from minager.auth.managers import UserManager, UserProfileManager
from minager.settings import config


@pytest.fixture
def fake():
    return Faker()


# ============================================================================
# PostgreSQL Test Database Setup
# ============================================================================
@pytest.fixture(scope='session')
async def main_db_test_engine():
    default_db_url = config.main_db.to_str(path='/postgres')
    default_engine = create_async_engine(default_db_url, isolation_level='AUTOCOMMIT')
    test_db_name = config.main_db.name
    async with default_engine.connect() as conn:
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{test_db_name}'")
        )
        exists = result.scalar()
        if not exists:
            await conn.execute(text(f'CREATE DATABASE {test_db_name}'))
    await default_engine.dispose()
    test_db_url = config.main_db.to_str()
    test_engine = create_async_engine(test_db_url, echo=False)
    alembic_cfg = Config('alembic.ini')
    alembic_cfg.set_main_option(
        'sqlalchemy.url', config.main_db.to_str(scheme='postgresql+asyncpg')
    )
    command.upgrade(alembic_cfg, 'head')
    yield test_engine
    await test_engine.dispose()
    default_engine = create_async_engine(default_db_url, isolation_level='AUTOCOMMIT')
    async with default_engine.connect() as conn:
        await conn.execute(
            text(
                f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_db_name}'
                AND pid <> pg_backend_pid()
                """
            )
        )
        await conn.execute(text(f'DROP DATABASE IF EXISTS {test_db_name}'))
    await default_engine.dispose()


@pytest.fixture(scope='session', autouse=True)
def main_db_test_session_factory(main_db_test_engine):
    """Creates async session factory for test database"""
    return async_sessionmaker(main_db_test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
async def main_db(main_db_test_session_factory):
    """Provides a database session with automatic rollback after each test"""
    async with main_db_test_session_factory() as session:
        yield session
        await session.rollback()


# ============================================================================
# Auth Fixtures
# ============================================================================
@pytest.fixture
async def test_user(main_db, fake):
    """Creates a test user in the database with profile"""
    user_manager = UserManager()
    username = fake.user_name()
    user_data = UserCreate(email=fake.email(), password='TestPassword123!', username=username)
    user = await user_manager.create_user(user_data, session=main_db)
    await main_db.commit()

    # Create user profile
    profile_manager = UserProfileManager()
    profile_data = UserProfileCreate(user_id=user.id, username=username)
    await profile_manager.create_profile(profile_data, session=main_db)
    await main_db.commit()

    user.plain_password = 'TestPassword123!'
    user.username = username
    return user


@pytest.fixture
def api_user():
    """Mock user data for JWT token"""
    return {'id': 'test_user', 'sub': 'test_user'}


@pytest.fixture
def unauthorized_api_client(api_user):
    """Test client with bearer token authentication"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def api_client(api_user):
    """Test client with bearer token authentication"""
    token = jwt.encode(
        api_user, config.secret_key.get_secret_value(), algorithm=config.jwt_hashing_algorithm
    )
    with TestClient(app, headers={'Authorization': f'Bearer {token}'}) as client:
        yield client
