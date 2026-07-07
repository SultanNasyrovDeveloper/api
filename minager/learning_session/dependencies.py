from typing import Annotated

from fastapi import Depends

from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.dependencies import MongoSession, SurrealSession

from .repositories import LearningSessionRepository
from .services import LearningSessionService
from .use_cases import PerformRepetitionUseCase, RegenerateQueueUseCase, StartSessionUseCase


def get_knowledge_tree_client(session: SurrealSession) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(session=session)


KnowledgeTreeClientDependency = Annotated[KnowledgeTreeClient, Depends(get_knowledge_tree_client)]


def get_learning_session_repository(session: MongoSession) -> LearningSessionRepository:
    return LearningSessionRepository(connection=session[LearningSessionRepository.COLLECTION])


LearningSessionRepositoryDependency = Annotated[
    LearningSessionRepository, Depends(get_learning_session_repository)
]


def get_learning_session_service(
    repository: LearningSessionRepositoryDependency,
) -> LearningSessionService:
    return LearningSessionService(repository=repository)


LearningSessionServiceDependency = Annotated[LearningSessionService, Depends(get_learning_session_service)]


def get_start_session_use_case(
    repository: LearningSessionRepositoryDependency,
    service: LearningSessionServiceDependency,
    knowledge_tree_client: KnowledgeTreeClientDependency,
) -> StartSessionUseCase:
    return StartSessionUseCase(
        repository=repository, service=service, knowledge_tree_client=knowledge_tree_client
    )


StartSessionUseCaseDependency = Annotated[StartSessionUseCase, Depends(get_start_session_use_case)]


def get_regenerate_queue_use_case(
    repository: LearningSessionRepositoryDependency,
    knowledge_tree_client: KnowledgeTreeClientDependency,
) -> RegenerateQueueUseCase:
    return RegenerateQueueUseCase(repository=repository, knowledge_tree_client=knowledge_tree_client)


RegenerateQueueUseCaseDependency = Annotated[RegenerateQueueUseCase, Depends(get_regenerate_queue_use_case)]


def get_perform_repetition_use_case(
    repository: LearningSessionRepositoryDependency,
    knowledge_tree_client: KnowledgeTreeClientDependency,
) -> PerformRepetitionUseCase:
    return PerformRepetitionUseCase(repository=repository, knowledge_tree_client=knowledge_tree_client)


PerformRepetitionUseCaseDependency = Annotated[
    PerformRepetitionUseCase, Depends(get_perform_repetition_use_case)
]
