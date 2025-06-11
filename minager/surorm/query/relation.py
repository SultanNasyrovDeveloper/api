from typing import Self

from .mixins import Returnable
from .types import Expression, Renderable
from .utils import render


class Relate(Returnable, Renderable):
    def __init__(self, name: 'str', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._relation = name
        self._from = []
        self._to = []

    def from_(self, *from_records: Expression) -> Self:
        self._from = from_records
        return self

    def to(self, *to_records: Expression) -> Self:
        self._to = to_records
        return self

    def sql(self):
        q = [
            'relate',
            (
                f'{self._render_relation_records(self._from)}'
                f'->{self._relation}'
                f'->{self._render_relation_records(self._to)}'
            ),
        ]
        if return_expr := self.get_return_sql():
            q.append(return_expr)
        return ' '.join(q)

    def _render_relation_records(self, records: list[Expression]) -> str:
        if len(records) == 1:
            return render(records[0])
        return f'[{','.join(map(render, records))}]'
