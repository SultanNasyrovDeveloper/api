from typing import Literal, Self

from minager.surorm.mixins import IfExists
from minager.surorm.types import Expression, Renderable
from minager.surorm.utils import render

type RemoveResource = Literal[
    'namespace', 'database', 'user', 'access', 'event', 'event', 'field', 'index'
]
type RemoveFrom = Literal['namespace', 'database', 'table']


class Remove(IfExists, Renderable):
    def __init__(self, resource: RemoveResource, name: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resource = resource
        self._name = name
        self._remove_from: RemoveFrom | None = None
        self._table_name: str | None = None

    def on(self, target: RemoveFrom, name: str | None = None) -> Self:
        self._remove_from = target
        if target == 'table':
            assert name
        self._table_name = name if target == 'table' else None
        return self

    def sql(self) -> str:
        stmt = [f'remove {self._resource}']
        if self._if_exists:
            stmt.append(self.get_if_exists_sql())
        stmt.append(render(self._name))
        if self._remove_from:
            stmt.append(self.get_on_sql())
        return ' '.join(stmt)

    def get_on_sql(self) -> str:
        stmt = [f'on {self._remove_from}']
        if self._remove_from == 'table':
            stmt.append(self._table_name)
        return ' '.join(stmt)
