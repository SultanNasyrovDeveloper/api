from abc import ABCMeta, abstractmethod

from minager.node.enums import SubtreeFilter, TraversalOrder
from minager.node.models import Node


class AbstractKnowledgeTreeClient(metaclass=ABCMeta):
    @abstractmethod
    async def create(self, data: dict) -> Node | None:
        pass

    @abstractmethod
    async def get(self, node_id: str) -> Node | None:
        pass

    @abstractmethod
    async def update(self, node_id: str, data: dict) -> Node | None:
        pass

    @abstractmethod
    async def get_subtree_ids(
        self,
        root_ids: list[str],
        filter_: SubtreeFilter = SubtreeFilter.all,
        order: TraversalOrder = TraversalOrder.bfs,
        limit: int = 50,
    ) -> list[str]:
        pass
