from typing import TypedDict

from api.surorm import Response
from api.surorm.query import Alias, ArrayFirst, Expression, Record, Select, Traverse

from .abstract import AbstractRequest


class GetNodeDetailConfig(TypedDict):
    id: str


class GetNodeDetailRequest(AbstractRequest[GetNodeDetailConfig]):
    async def perform(self) -> Response:
        return await self._db.query(self.make_query())

    def make_query(self) -> Expression:
        return (
            Select(Record('node', self._config['id']), only=True)
            .columns(
                Alias(
                    'parent_id',
                    ArrayFirst(Traverse('@').depth(1).relation('->child->node').columns('id')),
                ),
                Alias(
                    'parent',
                    Traverse('@').columns('id', 'title').relation('->child->node').alias('parent'),
                ),
                all_=True,
            )
        )
