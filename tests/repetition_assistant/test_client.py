from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from minager.repetition_assistant.client import ChatReviewClient, LLMTurn
from minager.repetition_assistant.enums import MessageType
from minager.repetition_assistant.models import (
    AssistantMessage,
    AssistantVerdictMessage,
    UserMessage,
)


def _client() -> ChatReviewClient:
    # Constructing the client only binds a schema; it makes no network call.
    return ChatReviewClient(api_key='sk-test', model='gpt-4o-mini')


def test_to_message_maps_question():
    message = _client()._to_message(
        LLMTurn(type=MessageType.question, content='What is X?'), force_verdict=False
    )
    assert isinstance(message, AssistantMessage)
    assert message.type == MessageType.question
    assert message.content == 'What is X?'


def test_to_message_maps_verdict():
    message = _client()._to_message(
        LLMTurn(type=MessageType.verdict, rating=5, topics_to_add=['recursion']),
        force_verdict=False,
    )
    assert isinstance(message, AssistantVerdictMessage)
    assert message.rating == 5
    assert message.topics_to_add == ['recursion']


def test_force_verdict_overrides_a_question_turn():
    # Even if the model tried to ask another question, force_verdict yields a verdict,
    # falling back to the lowest rating when the model gave none.
    message = _client()._to_message(LLMTurn(type=MessageType.question, content='ignored'), force_verdict=True)
    assert isinstance(message, AssistantVerdictMessage)
    assert message.rating == 1


def test_build_prompt_maps_roles_and_appends_force_verdict_instruction():
    client = _client()
    node = SimpleNamespace(title='Binary Tree', questions='What is it?', content='<p>content</p>')
    messages = [
        UserMessage(content='my answer'),
        AssistantMessage(type=MessageType.question, content='q1'),
        AssistantVerdictMessage(rating=3, topics_to_add=[]),
    ]

    prompt = client._build_prompt(node, messages, force_verdict=True)

    assert isinstance(prompt[0], SystemMessage)
    assert 'Binary Tree' in prompt[0].content
    assert isinstance(prompt[1], HumanMessage)
    assert isinstance(prompt[2], AIMessage)
    assert prompt[2].content == 'q1'
    assert isinstance(prompt[3], AIMessage)
    assert 'verdict' in prompt[3].content
    # force_verdict tacks on a final system instruction to conclude
    assert isinstance(prompt[-1], SystemMessage)
    assert 'VERDICT' in prompt[-1].content
