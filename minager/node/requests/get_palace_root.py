from typing import TypedDict

from minager.core.surorm import Response
from minager.core.surorm.statements import Select

from .abstract import AbstractRequest


class GetPalaceRootConfig(TypedDict):
    owner_id: str


class GetPalaceRootRequest(AbstractRequest[GetPalaceRootConfig]):
    async def perform(self) -> Response[str] | None:
        query = (
            Select('value id')
            .from_('node')
            .where('array::is_empty(->child->node)', f'owner_id == "{self._config['owner_id']}"')
        )
        return await self._db.query(query.sql())
