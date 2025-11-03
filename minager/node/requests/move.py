from abc import ABC, abstractmethod
from typing import TypedDict

from minager import surorm
from minager.core.lexorank import Lexorank
from minager.core.surorm import (
    Alias,
    DefineVariable,
    Manager,
    Record,
    Response,
    Select,
    Transaction,
)

from ..enums import NodeRelationType
from .abstract import AbstractRequest


class MoveNodeConfig(TypedDict):
    node_id: str
    target_id: str
    move_position: int
    return_with_children: bool


class MoveNodeStrategy(ABC):

    def __init__(self, db: Manager, config: MoveNodeConfig):
        self._db = db
        self._config = config

    @abstractmethod
    async def perform(self) -> Response:
        pass


# TODO: Return queried with children node only when config parameter provided.
class MoveNodeAsFirstChild(MoveNodeStrategy):

    async def perform(self) -> Response | None:
        current_first_child_order_query = (
            Select()
            .from_('node')
            .columns('value order')
            .where(f'->(child where out == node:{self._config['target_id']})')
            .order_by('order', direction='asc')
            .limit(1)
        )
        response = await self._db.query(current_first_child_order_query.sql())
        current_first_child_order = response.raw(many=False)
        current_first_child_order = current_first_child_order or ''
        order = Lexorank.middle(next_=current_first_child_order)
        move_node_query = (
            Transaction()
            .perform(
                f'delete child where in == node:{self._config['node_id']};',
                f'relate node:{self._config['node_id']}->child->node:{self._config['target_id']};',
                DefineVariable(
                    'updated', f'update only node:{self._config['node_id']} set order = "{order}";'
                ),
            )
            .return_(
                Select()
                .from_(Record('node', self._config['node_id']), only=True)
                .columns(
                    Alias(
                        'children',
                        Select()
                        .from_('node')
                        .columns('id', 'title')
                        .where(
                            f'->(child where out.id=={Record('node', self._config['node_id']).sql()})'
                        ),
                    ),
                    all_=True,
                )
            )
        )
        response = await self._db.query(move_node_query.sql())
        if response.data().get('result'):
            response.data()['result']['parent_id'] = self._config['target_id']
        return response


class MoveNodeAsLastChild(MoveNodeStrategy):
    async def perform(self) -> Response | None:
        current_last_child_order_query = (
            Select()
            .from_('node')
            .columns('value order')
            .where(f'->(child where out == node:{self._config['target_id']})')
            .order_by('order', direction='desc')
            .limit(1)
        )
        response = await self._db.query(current_last_child_order_query.sql())
        current_last_child_order = response.raw(many=False)
        current_last_child_order = current_last_child_order or ''
        order = Lexorank.middle(previous=current_last_child_order)
        move_node_query = (
            Transaction()
            .perform(
                f'delete child where in == node:{self._config['node_id']};',
                f'relate node:{self._config['node_id']}->child->node:{self._config['target_id']};',
                DefineVariable(
                    'updated', f'update only node:{self._config['node_id']} set order = "{order}";'
                ),
            )
            .return_(
                Select()
                .from_(Record('node', self._config['node_id']), only=True)
                .columns(
                    Alias(
                        'children',
                        Select()
                        .from_('node')
                        .columns('id', 'title')
                        .where(
                            f'->(child where out.id=={Record('node', self._config['node_id']).sql()})'
                        ),
                    ),
                    all_=True,
                )
            )
        )
        response = await self._db.query(move_node_query.sql())
        if response.data().get('result'):
            response.data()['result']['parent_id'] = self._config['target_id']
        return response


class MoveNodeBefore(MoveNodeStrategy):
    async def perform(self) -> Response | None:
        neighbour_orders_query = (
            Transaction()
            .perform(
                DefineVariable(
                    'target',
                    Select()
                    .from_(f'node:{self._config['target_id']}', only=True)
                    .columns('order', Alias('parent_id', surorm.F.array.first('->child.out'))),
                ),
                DefineVariable(
                    'prev_order',
                    surorm.F.array.first(
                        Select()
                        .from_('node')
                        .columns('value order')
                        .where('->(child where out == $target.parent_id)', 'order < $target.order')
                        .order_by('order', direction='desc')
                        .limit(1)
                    ),
                ),
            )
            .return_('{new_parent: $target.parent_id, previous: $prev_order, next: $target.order}')
        )
        response = await self._db.query(neighbour_orders_query.sql())
        move_data = response.raw(many=False)
        if not move_data:
            return
        order = Lexorank.middle(move_data['previous'], move_data['next'])
        move_node_query = (
            Transaction()
            .perform(
                f'delete child where in == node:{self._config['node_id']};',
                f'relate node:{self._config['node_id']}->child->{move_data['new_parent']};',
                DefineVariable(
                    'updated', f'update only node:{self._config['node_id']} set order = "{order}";'
                ),
            )
            .return_(
                Select()
                .from_(Record('node', self._config['node_id']), only=True)
                .columns(
                    Alias(
                        'children',
                        Select()
                        .from_('node')
                        .columns('id', 'title')
                        .where(
                            f'->(child where out.id=={Record('node', self._config['node_id']).sql()})'
                        ),
                    ),
                    all_=True,
                )
            )
        )
        response = await self._db.query(move_node_query.sql())
        if response.data().get('result'):
            response.data()['result']['parent_id'] = move_data['new_parent'].split(':')[1]
        return response


class MoveNodeAfter(MoveNodeStrategy):
    async def perform(self) -> Response | None:
        neighbour_orders_query = (
            Transaction()
            .perform(
                DefineVariable(
                    'target',
                    Select()
                    .from_(f'node:{self._config['target_id']}', only=True)
                    .columns('order', Alias('parent_id', surorm.F.array.first('->child.out'))),
                ),
                DefineVariable(
                    'next_order',
                    surorm.F.array.first(
                        Select()
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
        response = await self._db.query(neighbour_orders_query.sql())
        move_data = response.raw(many=False)
        if not move_data:
            return
        order = Lexorank.middle(move_data['previous'], move_data['next'])
        move_node_query = (
            Transaction()
            .perform(
                f'delete child where in == node:{self._config['node_id']};',
                f'relate node:{self._config['node_id']}->child->{move_data['new_parent']};',
                DefineVariable(
                    'updated', f'update only node:{self._config['node_id']} set order = "{order}";'
                ),
            )
            .return_(
                Select()
                .from_(Record('node', self._config['node_id']), only=True)
                .columns(
                    Alias(
                        'children',
                        Select()
                        .from_('node')
                        .columns('id', 'title')
                        .where(
                            f'->(child where out.id=={Record('node', self._config['node_id']).sql()})'
                        ),
                    ),
                    all_=True,
                )
            )
        )
        response = await self._db.query(move_node_query.sql())
        if response.data().get('result'):
            response.data()['result']['parent_id'] = move_data['new_parent'].split(':')[1]
        return response


class MoveNodeRequest(AbstractRequest[MoveNodeConfig]):

    MOVE_POSITION_HANDLERS = {
        NodeRelationType.first_child.value: MoveNodeAsFirstChild,
        NodeRelationType.last_child.value: MoveNodeAsLastChild,
        NodeRelationType.before.value: MoveNodeBefore,
        NodeRelationType.after.value: MoveNodeAfter,
    }

    async def perform(self) -> Response | None:
        handler = self.MOVE_POSITION_HANDLERS[self._config['move_position']]
        if not handler:
            return
        return await handler(db=self._db, config=self._config).perform()
