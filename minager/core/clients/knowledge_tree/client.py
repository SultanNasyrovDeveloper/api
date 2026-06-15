from minager.node.managers import KnowledgeTreeNodeManager

from .base import AbstractPalaceClient


class PalaceNodeServiceClient(KnowledgeTreeNodeManager, AbstractPalaceClient):
    pass


KnowledgeTreeClient = PalaceNodeServiceClient
