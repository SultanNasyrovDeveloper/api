from typing import TypedDict

from api.core.lexorank import Lexorank
from api.surorm import Response
from api.surorm.query import (
    Create,
    DefineVariable,
    Record,
    Relate,
    Select,
    Transaction,
    Variable,
)

from ..schemas import NodeCreateSchema
from .abstract import AbstractRequest


class CreateChildConfig(TypedDict):
    parent_id: str
    data: dict | NodeCreateSchema


class CreateChildRequest(AbstractRequest[CreateChildConfig]):
    async def perform(self) -> Response | None:
        last_child_order_query = (
            Select().columns('value order').from_('node')
            .where(f'->(child where out == {Record('node', self._config['parent_id']).sql()})')
            .order_by('order', direction='desc')
            .limit(1)
        )
        create_data = self._config['data']
        if isinstance(create_data, dict):
            create_data = NodeCreateSchema.model_validate(create_data)
        response = await self._db.query(last_child_order_query.sql())
        last_child_order = response.raw(many=False) or ''
        create_data.order = Lexorank.middle(previous=last_child_order)
        create_query = (
            Transaction()
            .perform(
                DefineVariable(
                    'child',
                    Create('node', only=True).content(
                        create_data.model_dump_surreal(exclude_unset=True, exclude_defaults=True)
                    ),
                ),
                Relate('child').from_('$child').to(Record('node', self._config['parent_id'])),
            )
            .return_(Variable('child'))
        )
        return await self._db.query(create_query.sql())
