from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from minager import settings
from minager.app import app
from minager.core import surorm
from minager.node.managers import PalaceNodeManager


@pytest.fixture(scope='session')
def original_config() -> settings.ApplicationConfig:
    """Returns the production SurrealDB config before any test patching."""
    return settings.config


@pytest.fixture(scope='session', autouse=True)
def test_config(
    original_config: settings.ApplicationConfig,
) -> Generator[settings.ApplicationConfig]:
    """
    Patches the global config singleton so the app lifespan boots with the
    test database. Must run before the app is started (i.e. before app_client).
    """
    settings.config.palace_node_db = original_config.palace_node_db.test
    yield settings.config
    settings.config.palace_node_db = original_config.palace_node_db


@pytest_asyncio.fixture(scope='session')
async def setup_manager(
    test_config: settings.ApplicationConfig,
) -> AsyncGenerator[PalaceNodeManager, None]:
    """
    A dedicated manager used ONLY for session-scoped setup/teardown.
    This runs in the session's event loop.
    """
    async with PalaceNodeManager(settings.config.palace_node_db) as manager:
        yield manager


@pytest_asyncio.fixture(scope='session', autouse=True)
async def palace_node_db_setup(
    setup_manager: PalaceNodeManager,
    original_config: settings.ApplicationConfig,
    test_config: settings.ApplicationConfig,
) -> AsyncGenerator[None]:
    """
    Session-scoped setup. Ensures the test namespace and database exist,
    then runs all pending migrations once for the whole session.
    Drops the test database on teardown, and the test namespace too if it
    differs from the production namespace.
    """
    production_config = original_config.palace_node_db
    config = test_config.palace_node_db
    await setup_manager.query(surorm.DefineNamespace(config.namespace).if_not_exists(True))
    await setup_manager.query(surorm.DefineDatabase(config.name).if_not_exists(True))
    await surorm.PerformMigrationCommand(setup_manager, settings.config.base_path).upgrade()
    yield
    await setup_manager.query(surorm.Remove('database', config.name).if_exists(True))
    if config.namespace != production_config.namespace:
        await setup_manager.query(surorm.Remove('namespace', config.namespace).if_exists(True))


@pytest_asyncio.fixture()
async def test_palace_node_manager(
    palace_node_db_setup: None,
) -> AsyncGenerator[PalaceNodeManager, None]:
    """
    A dedicated manager used ONLY for session-scoped setup/teardown.
    This runs in the session's event loop.
    """
    async with PalaceNodeManager(settings.config.palace_node_db) as manager:
        yield manager


@pytest_asyncio.fixture(autouse=True)
async def palace_node_db(test_palace_node_manager: PalaceNodeManager) -> AsyncGenerator[None]:
    """
    Function-scoped fixture. Yields the shared manager and wipes all test
    data after each test so every test starts with a clean state.
    """
    yield
    await test_palace_node_manager.query(surorm.Delete('node'))
    await test_palace_node_manager.query(surorm.Delete('child'))


@pytest_asyncio.fixture(scope='session')
async def app_client(palace_node_db_setup: None) -> AsyncGenerator[AsyncClient, None]:
    """
    Session-scoped httpx client using ASGI transport against the full FastAPI app.
    Depends on palace_node_db_setup to guarantee that the test database and all
    migrations are in place before the app lifespan starts.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        yield client
