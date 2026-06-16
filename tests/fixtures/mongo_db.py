from asyncio import get_running_loop
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from minager import settings
from minager.app import app
from minager.dependencies import get_mongo_session
from minager.learning_session.managers import LearningSessionManager


@pytest_asyncio.fixture(scope='session')
async def mongo_test_client() -> AsyncGenerator[AsyncIOMotorClient, None]:
    client = AsyncIOMotorClient(settings.config.mongo.to_str(scheme='mongodb'))
    client.get_io_loop = get_running_loop
    yield client
    client.close()


@pytest.fixture(scope='session')
def mongo_test_db(mongo_test_client: AsyncIOMotorClient) -> AsyncIOMotorDatabase:
    # Uses the main database; clean_mongo_data wipes the session collection before each test.
    return mongo_test_client[settings.config.mongo.name]


@pytest_asyncio.fixture(autouse=True)
async def override_mongo_session(mongo_test_db: AsyncIOMotorDatabase) -> AsyncGenerator[None, None]:
    app.dependency_overrides[get_mongo_session] = lambda: mongo_test_db
    yield
    app.dependency_overrides.pop(get_mongo_session, None)


@pytest_asyncio.fixture(autouse=True)
async def clean_mongo_data(mongo_test_db: AsyncIOMotorDatabase) -> AsyncGenerator[None, None]:
    await mongo_test_db[LearningSessionManager.COLLECTION].delete_many({})
    yield
