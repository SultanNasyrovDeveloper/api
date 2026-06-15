from typing import Annotated

from fastapi import Depends

from minager.core.clients.knowledge_tree import KnowledgeTreeClient
from minager.dependencies import MongoSession, SurrealConnection

from .managers import LearningSessionManager


def get_knowledge_tree_client(connection: SurrealConnection) -> KnowledgeTreeClient:
    return KnowledgeTreeClient(connection=connection)


KnowledgeTreeClientDependency = Annotated[KnowledgeTreeClient, Depends(get_knowledge_tree_client)]


def get_learning_session_manager(
    session: MongoSession, knowledge_tree_client: KnowledgeTreeClientDependency
) -> LearningSessionManager:
    return LearningSessionManager(
        connection=session[LearningSessionManager.COLLECTION], knowledge_tree_client=knowledge_tree_client
    )


LearningSessionManagerDependency = Annotated[LearningSessionManager, Depends(get_learning_session_manager)]
