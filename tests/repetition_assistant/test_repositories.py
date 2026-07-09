import pytest
from bson import ObjectId

from minager.repetition_assistant.enums import MessageType
from minager.repetition_assistant.models import (
    AssistantReviewConversation,
    AssistantVerdictMessage,
    UserMessage,
)
from minager.repetition_assistant.repositories import AssistantReviewConversationRepository
from tests.conftest import UserTestContext

pytestmark = pytest.mark.asyncio


def _conversation(
    user_id: str, *, session_id: str = 'session:1', node_id: str = 'node:1'
) -> AssistantReviewConversation:
    return AssistantReviewConversation(
        session_id=session_id,
        node_id=node_id,
        user_id=user_id,
        messages=[UserMessage(content='hello')],
    )


async def test_create_and_get(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
    test_user_context: UserTestContext,
):
    created = await test_assistant_review_conversation_repository.create(
        {
            'session_id': 'session:1',
            'node_id': 'node:1',
            'user_id': str(test_user_context.sub),
            'messages': [],
        }
    )
    assert created.id is not None

    fetched = await test_assistant_review_conversation_repository.get(created.id)
    assert fetched.id == created.id
    assert fetched.session_id == 'session:1'
    assert fetched.node_id == 'node:1'
    assert fetched.user_id == str(test_user_context.sub)


async def test_get_returns_none_when_missing(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
):
    result = await test_assistant_review_conversation_repository.get(str(ObjectId()))
    assert result is None


async def test_save_creates_conversation_with_messages(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
    test_user_context: UserTestContext,
):
    saved = await test_assistant_review_conversation_repository.save(
        _conversation(str(test_user_context.sub))
    )

    assert saved.id is not None
    assert len(saved.messages) == 1
    assert isinstance(saved.messages[0], UserMessage)
    assert saved.messages[0].content == 'hello'


async def test_find_by_session_and_node(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
    test_user_context: UserTestContext,
):
    user_id = str(test_user_context.sub)
    saved = await test_assistant_review_conversation_repository.save(
        _conversation(user_id, session_id='session:A', node_id='node:X')
    )
    # A different node in the same session must not match.
    await test_assistant_review_conversation_repository.save(
        _conversation(user_id, session_id='session:A', node_id='node:Y')
    )

    found = await test_assistant_review_conversation_repository.find_by_session_and_node(
        user_id=user_id, session_id='session:A', node_id='node:X'
    )
    assert found is not None
    assert found.id == saved.id


async def test_find_by_session_and_node_returns_none_when_absent(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
    test_user_context: UserTestContext,
):
    result = await test_assistant_review_conversation_repository.find_by_session_and_node(
        user_id=str(test_user_context.sub), session_id='session:none', node_id='node:none'
    )
    assert result is None


async def test_find_by_session_and_node_scoped_to_user(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
    test_user_context: UserTestContext,
):
    await test_assistant_review_conversation_repository.save(
        _conversation(str(test_user_context.sub), session_id='session:A', node_id='node:X')
    )
    # Another user with the same session/node coordinates sees nothing.
    result = await test_assistant_review_conversation_repository.find_by_session_and_node(
        user_id='other-user', session_id='session:A', node_id='node:X'
    )
    assert result is None


async def test_append_message_pushes_and_returns_updated(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
    test_user_context: UserTestContext,
):
    conversation = await test_assistant_review_conversation_repository.save(
        _conversation(str(test_user_context.sub))
    )

    verdict = AssistantVerdictMessage(rating=5, topics_to_add=['recursion'])
    updated = await test_assistant_review_conversation_repository.append_message(conversation.id, verdict)

    assert len(updated.messages) == 2
    last = updated.messages[-1]
    assert isinstance(last, AssistantVerdictMessage)
    assert last.type == MessageType.verdict
    assert last.rating == 5
    assert last.topics_to_add == ['recursion']
    assert updated.updated >= conversation.updated


async def test_append_message_raises_when_missing(
    test_assistant_review_conversation_repository: AssistantReviewConversationRepository,
):
    with pytest.raises(ValueError):
        await test_assistant_review_conversation_repository.append_message(
            str(ObjectId()), UserMessage(content='hi')
        )
