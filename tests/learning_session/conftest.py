from collections.abc import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from surorm import Session
from surrealdb import AsyncWsSurrealConnection

from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.learning_session.models import LearningSession
from minager.learning_session.repositories import LearningSessionRepository
from minager.learning_session.services import LearningSessionService
from minager.learning_session.use_cases import (
    PerformRepetitionUseCase,
    RegenerateQueueUseCase,
    StartSessionUseCase,
)
from minager.node.models import Node
from minager.node.services import NodeService
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
def test_knowledge_tree_client(surreal_test_connection: AsyncWsSurrealConnection) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(session=Session(connection=surreal_test_connection))


@pytest.fixture()
def test_learning_session_repository(mongo_test_db: AsyncIOMotorDatabase) -> LearningSessionRepository:
    return LearningSessionRepository(connection=mongo_test_db[LearningSessionRepository.COLLECTION])


@pytest.fixture()
def test_learning_session_service(
    test_learning_session_repository: LearningSessionRepository,
) -> LearningSessionService:
    return LearningSessionService(repository=test_learning_session_repository)


@pytest.fixture()
def test_start_session_use_case(
    test_learning_session_repository: LearningSessionRepository,
    test_learning_session_service: LearningSessionService,
    test_knowledge_tree_client: KnowledgeTreeClient,
) -> StartSessionUseCase:
    return StartSessionUseCase(
        repository=test_learning_session_repository,
        service=test_learning_session_service,
        knowledge_tree_client=test_knowledge_tree_client,
    )


@pytest.fixture()
def test_regenerate_queue_use_case(
    test_learning_session_repository: LearningSessionRepository,
    test_knowledge_tree_client: KnowledgeTreeClient,
) -> RegenerateQueueUseCase:
    return RegenerateQueueUseCase(
        repository=test_learning_session_repository,
        knowledge_tree_client=test_knowledge_tree_client,
    )


@pytest.fixture()
def test_perform_repetition_use_case(
    test_learning_session_repository: LearningSessionRepository,
    test_knowledge_tree_client: KnowledgeTreeClient,
) -> PerformRepetitionUseCase:
    return PerformRepetitionUseCase(
        repository=test_learning_session_repository,
        knowledge_tree_client=test_knowledge_tree_client,
    )


@pytest_asyncio.fixture()
async def active_session(
    test_start_session_use_case: StartSessionUseCase,
    test_palace_node_service: NodeService,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    node_data_factory: Callable[..., dict],
) -> AsyncGenerator[LearningSession, None]:
    for _ in range(3):
        await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data={'targets': [test_user_root_node.id.id_]},
    )
    yield session
