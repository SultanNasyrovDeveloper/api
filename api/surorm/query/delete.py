from typing import Self

from .mixins import Filterable, Returnable
from .types import Expression, Renderable


class Delete(Filterable, Returnable, Renderable):
    def __init__(self, from_: Expression, only: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._from = from_
        self._only = only

    def from_(self, target: str, only: bool = False) -> Self:
        self._from = target
        self._only = only
        return self

    def sql(self) -> str:
        q = ['delete']
        if self._only:
            q.append('only')
        q.append(self._from)
        if filter_expr := self.get_filter_sql():
            q.append(filter_expr)
        if return_expr := self.get_return_sql():
            q.append(return_expr)
        return ' '.join(q)
