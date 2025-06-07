import json
from typing import Literal, Self

from .mixins import Filterable, Returnable
from .types import Expression, Renderable
from .utils import render


class Update(Filterable, Returnable, Renderable):
    def __init__(self, target: Expression, only: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._target = render(target)
        self._only = only
        self._strategy: Literal['set', 'content', 'merge', 'patch'] = 'set'
        self._set = []
        self._content = {}
        self._merge = {}
        self._patch = {}
        self._timeout = None

    def set(self, *set_expressions: str) -> Self:
        self._strategy = 'set'
        self._set = set_expressions
        return self

    def content(self, update_content: dict) -> Self:
        self._strategy = 'content'
        self._content = update_content
        return self

    def merge(self, merge_content: dict | Expression) -> Self:
        self._strategy = 'merge'
        self._merge = merge_content
        return self

    def patch(self, patch_content: dict) -> Self:
        self._strategy = 'patch'
        self._patch = patch_content
        return self

    def sql(self):
        q = [f'update']
        if self._only:
            q.append('only')
        q.append(self._target)
        if self._strategy == 'set':
            q.append('set')
            q.extend(self._set)
        if self._strategy == 'content':
            q.append('content')
            q.append(json.dumps(self._content))
        if self._strategy == 'merge':
            q.append('merge')
            q.append(str(self._merge))
        if self._strategy == 'patch':
            q.append('patch')
            q.append(json.dumps(self._patch))
        if filter_expr := self.get_filter_sql():
            q.append(filter_expr)
        if return_expr := self.get_return_sql():
            q.append(return_expr)
        return ' '.join(q)
