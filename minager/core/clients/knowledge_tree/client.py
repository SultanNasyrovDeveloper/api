from minager.node.managers import PalaceNodeManager

from .base import AbstractPalaceClient


class PalaceNodeServiceClient(PalaceNodeManager, AbstractPalaceClient):
    pass


KnowledgeTreeClient = PalaceNodeServiceClient
