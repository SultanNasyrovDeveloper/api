from minager.core.clients.knowledge_tree import KnowledgeTreeClient

from . import enums, exceptions
from .client import MAX_QUESTIONS, ChatReviewClient
from .models import AssistantMessage, AssistantReviewConversation, UserMessage
from .repositories import AssistantReviewConversationRepository


class SendMessageUseCase:
    def __init__(
        self,
        repository: AssistantReviewConversationRepository,
        knowledge_tree_client: KnowledgeTreeClient,
        chat_client: ChatReviewClient,
    ):
        self.repository = repository
        self.knowledge_tree_client = knowledge_tree_client
        self.chat_client = chat_client

    async def execute(
        self,
        *,
        user_id: str,
        content: str,
        session_id: str | None = None,
        node_id: str | None = None,
        review_id: str | None = None,
    ) -> AssistantReviewConversation:
        if review_id is None:
            conversation = await self._start(
                user_id=user_id, session_id=session_id, node_id=node_id, content=content
            )
        else:
            conversation = await self._continue(user_id=user_id, review_id=review_id, content=content)

        node = await self.knowledge_tree_client.get(conversation.node_id)
        assistant_message = await self.chat_client.generate(
            node, conversation.messages, force_verdict=self._question_limit_reached(conversation)
        )
        return await self.repository.append_message(conversation.id, assistant_message)

    async def _start(
        self, *, user_id: str, session_id: str, node_id: str, content: str
    ) -> AssistantReviewConversation:
        conversation = AssistantReviewConversation(
            session_id=session_id,
            node_id=node_id,
            user_id=user_id,
            messages=[UserMessage(content=content)],
        )
        return await self.repository.save(conversation)

    async def _continue(self, *, user_id: str, review_id: str, content: str) -> AssistantReviewConversation:
        conversation = await self.repository.get(review_id)
        if not conversation or conversation.user_id != user_id:
            raise exceptions.ReviewNotFoundError
        return await self.repository.append_message(review_id, UserMessage(content=content))

    @staticmethod
    def _question_limit_reached(conversation: AssistantReviewConversation) -> bool:
        asked = sum(
            1
            for message in conversation.messages
            if isinstance(message, AssistantMessage) and message.type == enums.MessageType.question
        )
        return asked >= MAX_QUESTIONS
