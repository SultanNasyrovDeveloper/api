from typing import TypedDict

from api.surorm import Response
from api.surorm.query import Alias, Select, String, Traverse

from .abstract import AbstractRequest


class ListNodesRequestConfig(TypedDict):
    page: int
    per_page: int
    owner_id: str
    search: str | None


class ListNodesRequest(AbstractRequest[ListNodesRequestConfig]):

    async def perform(self) -> Response | None:
        query = (
            Select('node')
            .columns(
                'id',
                'title',
                Alias(
                    'parent',
                    Traverse('@').alias('parent').relation('->child->node').columns('id', 'title'),
                ),
            )
            .limit(self._config['per_page'])
            .start(self._config['per_page'] * (self._config['page'] - 1))
        )
        if owner_id := self._config['owner_id']:
            query.where(f'owner_id == {String(owner_id)}')
        if search := self._config['search']:
            query.where(f'title @@ {String(search)}')

        return await self._db.query(query.sql())
