from typing import Literal, Self

from .types import Expression
from .utils import render

type ReturnType = Literal['none', 'after', 'before', 'diff']


class Filterable:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._where = set()

    def where(self, *conditions: Expression) -> Self:
        if self._where:
            self._where.update(set(conditions))
        else:
            self._where = set(conditions)
        return self

    def get_filter_sql(self) -> str | None:
        if self._where:
            return f'where {' and '.join(map(render, self._where))}'


class Returnable:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._return: ReturnType | None = 'after'

    def get_return_sql(self) -> str | None:
        if self._return:
            return f'return {self._return}'

    def return_(self, value: ReturnType | None) -> Self:
        self._return = value
        return self


class Overridable:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._overwrite: bool = False

    def overwrite(self, value: bool) -> Self:
        self._overwrite = value
        return self

    def get_overwrite_sql(self) -> str | None:
        return 'overwrite' if self._overwrite else None


class IfExists:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._if_exists = False

    def if_exists(self, if_not_exists: bool) -> Self:
        self._if_exists = if_not_exists
        return self

    def get_if_exists_sql(self) -> str | None:
        return 'if exists' if self._if_exists else None


class IfNotExists:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._if_not_exists = False

    def if_not_exists(self, if_not_exists: bool) -> Self:
        self._if_not_exists = if_not_exists
        return self

    def get_if_not_exists_sql(self) -> str | None:
        return 'if not exists' if self._if_not_exists else None


class Commentable:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._comment: str | None = None

    def comment(self, text: str) -> Self:
        self._comment = text
        return self

    def get_comment_sql(self) -> str | None:
        return f'comment {self._comment}' if self._comment else None
