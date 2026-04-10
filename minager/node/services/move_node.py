from abc import ABCMeta, abstractmethod

from minager.core import surorm
from minager.core.lexorank import Lexorank

from ..enums import MovePosition


class MoveNodeStrategy(metaclass=ABCMeta):
    def __init__(self, manager: surorm.Manager):
        self.manager = manager

    @abstractmethod
    def move(self, id_: str, to: str): ...


# TODO: Return queried with children node only when config parameter provided.
class MoveNodeAsFirstChild(MoveNodeStrategy):

    async def move(self, id_: str, to: str):
        current_first_child_order_query = (
            surorm.Select('value order')
            .from_('node')
            .where(f'->(child where out == node:{to})')
            .order_by('order', direction='asc')
            .limit(1)
        )
        current_first_child_order = await self.manager.query(current_first_child_order_query.sql())
        current_first_child_order = current_first_child_order or ''
        order = Lexorank.middle(next_=current_first_child_order)
        move_node_query = surorm.Transaction().perform(
            f'delete child where in == node:{id_};',
            f'relate node:{id_}->child->node:{to};',
            surorm.DefineVariable('updated', f'update only node:{id_} set order = "{order}";'),
        )
        return await self.manager.query(move_node_query.sql())


class MoveNodeAsLastChild(MoveNodeStrategy):
    async def move(self, id_: str, to: str):
        current_last_child_order_query = (
            surorm.Select('value order')
            .from_('node')
            .where(f'->(child where out == node:{to})')
            .order_by('order', direction='desc')
            .limit(1)
        )
        current_last_child_order = await self.manager.query(current_last_child_order_query.sql())
        current_last_child_order = current_last_child_order or ''
        order = Lexorank.middle(previous=current_last_child_order)
        move_node_query = surorm.Transaction().perform(
            f'delete child where in == node:{id_};',
            f'relate node:{id_}->child->node:{to};',
            surorm.DefineVariable('updated', f'update only node:{id_} set order = "{order}";'),
        )
        return await self.manager.query(move_node_query.sql())


class MoveNodeBefore(MoveNodeStrategy):
    async def move(self, id_: str, to: str):
        neighbour_orders_query = (
            surorm.Transaction()
            .perform(
                surorm.DefineVariable(
                    'target',
                    surorm.Select(
                        'order', surorm.Alias('parent_id', surorm.F.array.first('->child.out'))
                    ).from_(f'node:{to}', only=True),
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
            f'delete child where in == node:{id_};',
            f'relate node:{id_}->child->{move_data['new_parent']};',
            surorm.DefineVariable('updated', f'update only node:{id_} set order = "{order}";'),
        )
        return await self.manager.query(move_node_query.sql())


class MoveNodeAfter(MoveNodeStrategy):
    async def move(self, id_: str, to: str):
        neighbour_orders_query = (
            surorm.Transaction()
            .perform(
                surorm.DefineVariable(
                    'target',
                    surorm.Select()
                    .from_(f'node:{to}', only=True)
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
            f'delete child where in == node:{id_};',
            f'relate node:{id_}->child->{move_data['new_parent']};',
            surorm.DefineVariable('updated', f'update only node:{id_} set order = "{order}";'),
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
        strategy = strategy_class(manager=self.manager)
        return await strategy.move(id_, to)
