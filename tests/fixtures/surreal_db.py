from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from minager import settings
from minager.core import surorm
from minager.core.surorm.core.settings import SurrealConfig
from minager.node.managers import PalaceNodeManager


@pytest.fixture(scope='session')
def surreal_original_config() -> SurrealConfig:
    return settings.config.palace_node_db


@pytest.fixture(scope='session', autouse=True)
def surreal_test_config(surreal_original_config: SurrealConfig) -> Generator[SurrealConfig]:
    settings.config.palace_node_db = surreal_original_config.test
    yield settings.config.palace_node_db
    settings.config.palace_node_db = surreal_original_config


@pytest_asyncio.fixture(scope='session')
async def palace_node_setup_manager(
    surreal_test_config: SurrealConfig,
) -> AsyncGenerator[PalaceNodeManager, None]:
    async with PalaceNodeManager(surreal_test_config) as manager:
        yield manager


@pytest_asyncio.fixture(scope='session', autouse=True)
async def palace_node_db_setup(
    palace_node_setup_manager: PalaceNodeManager,
    surreal_original_config: SurrealConfig,
    surreal_test_config: SurrealConfig,
) -> AsyncGenerator[None, None]:
    await palace_node_setup_manager.query(
        surorm.DefineNamespace(surreal_test_config.namespace).if_not_exists(True)
    )
    await palace_node_setup_manager.query(
        surorm.DefineDatabase(surreal_test_config.name).if_not_exists(True)
    )
    await surorm.PerformMigrationCommand(
        palace_node_setup_manager, settings.config.base_path
    ).upgrade()
    yield
    await palace_node_setup_manager.query(
        surorm.Remove('database', surreal_test_config.name).if_exists(True)
    )
    if surreal_test_config.namespace != surreal_original_config.namespace:
        await palace_node_setup_manager.query(
            surorm.Remove('namespace', surreal_test_config.namespace).if_exists(True)
        )


@pytest_asyncio.fixture()
async def test_palace_node_manager(
    palace_node_db_setup: None,
    surreal_test_config: SurrealConfig,
) -> AsyncGenerator[PalaceNodeManager, None]:
    async with PalaceNodeManager(surreal_test_config) as manager:
        yield manager


@pytest_asyncio.fixture(autouse=True)
async def palace_node_db(
    test_palace_node_manager: PalaceNodeManager,
) -> AsyncGenerator[None, None]:
    yield
    await test_palace_node_manager.query(surorm.Delete('node'))
    await test_palace_node_manager.query(surorm.Delete('child'))
