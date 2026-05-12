from abc import ABCMeta, abstractmethod
from dataclasses import dataclass

from minager.core import surorm
from minager.core.lexorank import Lexorank

from ..enums import MovePosition
from ..models import Node


@dataclass
class MoveNodeConfig:
    """Configuration for move node operation.

    Attributes:
        node_id: ID of the node being moved
        target_id: ID of the target node (parent for first/last_child, sibling for before/after)
    """

    node_id: str
    target_id: str


class MoveNodeStrategy(metaclass=ABCMeta):
    """Base class for move node strategies.

    Each strategy implements a specific way to move nodes within the tree:
    - first_child: Move to start of parent's children
    - last_child: Move to end of parent's children
    - before: Insert before a target sibling
    - after: Insert after a target sibling
    """

    def __init__(self, config: MoveNodeConfig, manager: surorm.Manager):
        self.config = config
        self.manager = manager

    async def _would_create_cycle(self) -> bool:
        """Check if target_id is a descendant of node_id.

        Uses LIMIT 1 to stop scanning after first match.
        Returns True if moving node_id under target_id would create cycle.
        """
        query = (
            surorm.Select('value id')
            .from_(f'node:{self.config.node_id}<-child<-node{{{{..+inclusive}}}}')
            .where(f'id == node:{self.config.target_id}')
            .limit(1)
        )
        result = await self.manager.query(query.sql())
        return bool(result)

    async def validate(self) -> None:
        """Validate the move operation before execution.

        Base validation common to all strategies.
        Subclasses can override to add strategy-specific validation.

        Raises:
            ValueError: If validation fails (self-reference or cycle detected)
        """
        # Check for self-reference
        if self.config.node_id == self.config.target_id:
            raise ValueError(f"Cannot move node to itself: node:{self.config.node_id}")

        # Check for cycle (would create circular reference)
        if await self._would_create_cycle():
            raise ValueError(
                f"Cannot move node:{self.config.node_id} to node:{self.config.target_id} "
                f"- would create cycle (target is a descendant of source)"
            )

    @abstractmethod
    async def move(self): ...

    """Execute the move operation.

    Uses self.config for all move parameters.
    """


# TODO: Return queried with children node only when config parameter provided.
class MoveNodeAsFirstChild(MoveNodeStrategy):

    async def move(self):
        current_first_child_order_query = (
            surorm.Select('value order')
            .from_('node')
            .where(f'->(child where out == node:{self.config.target_id})')
            .order_by('order', direction='asc')
            .limit(1)
        )
        current_first_child_order = await self.manager.query(current_first_child_order_query.sql())
        current_first_child_order = current_first_child_order or ''
        order = Lexorank.middle(next_=current_first_child_order)
        move_node_query = surorm.Transaction().perform(
            f'delete child where in == node:{self.config.node_id};',
            f'relate node:{self.config.node_id}->child->node:{self.config.target_id};',
            surorm.DefineVariable(
                'updated', f'update only node:{self.config.node_id} set order = "{order}";'
            ),
        )
        return await self.manager.query(move_node_query.sql())


class MoveNodeAsLastChild(MoveNodeStrategy):
    async def move(self):
        current_last_child_order_query = (
            surorm.Select('value order')
            .from_(Node)
            .where(f'->(child where out == node:{self.config.target_id})')
            .order_by('order', direction='desc')
            .limit(1)
        )
        current_last_child_order = await self.manager.query(current_last_child_order_query.sql())
        current_last_child_order = current_last_child_order or ''
        order = Lexorank.middle(previous=current_last_child_order)
        move_node_query = surorm.Transaction().perform(
            f'delete child where in == node:{self.config.node_id};',
            f'relate node:{self.config.node_id}->child->node:{self.config.target_id};',
            surorm.DefineVariable(
                'updated', f'update only node:{self.config.node_id} set order = "{order}";'
            ),
        )
        return await self.manager.query(move_node_query.sql())


class MoveNodeBefore(MoveNodeStrategy):
    async def move(self):
        neighbour_orders_query = (
            surorm.Transaction()
            .perform(
                surorm.DefineVariable(
                    'target',
                    surorm.Select(
                        'order', surorm.Alias('parent_id', surorm.F.array.first('->child.out'))
                    ).from_(f'node:{self.config.target_id}', only=True),
                ),
                surorm.DefineVariable(
                    'prev_order',
                    surorm.F.array.first(
                        surorm.Select('value order')
                        .from_('node')
                        .where('->(child where out == $target.parent_id)', 'order < $target.order')
                        .order_by('order', direction='desc')
                        .limit(1)
                    ),
                ),
            )
            .return_('{new_parent: $target.parent_id, previous: $prev_order, next: $target.order}')
        )
        move_data = await self.manager.query(neighbour_orders_query.sql())
        if not move_data:
            return
        order = Lexorank.middle(move_data['previous'], move_data['next'])
        move_node_query = surorm.Transaction().perform(
            f'delete child where in == node:{self.config.node_id};',
            f'relate node:{self.config.node_id}->child->{move_data['new_parent']};',
            surorm.DefineVariable(
                'updated', f'update only node:{self.config.node_id} set order = "{order}";'
            ),
        )
        return await self.manager.query(move_node_query.sql())


class MoveNodeAfter(MoveNodeStrategy):
    async def move(self):
        neighbour_orders_query = (
            surorm.Transaction()
            .perform(
                surorm.DefineVariable(
                    'target',
                    surorm.Select()
                    .from_(f'node:{self.config.target_id}', only=True)
                    .columns('order', surorm.Alias('parent_id', surorm.F.array.first('->child.out'))),
                ),
                surorm.DefineVariable(
                    'next_order',
                    surorm.F.array.first(
                        surorm.Select()
                        .from_('node')
                        .columns('value order')
                        .where('->(child where out == $target.parent_id)', 'order > $target.order')
                        .order_by('order', direction='asc')
                        .limit(1)
                    ),
                ),
            )
            .return_('{new_parent: $target.parent_id, next: $next_order, previous: $target.order}')
        )
        move_data = await self.manager.query(neighbour_orders_query.sql())
        if not move_data:
            return
        order = Lexorank.middle(move_data['previous'], move_data['next'])
        move_node_query = surorm.Transaction().perform(
            f'delete child where in == node:{self.config.node_id};',
            f'relate node:{self.config.node_id}->child->{move_data['new_parent']};',
            surorm.DefineVariable(
                'updated', f'update only node:{self.config.node_id} set order = "{order}";'
            ),
        )
        return await self.manager.query(move_node_query.sql())


class MoveNodeService:

    STRATEGY_MAP = {
        MovePosition.before.value: MoveNodeBefore,
        MovePosition.after.value: MoveNodeAfter,
        MovePosition.first_child.value: MoveNodeAsFirstChild,
        MovePosition.last_child.value: MoveNodeAsLastChild,
    }

    def __init__(self, manager: surorm.Manager):
        self.manager = manager

    async def move(self, id_: str, to: str, position: MovePosition = MovePosition.last_child):
        strategy_class = self.STRATEGY_MAP.get(position, None)
        if not strategy_class:
            raise ValueError('Unable to find proper move node strategy.')
        config = MoveNodeConfig(node_id=id_, target_id=to)
        strategy = strategy_class(config=config, manager=self.manager)
        await strategy.validate()
        return await strategy.move()
