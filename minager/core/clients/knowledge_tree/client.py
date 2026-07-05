from minager.node.managers import KnowledgeTreeNodeManager

from .base import AbstractKnowledgeTreeClient


class KnowledgeTreeClientImpl(KnowledgeTreeNodeManager, AbstractKnowledgeTreeClient):
    pass


KnowledgeTreeClient = KnowledgeTreeClientImpl
