from typing import Self

from minager.surorm.mixins import Returnable
from minager.surorm.utils import render

from ..base import Statement
from ..data_model.object import Object
from ..types import Expression, RecordDataSetMode


class Create(Statement, Returnable):
    def __init__(self, target: str, only: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target
        self._only = only
        self._data_strategy: RecordDataSetMode = 'content'
        self._content = None
        self._set = None

    def content(self, data: Expression) -> Self:
        self._data_strategy = 'content'
        self._content = data
        return self

    def set(self, *set_expressions: Expression) -> Self:
        self._data_strategy = 'set'
        self._set = set_expressions
        return self

    def sql(self) -> str:
        assert not self._content or not self._set
        q = ['create']
        if self._only:
            q.append('only')
        q.append(self._target)
        if self._data_strategy == 'content':
            content = self._content
            if isinstance(content, Object):
                content = content.sql(mode='content')
            q.extend(['content', content])
        if self._data_strategy == 'set':
            q.append('set')
            q.append(','.join(map(render, self._set)))
        if return_expr := self.get_return_sql():
            q.append(return_expr)
        return ' '.join(q)
