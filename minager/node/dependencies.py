from typing import Annotated

from fastapi import Depends

from minager.dependencies import SurrealConnection

from .managers import KnowledgeTreeNodeManager


def get_knowledge_tree_node_manager(connection: SurrealConnection) -> KnowledgeTreeNodeManager:
    return KnowledgeTreeNodeManager(connection=connection)


KnowledgeTreeNodeManagerDependency = Annotated[
    KnowledgeTreeNodeManager, Depends(get_knowledge_tree_node_manager)
]
