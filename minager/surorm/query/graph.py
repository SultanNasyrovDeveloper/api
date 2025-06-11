"""
Recursion depth
Fields
"""

from typing import Self

from .types import Expression, Renderable
from .utils import render


class Traverse(Renderable):
    MAX_ALLOWED = 256

    def __init__(self, target: Expression = '', *args, **kwargs):
        self.target = target
        self._depth = None
        self._min = ''
        self._max = ''
        self._alias = None
        self._relation = None
        self._columns = []
        self._all = False

    def depth(self, depth: int) -> Self:
        self._depth = depth
        return self

    def depth_range(self, from_: int | None = None, to: int | None = None) -> Self:
        self._min = from_ or ''
        self._max = to or ''
        return self

    def alias(self, name: str):
        self._alias = name
        return self

    def relation(self, relation: Expression):
        self._relation = relation
        return self

    def columns(self, *args: Expression, all_: bool = False):
        self._columns = args
        self._all = all_
        return self

    def sql(self) -> str:
        sql = [self.target, self._render_depth(), self._render_columns()]
        return ''.join(sql)

    def _render_depth(self) -> str:
        if self._depth:
            return f'{{{self._depth}}}'
        return f'{{{self._min}..{self._max}}}'

    def _render_columns(self) -> str:
        if self._alias or len(self._columns) > 1:
            return f'.{{{', '.join(self._columns)}, {self._alias or 'connections'}: {render(self._relation)}.@ }}'
        return f'({self._relation}).{self._columns[0]}'
