from minager.node.repositories import NodeRepository

from .base import AbstractKnowledgeTreeClient


class KnowledgeTreeClientImpl(NodeRepository, AbstractKnowledgeTreeClient):
    pass


KnowledgeTreeClient = KnowledgeTreeClientImpl
