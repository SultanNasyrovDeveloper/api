from collections.abc import AsyncGenerator, Callable
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase
from surorm import Session
from surrealdb import AsyncWsSurrealConnection

from minager.app import app
from minager.core.auth.dependencies import jwt_service
from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.node.models import Node
from minager.node.services import NodeService
from minager.repetition_assistant.dependencies import get_chat_review_client
from minager.repetition_assistant.enums import MessageType
from minager.repetition_assistant.models import (
    AssistantMessage,
    AssistantVerdictMessage,
    Message,
)
from minager.repetition_assistant.repositories import AssistantReviewConversationRepository
from minager.repetition_assistant.use_cases import SendMessageUseCase
from tests.conftest import UserTestContext


class StubChatReviewClient:
    """Scripted stand-in for the real langchain-backed ChatReviewClient.

    Returns a question every turn, or a verdict whenever ``force_verdict`` is set. Records
    each call so tests can assert what the use case asked for (message history, force flag).
    """

    def __init__(self):
        self.question = AssistantMessage(type=MessageType.question, content='Can you explain more?')
        self.verdict = AssistantVerdictMessage(rating=4, topics_to_add=['subtopic'])
        self.calls: list[SimpleNamespace] = []

    async def generate(
        self, node: Node, messages: list[Message], *, force_verdict: bool = False
    ) -> AssistantMessage | AssistantVerdictMessage:
        self.calls.append(SimpleNamespace(node=node, messages=list(messages), force_verdict=force_verdict))
        return self.verdict if force_verdict else self.question


@pytest.fixture()
def stub_chat_client() -> StubChatReviewClient:
    return StubChatReviewClient()


@pytest.fixture()
def other_user_auth_headers() -> dict[str, str]:
    """Auth headers for an unrelated user (CurrentUserID is pure-JWT, no DB lookup)."""
    token = jwt_service.create_access_token(uuid4())
    return {'Authorization': f'Bearer {token}'}


@pytest_asyncio.fixture(autouse=True)
async def override_chat_client(stub_chat_client: StubChatReviewClient) -> AsyncGenerator[None, None]:
    app.dependency_overrides[get_chat_review_client] = lambda: stub_chat_client
    yield
    app.dependency_overrides.pop(get_chat_review_client, None)


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
            'content': '<p>Some node content</p>',
            'order': 'aaaaa',
            **kwargs,
        }

    return _factory


@pytest.fixture()
def test_knowledge_tree_client(
    surreal_test_connection: AsyncWsSurrealConnection,
) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(session=Session(connection=surreal_test_connection))


@pytest.fixture()
def test_assistant_review_conversation_repository(
    mongo_test_db: AsyncIOMotorDatabase,
) -> AssistantReviewConversationRepository:
    return AssistantReviewConversationRepository(
        connection=mongo_test_db[AssistantReviewConversationRepository.COLLECTION]
    )


@pytest.fixture()
def test_send_message_use_case(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
    test_knowledge_tree_client: KnowledgeTreeClient,
    stub_chat_client: StubChatReviewClient,
) -> SendMessageUseCase:
    return SendMessageUseCase(
        repository=test_assistant_review_conversation_repository,
        knowledge_tree_client=test_knowledge_tree_client,
        chat_client=stub_chat_client,
    )


@pytest_asyncio.fixture()
async def review_node(
    test_palace_node_service: NodeService,
    test_user_root_node: Node,
    node_data_factory: Callable[..., dict],
) -> Node:
    """A node the user can review, created under their palace root."""
    return await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
