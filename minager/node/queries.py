from collections.abc import Callable

from surorm.base import Operator
from surorm.data_model import Array, RecordID
from surorm.functions import F
from surorm.operators import (
    And,
    Equals,
    GreaterOrEqual,
    Less,
    LessOrEqual,
    Or,
)
from surorm.orm.column import Column
from surorm.statements import Alias, Select

from . import enums, models

SUBTREE_FILTERS: dict[enums.SubtreeFilter, Operator | None] = {
    enums.SubtreeFilter.all: None,
    enums.SubtreeFilter.due: LessOrEqual(models.Node.next_optimal_repetition, F.time.now()),
    enums.SubtreeFilter.struggling: And(
        GreaterOrEqual(models.Node.repetitions, 3),
        Less(models.Node.last_rating, 3),
    ),
    enums.SubtreeFilter.never_reviewed: Or(
        Equals(models.Node.owner_views, 0),
        Equals(models.Node.repetitions, 0),
    ),
    enums.SubtreeFilter.empty: Equals(models.Node.size, 0),
}


def _bfs_select(source: str) -> Select:
    return Select(models.Node.id).from_(source)


def _random_select(source: str) -> Select:
    weight = Column('random_weight')
    return (
        Select(models.Node.id, Alias(weight.name, F.random(strategy='float'))).from_(source).order_by(weight)
    )


def _due_first_select(source: str) -> Select:
    return (
        Select(models.Node.id, models.Node.next_optimal_repetition)
        .from_(source)
        .order_by(models.Node.next_optimal_repetition)
    )


TRAVERSAL_ORDERS: dict[enums.TraversalOrder, Callable[[str], Select]] = {
    enums.TraversalOrder.bfs: _bfs_select,
    enums.TraversalOrder.random: _random_select,
    enums.TraversalOrder.due_first: _due_first_select,
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
        stmt = self.get_base_statement(root, order)
        filter_condition = self.get_filter_conditions(filter_)
        if filter_condition:
            stmt = stmt.where(filter_condition)
        return stmt

    def get_root(self, root_ids: list[str]) -> str:
        root_ids_array = Array([RecordID(models.Node, id_) for id_ in root_ids])
        return f'{root_ids_array}.{{..+collect+inclusive}}<-child<-node'

    def get_base_statement(self, source: str, order: enums.TraversalOrder) -> Select:
        generate_base_stmt = TRAVERSAL_ORDERS[order]
        return generate_base_stmt(source)

    def get_filter_conditions(self, filter_: enums.SubtreeFilter) -> Operator | None:
        return SUBTREE_FILTERS[filter_]
