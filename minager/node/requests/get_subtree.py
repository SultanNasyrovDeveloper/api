from typing import TypedDict

from minager.node.functions import GetAncestors
from minager.surorm import Response
from minager.surorm.query import (
    Alias,
    DefineVariable,
    Record,
    Select,
    Transaction,
    function,
)

from .abstract import AbstractRequest


class GetSubtreeConfig(TypedDict):
    root_id: str


class GetSubtreeRequest(AbstractRequest[GetSubtreeConfig]):

    async def perform(self) -> Response:
        root_id = Record('node', self._config['root_id'])
        query = (
            Transaction()
            .perform(
                DefineVariable('ancestors', GetAncestors(root_id)),
                DefineVariable(
                    'parent',
                    Select()
                    .from_(root_id, only=True)
                    .columns(
                        Alias('parent_id', function.ArrayFirst('->child->node.id')), all_=True
                    ),
                ),
                'if $parent is none { throw "Node not found"; }',
                DefineVariable(
                    'children_ids',
                    Select()
                    .from_('$parent.id', only=True)
                    .columns(Alias('id', '<-child<-node.id')),
                ),
                DefineVariable(
                    'children',
                    Select()
                    .from_('node')
                    .columns('id', 'title', 'order', Alias('children', '<-child<-node.*'))
                    .omit(
                        'children.questions',
                        'children.content',
                        'children.created',
                        'children.size',
                        'children.last_rating',
                        'children.difficulty',
                        'children.owner.views',
                        'children.cpr',
                        'children.last_repetition',
                        'children.next_optimal_repetition',
                        'children.repetitions',
                    )
                    .where('id in $children_ids.id')
                    .order_by('order', direction='asc'),
                ),
            )
            .return_(
                function.ObjectFromEntries(
                    function.ArrayConcat(
                        function.ObjectEntries('$parent'),
                        '[["children", $children], ["ancestors", $ancestors]]',
                    )
                )
            )
        )
        return await self._db.query(query.sql())
