from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from minager.core.lexorank import Lexorank

from ..enums import MovePosition
from ..repositories import NodeRepository


@dataclass
class MoveNodeConfig:
    node_id: str
    target_id: str


class MoveNodeStrategy(metaclass=ABCMeta):
    def __init__(self, config: MoveNodeConfig, repository: NodeRepository):
        self.config = config
        self.repository = repository

    async def validate(self) -> None:
        # Python-only check first - avoid DB call if moving to itself
        if self.config.node_id == self.config.target_id:
            raise ValueError(f'Cannot move node to itself: node:{self.config.node_id}')

        result = await self.repository.get_move_validation_context(self.config.node_id, self.config.target_id)

        # Validate source node exists
        if not result.get('source'):
            raise ValueError(f'Source node not found: node:{self.config.node_id}')

        # Validate target node exists
        if not result.get('target'):
            raise ValueError(f'Target node not found: node:{self.config.target_id}')

        # Check for cycle (would create circular reference)
        if result.get('has_cycle'):
            raise ValueError(
                f'Cannot move node:{self.config.node_id} to node:{self.config.target_id} '
                f'- would create cycle (target is a descendant of source)'
            )

    @abstractmethod
    async def move(self): ...

    """Execute the move operation.

    Uses self.config for all move parameters.
    """


class MoveNodeAsFirstChild(MoveNodeStrategy):
    async def move(self):
        current_first_child_order = await self.repository.get_first_child_order(self.config.target_id)
        order = Lexorank.middle(next_=current_first_child_order or '')
        await self.repository.move(self.config.node_id, self.config.target_id, order)
        return await self.repository.get(self.config.node_id)


class MoveNodeAsLastChild(MoveNodeStrategy):
    async def move(self):
        current_last_child_order = await self.repository.get_last_child_order(self.config.target_id)
        order = Lexorank.middle(previous=current_last_child_order or '')
        await self.repository.move(self.config.node_id, self.config.target_id, order)
        return await self.repository.get(self.config.node_id)


class MoveNodeBefore(MoveNodeStrategy):
    async def move(self):
        move_data = await self.repository.get_sibling_order_context(self.config.target_id, before=True)
        if not move_data:
            return None
        order = Lexorank.middle(move_data['previous'], move_data['next'])
        await self.repository.move(self.config.node_id, move_data['new_parent'], order)
        return await self.repository.get(self.config.node_id)


class MoveNodeAfter(MoveNodeStrategy):
    async def move(self):
        move_data = await self.repository.get_sibling_order_context(self.config.target_id, before=False)
        if not move_data:
            return None
        order = Lexorank.middle(move_data['previous'], move_data['next'])
        await self.repository.move(self.config.node_id, move_data['new_parent'], order)
        return await self.repository.get(self.config.node_id)


class MoveNodeUseCase:
    STRATEGY_MAP: ClassVar[dict] = {
        MovePosition.before.value: MoveNodeBefore,
        MovePosition.after.value: MoveNodeAfter,
        MovePosition.first_child.value: MoveNodeAsFirstChild,
        MovePosition.last_child.value: MoveNodeAsLastChild,
    }

    def __init__(self, repository: NodeRepository):
        self.repository = repository

    async def execute(self, id_: str, to: str, position: MovePosition = MovePosition.last_child):
        strategy_class = self.STRATEGY_MAP.get(position, None)
        if not strategy_class:
            raise ValueError('Unable to find proper move node strategy.')
        config = MoveNodeConfig(node_id=id_, target_id=to)
        strategy = strategy_class(config=config, repository=self.repository)
        await strategy.validate()
        return await strategy.move()
