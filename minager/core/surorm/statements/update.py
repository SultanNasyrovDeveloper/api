from typing import Any, Literal, Self

from ..base import Renderable
from ..data_model import Record
from ..mixins import Filterable, Returnable
from ..orm.models import Table
from ..orm.serializer import Serializer
from ..orm.utils import get_table_name
from ..types import Expression
from ..utils import render


class Update(Filterable, Returnable, Renderable):
    def __init__(self, target: Expression | type[Table], only: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target = target
        self.only = only
        self.strategy: Literal['set', 'content', 'merge', 'patch'] = 'set'
        self.data = {}
        self._patch = {}
        self._timeout = None

    def set(self, **set_expressions: Any) -> Self:
        self.strategy = 'set'
        self.data = set_expressions
        return self

    def content(self, update_content: dict) -> Self:
        self.strategy = 'content'
        self.data = update_content
        return self

    def merge(self, merge_content: dict | Expression) -> Self:
        self.strategy = 'merge'
        self.data = merge_content
        return self

    def patch(self, patch_content: dict) -> Self:
        raise NotImplementedError

    def sql(self):
        q = ['update']
        if self.only:
            q.append('only')
        q.append(self.get_update_target())
        q.append(self.strategy)
        q.append(self.serialize_data())
        if return_expr := self.get_return_sql():
            q.append(return_expr)
        return ' '.join(q)

    def get_update_target(self) -> str:
        if isinstance(self.target, type) and issubclass(self.target, Table):
            return get_table_name(self.target)
        return render(self.target)

    def serialize_data(self) -> str:
        # TODO: Refactor when serializer and orm implemented
        if isinstance(self.target, (int, float, str)):
            return str(self.data)
        table = None
        if isinstance(self.target, Record):
            if isinstance(self.target, (int, float, str)):
                return str(self.data)
            if issubclass(self.target.table, Table):
                table = self.target.table
        if isinstance(self.target, type) and issubclass(self.target, Table):
            table = self.target
        if table:
            serializer_class = type('DataSerializer', (Serializer,), {'model': table})
            serializer = serializer_class()
            return serializer.serialize(self.data, self.strategy)
        return str(self.data)
