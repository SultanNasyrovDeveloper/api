from typing import TypedDict

from minager.core.surorm import Alias, Expression, F, Record, Select, Traverse

from .abstract import AbstractRequest


class GetNodeDetailConfig(TypedDict):
    id: str


class GetNodeDetailRequest(AbstractRequest[GetNodeDetailConfig]):
    async def perform(self) -> dict | None:
        return await self._db.query(self.make_query())

    def make_query(self) -> Expression:
        return Select(
            Alias(
                'parent_id',
                F.array.first(Traverse('@', 'id').depth(1).relation('->child->node')),
            ),
            Alias(
                'parent',
                Traverse('@', 'id', 'title').relation('->child->node').alias('parent'),
            ),
            all_=True,
        ).from_(Record('node', self._config['id']), only=True)
