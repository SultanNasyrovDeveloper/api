from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from faker import Faker

from minager.auth.managers import UserManager, UserProfileManager

fake = Faker()


@pytest_asyncio.fixture
async def user_manager() -> AsyncGenerator[UserManager]:
    async with UserManager() as user_manager:
        yield user_manager


@pytest_asyncio.fixture
async def user_profile_manager() -> AsyncGenerator[UserProfileManager]:
    async with UserProfileManager() as manager:
        yield manager


@pytest.fixture
def user_create_data() -> dict:
    """Generate random user creation data"""
    return {'email': fake.email(), 'username': fake.user_name(), 'password': 'test_password'}
