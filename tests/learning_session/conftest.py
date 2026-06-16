from collections.abc import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from surrealdb import AsyncWsSurrealConnection

from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.learning_session.managers import LearningSessionManager
from minager.learning_session.models import LearningSession
from minager.node.managers import KnowledgeTreeNodeManager
from minager.node.models import Node
from tests.conftest import UserTestContext


@pytest.fixture()
def node_data_factory(test_user_context: UserTestContext) -> Callable[..., dict]:
    counter = 0

    def _factory(**kwargs) -> dict:
        nonlocal counter
        counter += 1
        return {
            'title': f'Test Node {counter}',
            'questions': 'What is this?',
            'owner_id': str(test_user_context.sub),
            'content': '{"root": {}}',
            'order': 'aaaaa',
            **kwargs,
        }

    return _factory


@pytest.fixture()
def test_learning_session_manager(
    mongo_test_db: AsyncIOMotorDatabase,
    surreal_test_connection: AsyncWsSurrealConnection,
) -> LearningSessionManager:
    return LearningSessionManager(
        connection=mongo_test_db[LearningSessionManager.COLLECTION],
        knowledge_tree_client=KnowledgeTreeClient(connection=surreal_test_connection),
    )


@pytest_asyncio.fixture()
async def active_session(
    test_learning_session_manager: LearningSessionManager,
    test_palace_node_manager: KnowledgeTreeNodeManager,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    node_data_factory: Callable[..., dict],
) -> AsyncGenerator[LearningSession, None]:
    for _ in range(3):
        await test_palace_node_manager.add_child(test_user_root_node.pk, node_data_factory())
    session = await test_learning_session_manager.start(
        user_id=str(test_user_context.sub),
        data={'target': test_user_root_node.id.id},
    )
    yield session
