import pytest
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from minager.core.auth.password import PasswordService
from minager.settings import password_hash
from minager.user.repositories import UserProfileRepository, UserRepository
from minager.user.services import UserProfileService, UserService

fake = Faker()


@pytest.fixture
def postgres_session(pg_session: AsyncSession) -> AsyncSession:
    return pg_session


@pytest.fixture
def user_repository(postgres_session: AsyncSession) -> UserRepository:
    return UserRepository(session=postgres_session)


@pytest.fixture
def user_profile_repository(postgres_session: AsyncSession) -> UserProfileRepository:
    return UserProfileRepository(session=postgres_session)


@pytest.fixture
def user_service(user_repository: UserRepository) -> UserService:
    return UserService(repository=user_repository, password_service=PasswordService(password_hash))


@pytest.fixture
def user_profile_service(user_profile_repository: UserProfileRepository) -> UserProfileService:
    return UserProfileService(repository=user_profile_repository)


@pytest.fixture
def user_create_data() -> dict:
    return {'email': fake.email(), 'username': fake.user_name(), 'password': 'test_password'}
