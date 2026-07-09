from typing import Literal, Self

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from minager.node.models import Node
from minager.settings import config

from . import enums
from .models import AssistantMessage, AssistantMessageT, AssistantVerdictMessage, Message

MAX_QUESTIONS = 3

SYSTEM_PROMPT = """
You are a knowledge review assistant. You help a learner verify how well they understand a
single node from their knowledge tree by having a short, focused conversation.

The node under review:
- Title: {title}
- Questions the node is meant to answer: {questions}
- Node content (rich HTML, source of truth): {content}

How the conversation works:
- Ask the learner focused questions that probe whether they actually understand the node.
- Ask AT MOST {max_questions} questions across the whole conversation. Keep them short.
- When you have enough signal (or you are told to conclude), produce a VERDICT instead of a question.

Each turn you MUST return exactly one of two shapes:
- A QUESTION: type="question", with `content` holding the question or task. Leave `rating` null and
  `topics_to_add` empty.
- A VERDICT: type="verdict", with `rating` (1=almost no understanding, 5=full mastery) and
  `topics_to_add` (a short list of sub-topics the learner should study next; may be empty).
  Leave `content` null.

The verdict is advisory only — it is shown to the learner as a recommendation, nothing is mutated.
"""

FORCE_VERDICT_INSTRUCTION = (
    'You have reached the question limit. Produce a VERDICT now (type="verdict"); '
    'do not ask another question.'
)


class LLMTurn(BaseModel):
    type: Literal[enums.MessageType.question, enums.MessageType.verdict]
    content: str | None = Field(default=None, description='The question text, when type is "question"')
    rating: int | None = Field(
        default=None, ge=1, le=5, description='Understanding rating, when type is "verdict"'
    )
    topics_to_add: list[str] = Field(default_factory=list)


class ChatReviewClient:
    def __init__(self, api_key: str, model: str):
        self.llm = ChatOpenAI(api_key=api_key, model=model).with_structured_output(LLMTurn)

    @classmethod
    def from_config(cls) -> Self:
        return cls(api_key=config.openai_api_token, model=config.openai_chat_model)

    async def generate(
        self, node: Node, messages: list[Message], *, force_verdict: bool = False
    ) -> AssistantMessageT:
        prompt = self._build_prompt(node, messages, force_verdict=force_verdict)
        turn: LLMTurn = await self.llm.ainvoke(prompt)
        return self._to_message(turn, force_verdict=force_verdict)

    def _build_prompt(self, node: Node, messages: list[Message], *, force_verdict: bool) -> list[BaseMessage]:
        system = SYSTEM_PROMPT.format(
            title=node.title,
            questions=node.questions,
            content=node.content,
            max_questions=MAX_QUESTIONS,
        )
        prompt: list[BaseMessage] = [SystemMessage(content=system)]
        for message in messages:
            if message.role == enums.MessageRole.user:
                prompt.append(HumanMessage(content=message.content))
            elif isinstance(message, AssistantVerdictMessage):
                prompt.append(AIMessage(content=f'[verdict] rating={message.rating}'))
            else:
                prompt.append(AIMessage(content=message.content))
        if force_verdict:
            prompt.append(SystemMessage(content=FORCE_VERDICT_INSTRUCTION))
        return prompt

    def _to_message(self, turn: LLMTurn, *, force_verdict: bool) -> AssistantMessageT:
        if turn.type == enums.MessageType.verdict or force_verdict:
            return AssistantVerdictMessage(
                rating=turn.rating if turn.rating is not None else 1,
                topics_to_add=turn.topics_to_add,
            )
        return AssistantMessage(type=enums.MessageType.question, content=turn.content or '')
