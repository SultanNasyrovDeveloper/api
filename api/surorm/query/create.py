from typing import Literal, Self

from .mixins import Returnable
from .types import Expression, Renderable
from .utils import render

type CreateDataStrategy = Literal['content', 'set']


class Create(Returnable, Renderable):
    def __init__(self, target: str, only: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = target
        self._only = only
        self._data_strategy: CreateDataStrategy = 'content'
        self._content = {}
        self._set = []

    def content(self, data: str) -> Self:
        self._data_strategy = 'content'
        self._content = data
        return self

    def set(self, *set_expressions: Expression) -> Self:
        self._data_strategy = 'set'
        self._set = set_expressions
        return self

    def sql(self) -> str:
        q = ['create']
        if self._only:
            q.append('only')
        q.append(self._target)
        if self._data_strategy == 'content':
            q.append('content')
            q.append(self._content)
        if self._data_strategy == 'set':
            q.append('set')
            q.append(','.join(map(render, self._set)))
        if return_expr := self.get_return_sql():
            q.append(return_expr)
        return ' '.join(q)
