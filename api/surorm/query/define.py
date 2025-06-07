from typing import Self

from .mixins import Commentable, IfNotExists, Overridable
from .types import Expression, Renderable, TableType
from .utils import render


class DefineNamespace(Overridable, IfNotExists, Commentable, Renderable):
    def __init__(self, name: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def sql(self) -> str:
        stmt = ['define namespace']
        if overwrite_sql := self.get_overwrite_sql():
            stmt.append(overwrite_sql)
        if if_not_exists_sql := self.get_if_not_exists_sql():
            stmt.append(if_not_exists_sql)
        stmt.append(render(self.name))
        if comment_sql := self.get_comment_sql():
            stmt.append(comment_sql)
        return ' '.join(stmt)


class DefineDatabase(Overridable, IfNotExists, Commentable, Renderable):
    def __init__(self, name: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def sql(self) -> str:
        stmt = ['define database']
        if overwrite_sql := self.get_overwrite_sql():
            stmt.append(overwrite_sql)
        if if_not_exists_sql := self.get_if_not_exists_sql():
            stmt.append(if_not_exists_sql)
        stmt.append(render(self.name))
        if comment_sql := self.get_comment_sql():
            stmt.append(comment_sql)
        return ' '.join(stmt)


class DefineTable(Overridable, IfNotExists, Commentable, Renderable):
    def __init__(self, name: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name
        self._type: TableType = 'normal'
        self._from: str | None = None
        self._to: str | None = None
        self._schemafull: bool = False

    def type(
        self, table_type: TableType, from_: Expression | None = None, to: Expression | None = None
    ) -> Self:
        if table_type == 'relation':
            assert from_ and to
            self._type = table_type
            self._from = from_
            self._to = to
        else:
            assert not from_ and not to
            self._type = table_type
        return self

    def schemafull(self, value: bool) -> Self:
        self._schemafull = value
        return self

    def sql(self) -> str:
        stmt = ['define table']
        if overwrite_sql := self.get_overwrite_sql():
            stmt.append(overwrite_sql)
        if if_not_exists_sql := self.get_if_not_exists_sql():
            stmt.append(if_not_exists_sql)
        stmt.append(render(self._name))
        stmt.append('schemafull' if self._schemafull else 'schemaless')
        stmt.append(self._get_type_sql())
        if comment_sql := self.get_comment_sql():
            stmt.append(comment_sql)
        return ' '.join(stmt)

    def _get_type_sql(self) -> str:
        stmt = [f'type {self._type}']
        if self._type == 'relation':
            stmt.append(f'from {self._from} to {self._to}')
        return ' '.join(stmt)


class DefineField(Overridable, IfNotExists, Commentable, Renderable):
    def __init__(self, name: Expression, type_: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name: Expression = name
        self._type: Expression = type_
        self._table: Expression | None = None
        self._is_optional: bool = False
        self._is_flexible: bool = False
        self._default: Expression | None = None
        self._assert: Expression | None = None
        self._is_read_only: bool = False

    def on(self, table: Expression) -> Self:
        self._table = table
        return self

    def type(self, type_: Expression, is_optional: bool = False, is_flexible: bool = False) -> Self:
        self._type = type_
        self._is_optional = is_optional
        self._is_flexible = is_flexible
        return self

    def default(self, expression: Expression) -> Self:
        self._default = expression
        return self

    def sql(self) -> str:
        stmt = ['define field']
        if overwrite_sql := self.get_overwrite_sql():
            stmt.append(overwrite_sql)
        if if_not_exists_sql := self.get_if_not_exists_sql():
            stmt.append(if_not_exists_sql)
        stmt.append(render(self._name))
        stmt.append(f'on table {render(self._table)}')
        if self._is_flexible:
            stmt.append('flexible')
        stmt.append(f'type {render(self._type)}')
        if self._default:
            stmt.append(f'default {render(self._default)}')
        if comment_sql := self.get_comment_sql():
            stmt.append(comment_sql)
        return ' '.join(stmt)


class DefineIndex(Overridable, IfNotExists, Commentable, Renderable):
    def __init__(self, name: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name
        self._table: str | None = None
        self._columns = []
        self._is_unique = False
        self._is_search: bool = False
        self._search_analyzer: str | None = None
        self._ranking_algorithm: str | None = None
        self._is_highlighted: bool = False

    def on(self, table: str) -> Self:
        self._table = table
        return self

    def columns(self, *columns: str) -> Self:
        self._columns = columns
        return self

    def search(self, analyzer: str, ranking: str, is_highlighted: bool = False) -> Self:
        self._is_search = True
        self._search_analyzer = analyzer
        self._ranking_algorithm = ranking
        self._is_highlighted = is_highlighted
        return self

    def sql(self) -> str:
        stmt = ['define index']
        if overwrite_sql := self.get_overwrite_sql():
            stmt.append(overwrite_sql)
        if if_not_exists_sql := self.get_if_not_exists_sql():
            stmt.append(if_not_exists_sql)
        stmt.append(render(self._name))
        stmt.append(f'on table {self._table}')
        stmt.append(f'columns {', '.join(self._columns)}')
        if self._is_unique:
            stmt.append('unique')
        if self._is_search:
            stmt.append(self._get_search_sql())
        if comment_sql := self.get_comment_sql():
            stmt.append(comment_sql)
        return ' '.join(stmt)

    def _get_search_sql(self) -> str:
        stmt = [f'search analyzer {self._search_analyzer} {self._ranking_algorithm}']
        if self._is_highlighted:
            stmt.append('highlights')
        return ' '.join(stmt)


class DefineAnalyzer(Overridable, IfNotExists, Commentable, Renderable):
    def __init__(self, name: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name: Expression = name
        self._tokenizers: list[str] = []
        self._filters: list[Expression] = []

    def tokenizers(self, *values: str) -> Self:
        self._tokenizers = values
        return self

    def filters(self, *values: Expression) -> Self:
        self._filters = values
        return self

    def sql(self) -> str:
        stmt = ['define analyzer']
        if overwrite_sql := self.get_overwrite_sql():
            stmt.append(overwrite_sql)
        if if_not_exists_sql := self.get_if_not_exists_sql():
            stmt.append(if_not_exists_sql)
        stmt.append(render(self._name))
        if self._tokenizers:
            stmt.append(f'tokenizers {', '.join(map(render, self._tokenizers))}')
        if self._filters:
            stmt.append(f'filters {', '.join(map(render, self._filters))}')
        if comment_sql := self.get_comment_sql():
            stmt.append(comment_sql)
        return ' '.join(stmt)


class DefineFunction(Overridable, IfNotExists, Commentable, Renderable):
    def __init__(self, target: Expression, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name: Expression = target
        self._body: Expression | None = None
        self._args: list[Expression] = []

    def body(self, code: Expression) -> Self:
        self._body = code
        return self

    def args(self, *arguments: Expression) -> Self:
        self._args = arguments
        return self

    def sql(self) -> str:
        stmt = ['define function']
        if overwrite_sql := self.get_overwrite_sql():
            stmt.append(overwrite_sql)
        if if_not_exists_sql := self.get_if_not_exists_sql():
            stmt.append(if_not_exists_sql)
        stmt.append(render(self._name))
        stmt.append(f'({', '.join(map(render, self._args))})')
        stmt.append(f'{{ {render(self._body)}; }}')
        if comment_sql := self.get_comment_sql():
            stmt.append(comment_sql)
        return ' '.join(stmt)
