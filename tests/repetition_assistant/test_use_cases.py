import pytest
from bson import ObjectId

from minager.node.models import Node
from minager.repetition_assistant.enums import MessageType
from minager.repetition_assistant.exceptions import ReviewNotFoundError
from minager.repetition_assistant.models import (
    AssistantMessage,
    AssistantVerdictMessage,
    UserMessage,
)
from minager.repetition_assistant.use_cases import SendMessageUseCase
from tests.conftest import UserTestContext
from tests.repetition_assistant.conftest import StubChatReviewClient

pytestmark = pytest.mark.asyncio


async def test_first_message_creates_conversation_and_replies(
    test_send_message_use_case: SendMessageUseCase,
    stub_chat_client: StubChatReviewClient,
    test_user_context: UserTestContext,
    review_node: Node,
):
    conversation = await test_send_message_use_case.execute(
        user_id=str(test_user_context.sub),
        session_id='session:1',
        node_id=review_node.pk,
        content='I think it is a data structure.',
    )

    assert conversation.id is not None
    assert conversation.session_id == 'session:1'
    assert conversation.node_id == review_node.pk
    assert conversation.user_id == str(test_user_context.sub)
    # user message + one assistant question
    assert [type(m) for m in conversation.messages] == [UserMessage, AssistantMessage]
    assert conversation.messages[-1].type == MessageType.question
    # the LLM received the node and was not forced to a verdict on the first turn
    assert stub_chat_client.calls[-1].force_verdict is False
    assert stub_chat_client.calls[-1].node.pk == review_node.pk


async def test_follow_up_message_appends_to_conversation(
    test_send_message_use_case: SendMessageUseCase,
    test_user_context: UserTestContext,
    review_node: Node,
):
    conversation = await test_send_message_use_case.execute(
        user_id=str(test_user_context.sub),
        session_id='session:1',
        node_id=review_node.pk,
        content='first answer',
    )

    updated = await test_send_message_use_case.execute(
        user_id=str(test_user_context.sub),
        review_id=conversation.id,
        content='second answer',
    )

    assert updated.id == conversation.id
    # user, question, user, question
    assert [type(m) for m in updated.messages] == [
        UserMessage,
        AssistantMessage,
        UserMessage,
        AssistantMessage,
    ]


async def test_follow_up_raises_when_review_missing(
    test_send_message_use_case: SendMessageUseCase,
    test_user_context: UserTestContext,
):
    with pytest.raises(ReviewNotFoundError):
        await test_send_message_use_case.execute(
            user_id=str(test_user_context.sub),
            review_id=str(ObjectId()),
            content='hello',
        )


async def test_follow_up_raises_when_review_belongs_to_another_user(
    test_send_message_use_case: SendMessageUseCase,
    test_user_context: UserTestContext,
    review_node: Node,
):
    conversation = await test_send_message_use_case.execute(
        user_id=str(test_user_context.sub),
        session_id='session:1',
        node_id=review_node.pk,
        content='first answer',
    )

    with pytest.raises(ReviewNotFoundError):
        await test_send_message_use_case.execute(
            user_id='some-other-user-id',
            review_id=conversation.id,
            content='sneaky',
        )


async def test_verdict_is_forced_after_question_cap(
    test_send_message_use_case: SendMessageUseCase,
    stub_chat_client: StubChatReviewClient,
    test_user_context: UserTestContext,
    review_node: Node,
):
    # First message + follow-ups. The stub asks a question every turn until the use case
    # forces a verdict once 3 questions have already been asked.
    conversation = await test_send_message_use_case.execute(
        user_id=str(test_user_context.sub),
        session_id='session:1',
        node_id=review_node.pk,
        content='answer 0',
    )
    for i in range(1, 4):
        conversation = await test_send_message_use_case.execute(
            user_id=str(test_user_context.sub),
            review_id=conversation.id,
            content=f'answer {i}',
        )

    # Three questions were produced, then the 4th assistant turn is a forced verdict.
    questions = [
        m for m in conversation.messages if isinstance(m, AssistantMessage) and m.type == MessageType.question
    ]
    assert len(questions) == 3
    assert isinstance(conversation.messages[-1], AssistantVerdictMessage)
    assert stub_chat_client.calls[-1].force_verdict is True
