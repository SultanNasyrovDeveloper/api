from typing import TypedDict

from minager.core.lexorank import Lexorank
from minager.core.surorm import Record
from minager.core.surorm.statements import (
    Create,
    DefineVariable,
    Relate,
    Transaction,
    Variable,
)

from ..queries import get_last_child_order_query
from ..schemas import NodeCreateSchema
from .abstract import AbstractRequest


class CreateChildConfig(TypedDict):
    parent_id: str
    data: dict | NodeCreateSchema


class CreateChildRequest(AbstractRequest[CreateChildConfig]):
    async def perform(self) -> dict | None:
        last_child_order_query = get_last_child_order_query(self._config['parent_id'])
        last_child_order: str | list = await self._db.query(last_child_order_query)
        if isinstance(last_child_order, list):
            last_child_order: str = last_child_order[0] if len(last_child_order) > 0 else None

        create_data = self._config['data']
        if isinstance(create_data, dict):
            create_data = NodeCreateSchema.model_validate(create_data)
        create_data.order = Lexorank.middle(previous=last_child_order)

        child_var = Variable('child')

        create_query = Transaction(
            DefineVariable(
                'child',
                Create('node', only=True).content(
                    create_data.model_dump_surreal(exclude_unset=True, exclude_defaults=True)
                ),
            ),
            Relate('child').from_(child_var).to(Record('node', self._config['parent_id'])),
        ).return_(child_var)
        return await self._db.query(create_query)
