from typing import Literal, Self

from .mixins import Filterable
from .types import Expression, Renderable
from .utils import render


class Select(Filterable, Renderable):
    def __init__(self, from_: Expression = None, only: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._from = None
        if from_:
            self.from_(from_, only=only)
        self._columns = []
        self._omit = []
        self._with = []
        self._where = []
        self._order_by = []
        self._order_by_direction = 'asc'
        self._group_by = []
        self._group_all = False
        self._split = []
        self._limit = 0
        self._start = 0
        self._timeout = 0
        self._fetch = []
        self._parallel = 1

    def __str__(self) -> str:
        return self.sql()

    def from_(self, name: Expression, only: bool = False) -> Self:
        sql = ['from']
        if only:
            sql.append('only')
        sql.append(render(name))
        self._from = ' '.join(sql)
        return self

    def columns(self, *columns: Expression, all_: bool = False) -> Self:
        if all_ and not (self._columns[0] == '*' if self._columns else False):
            if self._columns:
                self._columns.insert(0, '*')
            else:
                self._columns.append('*')
        existing_columns = set(self._columns)
        for column in columns:
            if column not in existing_columns:
                self._columns.append(column)
        return self

    def omit(self, *columns: Expression) -> Self:
        already_omitted = set(self._omit)
        for column in columns:
            if column not in already_omitted:
                self._omit.append(render(column))
        return self

    def start(self, number: int | None) -> Self:
        self._start = number
        return self

    def limit(self, number: int | None) -> Self:
        self._limit = number
        return self

    def split(self) -> Self:
        return self

    def with_(self) -> Self:
        return self

    def fetch(self, *columns: Expression) -> Self:
        self._fetch = columns
        return self

    def order_by(self, *columns: str, direction: Literal['asc', 'desc'] = 'asc') -> Self:
        existing_order_by_columns = set(self._order_by)
        for column in columns:
            if column not in existing_order_by_columns:
                self._order_by.append(column)
        self._order_by_direction = direction
        return self

    def group(self, *columns: Expression, all_: bool = True) -> Self:
        if all_:
            self._group_all = True
            self._group_by = []
        else:
            self._group_all = False
            self._group_by = columns
        return self

    def sql(self) -> str:
        q = ['select', ','.join(map(render, self._columns))]
        if self._omit:
            q.append('omit')
            q.append(','.join(self._omit))
        q.append(render(self._from))

        if self._fetch:
            q.append('fetch')
            q.append(', '.join([render(column) for column in self._fetch]))

        if filter_expression := self.get_filter_sql():
            q.append(filter_expression)

        if self._group_all or self._group_by:
            q.append('group all' if self._group_all else f'group by {','.join(self._group_by)}')

        if self._order_by:
            q.append(f'order by {','.join(self._order_by)} {self._order_by_direction}')

        if self._limit:
            q.append(f'limit {self._limit}')

        if self._start:
            q.append(f'start {self._start}')
        return ' '.join(q)
