import pytest
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from minager.auth.managers import UserManager, UserProfileManager

fake = Faker()


@pytest.fixture
def postgres_session(pg_session: AsyncSession) -> AsyncSession:
    return pg_session


@pytest.fixture
def user_manager(postgres_session: AsyncSession) -> UserManager:
    return UserManager(session=postgres_session)


@pytest.fixture
def user_profile_manager(postgres_session: AsyncSession) -> UserProfileManager:
    return UserProfileManager(session=postgres_session)


@pytest.fixture
def user_create_data() -> dict:
    return {'email': fake.email(), 'username': fake.user_name(), 'password': 'test_password'}
