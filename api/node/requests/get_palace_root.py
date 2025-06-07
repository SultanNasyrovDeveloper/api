from typing import TypedDict

from api.surorm import Response
from api.surorm.query import Select

from .abstract import AbstractRequest


class GetPalaceRootConfig(TypedDict):
    owner_id: str


class GetPalaceRootRequest(AbstractRequest[GetPalaceRootConfig]):
    async def perform(self) -> Response[str] | None:
        query = (
            Select('node')
            .columns('value id')
            .where('array::is_empty(->child->node)', f'owner_id == "{self._config['owner_id']}"')
        )
        return await self._db.query(query.sql())
