from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from surrealdb import AsyncSurreal

from minager import settings
from minager.app import app
from minager.core import surorm
from minager.core.surorm.core.settings import SurrealConfig
from minager.core.surorm.orm.managers import Manager as SurrealManager
from minager.dependencies import get_surreal_connection
from minager.node.managers import KnowledgeTreeNodeManager
from minager.node.models import Node
from minager.user.schemas import UserWithProfileSchema


@pytest.fixture(scope='session')
def surreal_test_config() -> SurrealConfig:
    test_config = settings.config.surreal.test
    if not test_config:
        raise ValueError('Unable to locate knowledge tree database configuration for tests.')
    return test_config


@pytest_asyncio.fixture(scope='session')
async def surreal_test_connection(surreal_test_config: SurrealConfig) -> AsyncGenerator:
    conn = AsyncSurreal(f'ws://{surreal_test_config.host}:{surreal_test_config.port}')
    credentials = {
        'username': surreal_test_config.username,
        'password': surreal_test_config.password.get_secret_value(),
    }
    await conn.connect()
    await conn.signin(credentials)
    await conn.use(namespace=surreal_test_config.namespace, database=surreal_test_config.name)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope='session', autouse=True)
async def palace_node_db_setup(
    surreal_test_connection,
    surreal_test_config: SurrealConfig,
) -> AsyncGenerator[None, None]:
    setup_manager = SurrealManager(connection=surreal_test_connection)
    await setup_manager.query(surorm.DefineNamespace(surreal_test_config.namespace).if_not_exists(True))
    await setup_manager.query(surorm.DefineDatabase(surreal_test_config.name).if_not_exists(True))
    await surorm.PerformMigrationCommand(setup_manager, settings.config.base_path).upgrade()
    yield
    await setup_manager.query(surorm.Remove('database', surreal_test_config.name).if_exists(True))
    if surreal_test_config.namespace != settings.config.surreal.namespace:
        await setup_manager.query(surorm.Remove('namespace', surreal_test_config.namespace).if_exists(True))


@pytest.fixture()
def test_palace_node_manager(
    surreal_test_connection,
    palace_node_db_setup: None,
) -> KnowledgeTreeNodeManager:
    return KnowledgeTreeNodeManager(connection=surreal_test_connection)


@pytest_asyncio.fixture(autouse=True)
async def override_surreal_connection(surreal_test_connection) -> AsyncGenerator[None, None]:
    app.dependency_overrides[get_surreal_connection] = lambda: surreal_test_connection
    yield
    app.dependency_overrides.pop(get_surreal_connection, None)


@pytest_asyncio.fixture(autouse=True)
async def clean_surreal_data(
    surreal_test_connection,
    palace_node_db_setup: None,
) -> AsyncGenerator[None, None]:
    await surreal_test_connection.query('DELETE node; DELETE child;')
    yield


@pytest_asyncio.fixture
async def test_user_root_node(
    test_palace_node_manager: KnowledgeTreeNodeManager,
    test_user: UserWithProfileSchema,
) -> AsyncGenerator[Node, None]:
    assert test_user.knowledge_tree_root_id
    root_node = await test_palace_node_manager.get(test_user.knowledge_tree_root_id)
    if not root_node:
        raise ValueError('Unable to find root node for test.')
    yield root_node
