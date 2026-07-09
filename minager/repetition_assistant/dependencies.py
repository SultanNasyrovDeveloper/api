from typing import Annotated

from fastapi import Depends

from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.dependencies import MongoSession, SurrealSession

from .client import ChatReviewClient
from .repositories import AssistantReviewConversationRepository
from .services import AssistantReviewConversationService
from .use_cases import SendMessageUseCase


def get_knowledge_tree_client(session: SurrealSession) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(session=session)


KnowledgeTreeClientDependency = Annotated[KnowledgeTreeClient, Depends(get_knowledge_tree_client)]


def get_chat_review_client() -> ChatReviewClient:
    return ChatReviewClient.from_config()


ChatReviewClientDependency = Annotated[ChatReviewClient, Depends(get_chat_review_client)]


def get_assistant_review_conversation_repository(
    session: MongoSession,
) -> AssistantReviewConversationRepository:
    return AssistantReviewConversationRepository(
        connection=session[AssistantReviewConversationRepository.COLLECTION]
    )


AssistantReviewConversationRepositoryDependency = Annotated[
    AssistantReviewConversationRepository, Depends(get_assistant_review_conversation_repository)
]


def get_assistant_review_conversation_service(
    repository: AssistantReviewConversationRepositoryDependency,
) -> AssistantReviewConversationService:
    return AssistantReviewConversationService(repository=repository)


AssistantReviewConversationServiceDependency = Annotated[
    AssistantReviewConversationService, Depends(get_assistant_review_conversation_service)
]


def get_send_message_use_case(
    repository: AssistantReviewConversationRepositoryDependency,
    knowledge_tree_client: KnowledgeTreeClientDependency,
    chat_client: ChatReviewClientDependency,
) -> SendMessageUseCase:
    return SendMessageUseCase(
        repository=repository,
        knowledge_tree_client=knowledge_tree_client,
        chat_client=chat_client,
    )


SendMessageUseCaseDependency = Annotated[SendMessageUseCase, Depends(get_send_message_use_case)]
