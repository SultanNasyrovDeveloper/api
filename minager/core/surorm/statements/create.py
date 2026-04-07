from typing import Any, Self, Type

from ..base import Statement
from ..mixins import Returnable
from ..orm.models import Table
from ..orm.serializer import Serializer
from ..types import RecordDataSetMode
from ..utils import render


class Create(Statement, Returnable):
    def __init__(self, target: str | Type[Table], only: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target
        self._only = only
        self._data_strategy: RecordDataSetMode = 'content'
        self._data = None

    def content(self, data: dict) -> Self:
        self._data_strategy = 'content'
        self._data = data
        return self

    def set(self, **field_values: Any) -> Self:
        self._data_strategy = 'set'
        self._data = field_values
        return self

    def sql(self) -> str:
        q = ['create']
        if self._only:
            q.append('only')
        table_name = self._target if isinstance(self._target, str) else self._target.__table_name__
        q.append(table_name)
        q.append(self._data_strategy)
        q.append(self.serialize_data())
        if return_expr := self.get_return_sql():
            q.append(return_expr)
        return ' '.join(q)

    def serialize_data(self) -> str:
        if isinstance(self._target, str):
            return render(self._data)
        serializer_class = type('DataSerializer', (Serializer,), {'model': self._target})
        serializer = serializer_class()
        return serializer.serialize(self._data, mode=self._data_strategy)
