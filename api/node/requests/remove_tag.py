from typing import TypedDict

from api.surorm import Response
from api.surorm.query import Array, Record, Update

from .abstract import AbstractRequest


class RemoveTagRequestConfig(TypedDict):
    node_id: str
    tag_ids: list[str]


class RemoveTagRequest(AbstractRequest[RemoveTagRequestConfig]):
    async def perform(self) -> Response | None:
        tags = Array(*[f'tag:{tag_id}' for tag_id in self._config['tag_ids']])
        query = (
            Update(Record('node', self._config['node_id'])).set(f'tags -= {tags}').return_('after')
        )
        return await self._db.query(query.sql())
