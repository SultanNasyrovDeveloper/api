from collections.abc import Callable

from surorm.data_model import Array, RecordID
from surorm.functions import F
from surorm.operators import (
    Equals,
    GreaterOrEqual,
    Less,
    LessOrEqual,
    Or,
)
from surorm.statements import Select

from . import enums, models

type QueryModifierFunction = Callable[[Select], Select]

SUBTREE_FILTERS: dict[enums.SubtreeFilter, QueryModifierFunction | None] = {
    enums.SubtreeFilter.all: lambda stmt: stmt.columns(models.Node.next_optimal_repetition).order_by(
        models.Node.next_optimal_repetition, direction='ASC'
    ),
    enums.SubtreeFilter.due: lambda stmt: (
        stmt.columns(models.Node.next_optimal_repetition)
        .where(LessOrEqual(models.Node.next_optimal_repetition, F.time.now()))
        .order_by(models.Node.next_optimal_repetition, direction='ASC')
    ),
    enums.SubtreeFilter.struggling: lambda stmt: stmt.where(
        GreaterOrEqual(models.Node.repetitions, 3), Less(models.Node.last_rating, 3)
    ),
    enums.SubtreeFilter.never_reviewed: lambda stmt: stmt.where(
        Or(
            Equals(models.Node.owner_views, 0),
            Equals(models.Node.repetitions, 0),
        )
    ),
    enums.SubtreeFilter.empty: lambda stmt: stmt.where(Equals(models.Node.size, 0)),
}


TRAVERSAL_ORDERS: dict[enums.TraversalOrder, QueryModifierFunction] = {
    enums.TraversalOrder.bfs: lambda stmt: stmt,
    enums.TraversalOrder.random: lambda stmt: stmt.order_by(F.random()),
}


class SubtreeIdsQuery:
    def build(
        self,
        root_ids: list[str],
        filter_: enums.SubtreeFilter = enums.SubtreeFilter.all,
        order: enums.TraversalOrder = enums.TraversalOrder.bfs,
    ) -> Select:
        assert order in TRAVERSAL_ORDERS, f'Traversal order {order} has no query behind it yet'
        root = self.get_root(root_ids)
        stmt = Select(models.Node.id).from_(root)
        stmt = self.apply_traversal_order(stmt, order)
        stmt = self.apply_filter_condition(stmt, filter_)
        return stmt

    def get_root(self, root_ids: list[str]) -> str:
        root_ids_array = Array([RecordID(models.Node, id_) for id_ in root_ids])
        return f'{root_ids_array}.{{..+collect+inclusive}}<-child<-node'

    def apply_traversal_order(self, stmt: Select, traversal_strategy: enums.TraversalOrder) -> Select:
        modification_function = TRAVERSAL_ORDERS[traversal_strategy]
        return modification_function(stmt)

    def apply_filter_condition(self, stmt: Select, filter_strategy: enums.SubtreeFilter) -> Select:
        modification_function = SUBTREE_FILTERS[filter_strategy]
        return modification_function(stmt)
